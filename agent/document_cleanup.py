"""Ownership-scoped deletion of Telegram document records and saved text."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Callable


def delete_owned_document(
    state_file: Path,
    text_dir: Path,
    user_id: int,
    doc_id: str,
    delete_vectors: Callable[[int, str], None],
) -> bool:
    """Do not touch another user's text, SQLite row or LanceDB vectors."""
    if type(user_id) is not int or user_id <= 0 or not re.fullmatch(r"[a-f0-9]{32}", doc_id):
        raise ValueError("Invalid document ownership data")

    with sqlite3.connect(state_file, timeout=30) as con:
        found = con.execute(
            "SELECT 1 FROM telegram_documents WHERE user_id=? AND doc_id=?",
            (user_id, doc_id),
        ).fetchone()
    if not found:
        return False

    # Strong invariant: never claim deletion if the search index deletion fails.
    delete_vectors(user_id, doc_id)

    with sqlite3.connect(state_file, timeout=30) as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "DELETE FROM telegram_documents WHERE user_id=? AND doc_id=?",
            (user_id, doc_id),
        )
        con.execute(
            "UPDATE telegram_sessions SET active_doc_id=NULL "
            "WHERE user_id=? AND active_doc_id=?",
            (user_id, doc_id),
        )

    target = text_dir / str(user_id) / f"{doc_id}.txt"
    if target.is_symlink():
        raise ValueError("Unexpected symlink in document storage")
    target.unlink(missing_ok=True)
    return True
