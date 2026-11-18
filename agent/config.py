"""Конфигурация CLI и Telegram-интерфейса."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
DOCS = ROOT / "documents"
DATA.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

MODELS = {
    "1": ("Baidu ERNIE 5.5 Flash", "baidu/ernie-5.5-flash-preview:free"),
    "2": ("Cohere North Mini Code", "cohere/north-mini-code:free"),
    "3": ("Dots3 Note", "dots-studio/dots-3-note-preview:free"),
    "4": ("Gemma 4 26B", "google/gemma-4-26b-a4b-it:free"),
    "5": ("Gemma 4 31B", "google/gemma-4-31b-it:free"),
    "6": ("Liquid LFM3", "liquid/lfm-3-1.7b:free"),
    "7": ("Nemotron Nano Omni", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"),
    "8": ("Nemotron Ultra", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    "9": ("Nemotron Lightning", "nvidia/nemotron-3.5-lightning:free"),
    "10": ("Nemotron Super VL", "nvidia/nemotron-3.5-super-vl:free"),
    "11": ("Particle-1", "particle-ai/particle-1:free"),
    "12": ("Recursive Flint", "recursive/flint-v1.0:free"),
    "13": ("Inkling 2 Small", "thinkingmachines/inkling-2-small:free"),
    "14": ("Ling 3.2 Flash", "inclusionai/ling-3.2-flash:free"),
}

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("ID_MODEL", MODELS["9"][1]).strip()
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSIONS = 384
HISTORY_RUNS = 8
MAX_TOKENS = 2500
FALLBACKS = [MODELS["8"][1], MODELS["5"][1]]
SEED_URL = "https://docs.agno.com/introduction.md"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def parse_telegram_ids(raw: str) -> frozenset[int]:
    """Список ID через запятую. Некорректные значения блокируют запуск."""
    if not raw.strip():
        return frozenset()
    parts = [piece.strip() for piece in raw.split(",")]
    if any(not part.isascii() or not part.isdecimal() or int(part) <= 0 for part in parts):
        raise ValueError(
            "TELEGRAM_OWNER_ID должен содержать Telegram ID через запятую без пустых элементов"
        )
    return frozenset(int(part) for part in parts)


TELEGRAM_OWNER_IDS = parse_telegram_ids(os.getenv("TELEGRAM_OWNER_ID", ""))
