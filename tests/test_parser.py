from pathlib import Path
import io
import sys
import zipfile
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worker'))
from parse_once import DocumentRejected, parse


def test_fake_pdf_is_rejected(tmp_path):
    file = tmp_path / 'file.bin'
    file.write_bytes(b'MZ' + b'A' * 100)
    with pytest.raises(DocumentRejected):
        parse(file, '.pdf')


def test_zip_bomb_is_rejected(tmp_path):
    file = tmp_path / 'file.bin'
    with zipfile.ZipFile(file, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', 'a')
        z.writestr('word/document.xml', 'A' * (500 * 1024))
    with pytest.raises(DocumentRejected):
        parse(file, '.docx')


def test_text_file(tmp_path):
    file = tmp_path / 'file.bin'
    file.write_text('Лекция по безопасности приложений. ' * 8, encoding='utf-8')
    extracted, pages = parse(file, '.txt')
    assert pages == 0
    assert 'Лекция' in extracted
