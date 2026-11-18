"""LanceDB + Agno Knowledge; изолированные индексы пользователей Telegram."""

from functools import lru_cache
from pathlib import Path

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


def insert_clean_text(knowledge: Knowledge, text: str, *, name: str, metadata: dict | None = None) -> None:
    """Insert already-extracted UTF-8 content, never a user-supplied binary."""
    if not 50 <= len(text) <= 250_000:
        raise ValueError("Недопустимый размер извлечённого текста")
    knowledge.insert(text_content=text, name=name, metadata=metadata, skip_if_exists=True)


def delete_document_vectors(user_id: int, doc_id: str) -> None:
    """Delete only vectors for this one Telegram document. Fail closed on errors."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Неверный Telegram ID")
    from uuid import UUID
    # Existing document IDs are UUID4 hexadecimal strings.
    if len(doc_id) != 32 or UUID(doc_id).hex != doc_id:
        raise ValueError("Неверный ID документа")
    knowledge = create_user_knowledge(user_id)
    name = f"telegram_{user_id}_{doc_id}"
    deleted = knowledge.vector_db.delete_by_name(name)
    if deleted is False:
        raise RuntimeError("Не удалось удалить векторный индекс. Данные не затронуты")


def add_path(knowledge: Knowledge, value: str, *, metadata=None, name=None) -> str:
    """Compatibility API: all uploaded local documents go through Docker."""
    import asyncio
    from sandbox_client import sanitize_local_document
    path = Path(value).expanduser().resolve(strict=True)
    text, _ = asyncio.run(sanitize_local_document(path))
    insert_clean_text(knowledge, text, name=name or path.name, metadata=metadata)
    return path.name


def add_url(knowledge: Knowledge, url: str) -> str:
    """Only the pre-approved public documentation URL is allowed."""
    if url != SEED_URL:
        raise ValueError("Загрузка произвольных URL отключена")
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
