"""Parse ONE untrusted document in a Docker sandbox. Do not import from bot."""

from __future__ import annotations

import json
import os
import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

INPUT = Path('/work/inbox')
OUTPUT = Path('/work/outbox')
MAX_BYTES = 8 * 1024 * 1024
MAX_CHARS = 250_000
MAX_PAGES = 120
MAX_ZIP_ENTRIES = 750
MAX_UNCOMPRESSED = 35 * 1024 * 1024
EXTS = {'.pdf', '.docx', '.txt', '.md', '.csv'}


class DocumentRejected(ValueError):
    pass


def _check_magic(path: Path, ext: str) -> None:
    with path.open('rb') as f:
        start = f.read(8192)
    if ext == '.pdf':
        if not start.startswith(b'%PDF-'):
            raise DocumentRejected('PDF имеет неверную сигнатуру')
        # These checks are defense-in-depth; they cannot detect compressed/obfuscated content.
        if any(s in start for s in (b'/JavaScript', b'/Launch', b'/EmbeddedFile')):
            raise DocumentRejected('PDF содержит подозрительные активные элементы')
    elif ext == '.docx':
        if not start.startswith(b'PK\x03\x04'):
            raise DocumentRejected('DOCX имеет неверную сигнатуру ZIP')
    else:
        if b'\x00' in start[:2048] and not start.startswith((b'\xff\xfe', b'\xfe\xff')):
            raise DocumentRejected('Файл похож на двоичный, а не текстовый')


def _check_docx_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise DocumentRejected('Слишком много объектов в DOCX')
        total = 0
        names = set()
        for entry in entries:
            name = entry.filename.replace('\\', '/')
            lower = name.lower()
            if (name.startswith('/') or ':' in name or
                    '..' in name.split('/') or entry.flag_bits & 1):
                raise DocumentRejected('Подозрительная структура DOCX')
            if (lower.endswith(('.bin', '.exe', '.js', '.vbs', '.ps1', '.dll', '.scr'))
                or any(p in lower for p in ('/activex/', '/embeddings/', '/oleobject', 'vbaproject'))):
                raise DocumentRejected('В DOCX есть вложенный активный/двоичный объект')
            if entry.file_size > MAX_UNCOMPRESSED:
                raise DocumentRejected('DOCX содержит слишком большой объект')
            if entry.compress_size == 0 and entry.file_size > 0:
                raise DocumentRejected('Подозрительное сжатие DOCX')
            if entry.compress_size and entry.file_size > entry.compress_size * 150:
                raise DocumentRejected('Возможная ZIP-бомба')
            total += entry.file_size
            if total > MAX_UNCOMPRESSED:
                raise DocumentRejected('DOCX слишком большой после распаковки')
            names.add(name)
        if 'word/document.xml' not in names or '[Content_Types].xml' not in names:
            raise DocumentRejected('Некорректный DOCX')


def parse(path: Path, ext: str) -> tuple[str, int]:
    _check_magic(path, ext)
    pieces: list[str] = []
    count = 0
    pages = 0

    def add(text: str):
        nonlocal count
        remaining = MAX_CHARS - count
        if remaining > 0 and text:
            part = text[:remaining]
            pieces.append(part)
            count += len(part)

    if ext == '.pdf':
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            raise DocumentRejected('Зашифрованные PDF не поддерживаются')
        if len(reader.pages) > MAX_PAGES:
            raise DocumentRejected(f'В PDF больше {MAX_PAGES} страниц')
        for index, page in enumerate(reader.pages, 1):
            pages = index
            if count >= MAX_CHARS:
                break
            add(f'\n[Страница {index}]\n')
            add((page.extract_text() or '') + '\n')
    elif ext == '.docx':
        _check_docx_zip(path)
        doc = Document(str(path))
        for paragraph in doc.paragraphs:
            if count >= MAX_CHARS:
                break
            add(paragraph.text + '\n')
        for table in doc.tables:
            for row in table.rows:
                if count >= MAX_CHARS:
                    break
                add(' | '.join(cell.text for cell in row.cells) + '\n')
    else:
        raw = path.read_bytes()
        for enc in ('utf-8-sig', 'utf-16', 'cp1251'):
            try:
                add(raw.decode(enc))
                break
            except UnicodeError:
                pass

    result = ''.join(pieces).strip()
    result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', result)
    if len(result) < 50:
        raise DocumentRejected('Недостаточно текста; для сканов нужен OCR')
    return result, pages


def main():
    job_id = sys.argv[1]
    if not re.fullmatch(r'[a-f0-9]{32}', job_id):
        raise SystemExit('Invalid job ID')
    raw_path = INPUT / f'{job_id}.bin'
    job_path = INPUT / f'{job_id}.json'
    result_path = OUTPUT / f'{job_id}.json'
    text_path = OUTPUT / f'{job_id}.txt'
    try:
        # File name and content never influence filesystem paths.
        job = json.loads(job_path.read_text(encoding='utf-8'))
        ext = job.get('ext')
        if ext not in EXTS:
            raise DocumentRejected('Неподдерживаемый формат')
        if raw_path.is_symlink() or not raw_path.is_file():
            raise DocumentRejected('Некорректный файл в карантине')
        if raw_path.stat().st_size > MAX_BYTES or raw_path.stat().st_size == 0:
            raise DocumentRejected('Файл пустой или больше лимита')
        text, pages = parse(raw_path, ext)
        temp = text_path.with_suffix('.txt.tmp')
        temp.write_text(text, encoding='utf-8')
        os.replace(temp, text_path)
        result = {'status': 'ok', 'pages': pages, 'characters': len(text)}
    except Exception as exc:
        # No stack traces or raw content are returned to the bot.
        reason = str(exc) if isinstance(exc, DocumentRejected) else 'Не удалось безопасно обработать документ'
        result = {'status': 'error', 'error': reason[:180]}
    temp = result_path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    os.replace(temp, result_path)


if __name__ == '__main__':
    main()
