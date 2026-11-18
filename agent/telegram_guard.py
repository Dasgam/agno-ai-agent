"""Deterministic document-reference detection (no vague 'file' keyword block)."""
import re

# Do not block general programming questions such as 'Как создать файл в Python?'.
MISSING_DOC_QUESTION = re.compile(
    r"^\s*(?:о\s+ч[её]м|что\s+в|что\s+содержится\s+в|"
    r"перескажи|проанализируй|суммируй|прочитай)\s+"
    r"(?:(?:этот|данный|данном|этом|загруженн\w*|мой)\s+)?"
    r"(?:файл\w*|документ\w*|pdf)\b",
    re.IGNORECASE,
)


def requests_missing_document(question: str) -> bool:
    return bool(MISSING_DOC_QUESTION.search(question))
