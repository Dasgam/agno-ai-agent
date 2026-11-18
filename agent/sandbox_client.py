"""The bot stores an upload in quarantine and ONLY consumes sanitized text.

No untrusted PDF/DOCX parser is imported in this process. A separate
network-disabled Docker container handles all parsing. Fail closed if absent.
"""

import asyncio
import json
import os
import time
from pathlib import Path

from config import DATA

SPOOL = DATA / 'sandbox_spool'
INBOX = SPOOL / 'inbox'
OUTBOX = SPOOL / 'outbox'
MAX_TEXT_BYTES = 1_200_000
MAX_RESULT_BYTES = 2_048
WAIT_SECONDS = 55


def initialize_sandbox() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    OUTBOX.mkdir(parents=True, exist_ok=True)
    # Clean abandoned quarantine artifacts after crashes. Never remove fresh jobs.
    cutoff = time.time() - 900
    for folder in (INBOX, OUTBOX):
        for path in folder.iterdir():
            if path.is_file() and path.name != 'health.txt' and path.suffix in ('.bin', '.json', '.txt', '.tmp'):
                try:
                    if path.stat().st_mtime < cutoff:
                        path.unlink(missing_ok=True)
                except OSError:
                    pass


def sandbox_online() -> bool:
    health = OUTBOX / 'health.txt'
    try:
        stamp = float(_safe_read(health, 64))
        return 0 <= time.time() - stamp < 12
    except (OSError, ValueError):
        return False


def _safe_read(path: Path, max_bytes: int) -> bytes:
    """Never follow a symlink from a compromised extraction worker."""
    if path.is_symlink():
        raise ValueError('Опасный результат обработчика')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags)
    try:
        if os.fstat(fd).st_size > max_bytes:
            raise ValueError('Обработчик вернул слишком большой результат')
        return os.read(fd, max_bytes + 1)
    finally:
        os.close(fd)


async def extract_isolated(job_id: str, raw_path: Path, suffix: str) -> tuple[str, int]:
    """Input raw_path is already downloaded to INBOX/ID.bin."""
    if raw_path != INBOX / f'{job_id}.bin':
        raise ValueError('Неверный путь карантина')
    if len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
        raise ValueError('Неверный идентификатор документа')
    job = INBOX / f'{job_id}.json'
    tmp_job = INBOX / f'{job_id}.tmp'
    status = OUTBOX / f'{job_id}.json'
    text_file = OUTBOX / f'{job_id}.txt'
    try:
        tmp_job.write_text(json.dumps({'ext': suffix}), encoding='utf-8')
        os.replace(tmp_job, job)
        for _ in range(int(WAIT_SECONDS / 0.4)):
            if status.is_file() or status.is_symlink():
                result = json.loads(_safe_read(status, MAX_RESULT_BYTES))
                if result.get('status') != 'ok':
                    raise ValueError(result.get('error', 'Файл отклонён обработчиком'))
                text = _safe_read(text_file, MAX_TEXT_BYTES).decode('utf-8')
                if not (50 <= len(text) <= 250_000):
                    raise ValueError('Некорректный извлечённый текст')
                pages = result.get('pages', 0)
                if not isinstance(pages, int) or pages < 0 or pages > 120:
                    raise ValueError('Некорректные метаданные')
                return text, pages
            await asyncio.sleep(0.4)
        raise TimeoutError(
            'Изолированный обработчик не ответил. '
            'Проверь Docker: docker compose ps / docker compose logs document-sandbox'
        )
    finally:
        for p in (job, tmp_job, raw_path, status, text_file):
            p.unlink(missing_ok=True)

async def sanitize_local_document(source: Path) -> tuple[str, int]:
    """Use the same offline Docker parser for CLI supplied files.

    The API is deliberately fail-closed: no direct PDF/DOCX parsing fallback.
    """
    import shutil
    from uuid import uuid4

    if not sandbox_online():
        raise RuntimeError('Сначала запусти docker compose up -d --build')
    source = source.expanduser().resolve(strict=True)
    ext = source.suffix.lower()
    if ext not in ('.pdf', '.docx', '.txt', '.md', '.csv'):
        raise ValueError('Разрешены только PDF/DOCX/TXT/MD/CSV')
    if source.stat().st_size > 8 * 1024 * 1024 or source.stat().st_size == 0:
        raise ValueError('Файл пустой или больше 8 МБ')
    job_id = uuid4().hex
    dest = INBOX / f'{job_id}.bin'
    try:
        with source.open('rb') as src, dest.open('xb') as target:
            shutil.copyfileobj(src, target, length=64 * 1024)
        return await extract_isolated(job_id, dest, ext)
    finally:
        dest.unlink(missing_ok=True)
