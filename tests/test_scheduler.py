from __future__ import annotations

from pathlib import Path

from config import Settings
from database.db import Database


def test_database_schema_initializes(tmp_path: Path):
    db = Database(tmp_path / "x.sqlite3")
    db.init()
    with db.connect() as con:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "raw_statements" in tables
    assert "alerts" in tables
    assert "source_state" in tables
