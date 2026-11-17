"""Локальный RAG с многоязычными эмбеддингами."""
from pathlib import Path
from urllib.parse import urlparse
from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.lancedb import LanceDb, SearchType
from config import DATA, DOCS, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, SEED_URL

SUPPORTED = {'.pdf', '.docx', '.txt', '.md', '.csv'}


def create_knowledge():
    embedder = SentenceTransformerEmbedder(
        id=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSIONS,
        normalize_embeddings=True,
    )
    db = LanceDb(
        uri=str(DATA / 'vectors_multilingual_v1'),
        table_name='assistant_documents',
        search_type=SearchType.hybrid,
        embedder=embedder,
    )
    return Knowledge(vector_db=db)


def add_path(knowledge, value: str):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f'Файл не найден: {path}')
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f'Неподдерживаемый формат: {path.suffix}')
    knowledge.insert(path=str(path), skip_if_exists=True)
    return path.name


def add_url(knowledge, url: str):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.netloc:
        raise ValueError('Разрешены только публичные HTTPS-ссылки.')
    # Загружайте только доверенные публичные URL: reader делает сетевой запрос.
    knowledge.insert(url=url, skip_if_exists=True)
    return url


def seed_knowledge(knowledge):
    """Официальная документация Agno вместо художественной книги."""
    return add_url(knowledge, SEED_URL)


def import_documents(knowledge):
    count = 0
    for path in sorted(DOCS.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            add_path(knowledge, str(path))
            count += 1
    return count
