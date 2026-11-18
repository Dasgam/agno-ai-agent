import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'agent'))
from telegram_guard import requests_missing_document


def test_general_questions_not_blocked():
    for q in (
        'Как создать файл в Python?',
        'Как устроены PDF файлы?',
        'Расскажи про документы в бухгалтерии',
        'Напиши код для чтения файла',
        'Как написать лекцию по программированию?',
    ):
        assert not requests_missing_document(q), q


def test_explicit_document_reference_detected():
    for q in (
        'О чём этот файл?',
        'Что содержится в загруженном документе?',
        'Перескажи pdf',
        'Проанализируй документ',
    ):
        assert requests_missing_document(q), q
