"""LanceDB + Agno Knowledge; изолированные индексы пользователей Telegram."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType

from config import DATA, DOCS, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, SEED_URL

SUPPORTED = {".pdf", ".docx", ".txt", ".md", ".csv"}


@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformerEmbedder(
        id=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
        normalize_embeddings=True,
    )


def _knowledge_at(folder: Path) -> Knowledge:
    folder.mkdir(parents=True, exist_ok=True)
    return Knowledge(
        vector_db=LanceDb(
            uri=str(folder),
            table_name="assistant_documents",
            search_type=SearchType.hybrid,
            embedder=get_embedder(),
        )
    )


def create_knowledge() -> Knowledge:
    """Общая локальная база CLI. Не используется в Telegram."""
    return _knowledge_at(DATA / "vectors_multilingual_v1")


@lru_cache(maxsize=32)
def create_user_knowledge(user_id: int) -> Knowledge:
    """Каждый Telegram ID получает собственную физическую LanceDB."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Некорректный ID Telegram")
    return _knowledge_at(DATA / "telegram_rag" / f"user_{user_id}")


def add_path(knowledge: Knowledge, value: str, *, metadata=None, name=None) -> str:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Неподдерживаемый формат: {path.suffix}")
    kwargs = {"path": str(path), "skip_if_exists": True}
    if metadata:
        kwargs["metadata"] = metadata
    if name:
        kwargs["name"] = name
    knowledge.insert(**kwargs)
    return path.name


def add_url(knowledge: Knowledge, url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Поддерживаются только HTTPS-ссылки")
    # Использовать только доверенные URL, доступные для чтения сервером.
    knowledge.insert(url=url, skip_if_exists=True)
    return url


def seed_knowledge(knowledge: Knowledge):
    return add_url(knowledge, SEED_URL)


def import_documents(knowledge: Knowledge) -> int:
    count = 0
    for path in sorted(DOCS.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            add_path(knowledge, str(path))
            count += 1
    return count
