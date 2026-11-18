"""Deterministic excerpts from the selected document; no model/tool access here."""
from __future__ import annotations

import re

IGNORE = {
    "файл", "файле", "файла", "этого", "данном", "каком", "чем", "кратко",
    "расскажи", "лекция", "лекции", "документ", "документа", "содержание",
    "пожалуйста", "подробно", "основные", "проанализируй", "изложи",
    "этот", "почему", "какие", "являются", "краткий", "основных",
}


def excerpt_for_question(text: str, question: str, limit: int = 13_000) -> str:
    if limit < 500:
        raise ValueError("Слишком маленький лимит контекста")
    # Include page labels in every chunk instead of losing them when splitting.
    pages = re.split(r"(?=\[Страница \d+\])", text)
    blocks: list[str] = []
    for page in pages:
        if not page.strip():
            continue
        marker = re.match(r"\[Страница \d+\]", page)
        title = marker.group(0) if marker else "[Текстовый документ]"
        content = page[len(marker.group(0)):] if marker else page
        for start in range(0, len(content), 1350):
            blocks.append(f"{title}\n{content[start:start + 1350]}")
    if not blocks:
        return ""

    tokens = {
        word for word in re.findall(r"[\wа-яё]{4,}", question.lower())
        if word not in IGNORE
    }
    broad = not tokens or bool(re.search(
        r"(?:обзор|перескаж|содержание|основн|раздел|кратк|главн|вывод|целом)",
        question.lower(),
    ))

    if broad:
        # Broad summaries sample from across the *whole* document, not only page 1.
        positions = [round(i * (len(blocks) - 1) / 9) for i in range(10)]
        selected = list(dict.fromkeys(positions))
    else:
        ranked = sorted(
            range(len(blocks)),
            key=lambda idx: sum(blocks[idx].lower().count(tok) for tok in tokens),
            reverse=True,
        )
        selected = list(dict.fromkeys([0] + ranked[:9]))
        selected.sort()

    result: list[str] = []
    used = 0
    for idx in selected:
        chunk = f"[Фрагмент {idx + 1} из {len(blocks)}]\n{blocks[idx].strip()}"
        if used + len(chunk) + 3 > limit:
            remainder = limit - used - 3
            if remainder > 200:
                result.append(chunk[:remainder])
            break
        result.append(chunk)
        used += len(chunk) + 3
    return "\n…\n".join(result)
