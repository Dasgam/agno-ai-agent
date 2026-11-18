import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from document_retrieval import excerpt_for_question


def test_broad_document_summary_uses_start_middle_end():
    text = ''.join(f'[Страница {i}]\n' + (f'Тема {i}. ' * 100) for i in range(1, 41))
    excerpt = excerpt_for_question(text, 'Сделай обзор всех глав и разделов', 14_000)
    assert '[Страница 1]' in excerpt
    assert '[Страница 40]' in excerpt
    assert 'Фрагмент' in excerpt
    assert len(excerpt) <= 14_000


def test_specific_question_retrieves_matching_section():
    text = ('[Страница 1]\nВведение. ' * 120) + ('[Страница 2]\nSQL инъекции. ' * 120)
    result = excerpt_for_question(text, 'Что такое SQL инъекции?')
    assert 'SQL инъекции' in result


def test_empty_text_returns_empty_string():
    assert excerpt_for_question('  ', 'Объясни') == ''
