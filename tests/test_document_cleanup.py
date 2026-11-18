import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from document_cleanup import delete_owned_document


def setup_db(tmp_path):
    database = tmp_path / "state.sqlite3"
    documents = tmp_path / "texts"
    documents.mkdir()
    with sqlite3.connect(database) as con:
        con.execute("CREATE TABLE telegram_documents (doc_id TEXT PRIMARY KEY, user_id INT)")
        con.execute("CREATE TABLE telegram_sessions (user_id INT PRIMARY KEY, active_doc_id TEXT)")
        con.execute("INSERT INTO telegram_documents VALUES (?,?)", ("a" * 32, 111))
        con.execute("INSERT INTO telegram_documents VALUES (?,?)", ("b" * 32, 222))
        con.execute("INSERT INTO telegram_sessions VALUES (?,?)", (111, "a" * 32))
        con.execute("INSERT INTO telegram_sessions VALUES (?,?)", (222, "b" * 32))
    for uid, ident in [(111, "a" * 32), (222, "b" * 32)]:
        folder = documents / str(uid)
        folder.mkdir()
        (folder / f"{ident}.txt").write_text("Stored text", encoding="utf-8")
    return database, documents


def test_user_cannot_delete_another_users_document(tmp_path):
    db, txt = setup_db(tmp_path)
    touched = []
    assert not delete_owned_document(db, txt, 111, "b" * 32, lambda *args: touched.append(args))
    assert touched == []
    assert (txt / "222" / f"{'b' * 32}.txt").exists()
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM telegram_documents").fetchone()[0] == 2


def test_delete_removes_only_owned_document_and_active_state(tmp_path):
    db, txt = setup_db(tmp_path)
    called = []
    assert delete_owned_document(db, txt, 111, "a" * 32, lambda *args: called.append(args))
    assert called == [(111, "a" * 32)]
    assert not (txt / "111" / f"{'a' * 32}.txt").exists()
    assert (txt / "222" / f"{'b' * 32}.txt").exists()
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM telegram_documents").fetchone()[0] == 1
        assert con.execute("SELECT active_doc_id FROM telegram_sessions WHERE user_id=111").fetchone()[0] is None
        assert con.execute("SELECT active_doc_id FROM telegram_sessions WHERE user_id=222").fetchone()[0] == "b" * 32


def test_failed_vector_delete_keeps_records_and_file(tmp_path):
    db, txt = setup_db(tmp_path)

    def fails(*args):
        raise RuntimeError("Index deletion failed")

    with pytest.raises(RuntimeError, match="Index"):
        delete_owned_document(db, txt, 111, "a" * 32, fails)
    assert (txt / "111" / f"{'a' * 32}.txt").exists()
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM telegram_documents").fetchone()[0] == 2
