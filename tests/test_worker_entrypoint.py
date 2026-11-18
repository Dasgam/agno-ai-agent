import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worker'))
import parse_once as parser


def test_worker_entrypoint_returns_clean_text(tmp_path, monkeypatch):
    input_file = tmp_path / 'data.bin'
    output = tmp_path / 'output'
    output.mkdir()
    input_file.write_text('Данные из документа, предназначенные для безопасного разбора. ' * 5, encoding='utf-8')
    monkeypatch.setattr(parser, 'INPUT', input_file)
    monkeypatch.setattr(parser, 'OUTPUT', output)
    monkeypatch.setattr(sys, 'argv', ['parse_once.py', '.txt'])
    parser.main()
    status = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    assert status['status'] == 'ok'
    assert (output / 'content.txt').read_text(encoding='utf-8').startswith('Данные')


def test_worker_entrypoint_rejects_renamed_executable(tmp_path, monkeypatch):
    input_file = tmp_path / 'data.bin'
    output = tmp_path / 'output'
    output.mkdir()
    input_file.write_bytes(b'MZ' + b'A' * 200)
    monkeypatch.setattr(parser, 'INPUT', input_file)
    monkeypatch.setattr(parser, 'OUTPUT', output)
    monkeypatch.setattr(sys, 'argv', ['parse_once.py', '.pdf'])
    parser.main()
    status = json.loads((output / 'result.json').read_text(encoding='utf-8'))
    assert status['status'] == 'error'
    assert not (output / 'content.txt').exists()
