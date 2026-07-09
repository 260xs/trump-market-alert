from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).astimezone(timezone.utc).isoformat()


class StockResearchDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS stock_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    setup_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    sent_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_stock_alerts_key_time ON stock_alerts(setup_key, sent_at);
                CREATE INDEX IF NOT EXISTS idx_stock_alerts_ticker_signal_time ON stock_alerts(ticker, signal, sent_at);

                CREATE TABLE IF NOT EXISTS top_candidates (
                    ticker TEXT PRIMARY KEY,
                    score REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    selected_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS stock_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    scanned_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_stock_scans_ticker_time ON stock_scans(ticker, scanned_at);
                CREATE INDEX IF NOT EXISTS idx_stock_scans_time ON stock_scans(scanned_at);

                CREATE TABLE IF NOT EXISTS active_stock_setups (
                    ticker TEXT PRIMARY KEY,
                    setup_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    opened_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                );
                CREATE INDEX IF NOT EXISTS idx_active_stock_setups_status_time ON active_stock_setups(status, updated_at);
                """
            )

    def seen_recent(self, setup_key: str, hours: int) -> bool:
        cutoff = iso(utc_now() - timedelta(hours=hours))
        with self.connect() as con:
            row = con.execute(
                "SELECT id FROM stock_alerts WHERE setup_key=? AND sent_at>=? LIMIT 1",
                (setup_key, cutoff),
            ).fetchone()
            return bool(row)

    def seen_ticker_signal_recent(self, ticker: str, signal: str, hours: int) -> bool:
        cutoff = iso(utc_now() - timedelta(hours=hours))
        with self.connect() as con:
            row = con.execute(
                "SELECT id FROM stock_alerts WHERE ticker=? AND signal=? AND sent_at>=? LIMIT 1",
                (ticker, signal, cutoff),
            ).fetchone()
            return bool(row)

    def store_alert(self, ticker: str, signal: str, setup_key: str, payload: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                "INSERT INTO stock_alerts (ticker, signal, setup_key, payload_json, sent_at) VALUES (?, ?, ?, ?, ?)",
                (ticker, signal, setup_key, json.dumps(payload, default=str), iso()),
            )

    def store_scan(self, ticker: str, payload: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                "INSERT INTO stock_scans (ticker, payload_json, scanned_at) VALUES (?, ?, ?)",
                (ticker, json.dumps(payload, default=str), iso()),
            )
            self._prune_old_scans(con)

    def _prune_old_scans(self, con: sqlite3.Connection, days: int = 14, max_rows: int = 5000) -> None:
        cutoff = iso(utc_now() - timedelta(days=days))
        con.execute("DELETE FROM stock_scans WHERE scanned_at < ?", (cutoff,))
        row = con.execute("SELECT COUNT(*) AS count FROM stock_scans").fetchone()
        if row and int(row["count"]) > max_rows:
            rows_to_delete = int(row["count"]) - max_rows
            con.execute(
                "DELETE FROM stock_scans WHERE id IN (SELECT id FROM stock_scans ORDER BY scanned_at ASC LIMIT ?)",
                (rows_to_delete,),
            )

    def open_entry_setup(self, ticker: str, setup_key: str, payload: dict[str, Any]) -> None:
        now = iso()
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO active_stock_setups (ticker, setup_key, payload_json, opened_at, updated_at, status)
                VALUES (?, ?, ?, ?, ?, 'open')
                ON CONFLICT(ticker) DO UPDATE SET
                    setup_key=excluded.setup_key,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at,
                    status='open'
                """,
                (ticker, setup_key, json.dumps(payload, default=str), now, now),
            )

    def load_open_entry_setup(self, ticker: str) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute(
                "SELECT payload_json FROM active_stock_setups WHERE ticker=? AND status='open' LIMIT 1",
                (ticker,),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(str(row["payload_json"]))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def close_entry_setup(self, ticker: str, payload: dict[str, Any]) -> None:
        with self.connect() as con:
            con.execute(
                "UPDATE active_stock_setups SET status='closed', payload_json=?, updated_at=? WHERE ticker=? AND status='open'",
                (json.dumps(payload, default=str), iso(), ticker),
            )

    def save_candidates(self, candidates: list[dict[str, Any]]) -> None:
        with self.connect() as con:
            con.execute("DELETE FROM top_candidates")
            for rank, item in enumerate(candidates, start=1):
                con.execute(
                    "INSERT INTO top_candidates (ticker, score, rank, payload_json, selected_at) VALUES (?, ?, ?, ?, ?)",
                    (item["ticker"], float(item["score"]), rank, json.dumps(item, default=str), iso()),
                )

    def load_candidate_tickers(self) -> list[str]:
        with self.connect() as con:
            rows = con.execute("SELECT ticker FROM top_candidates ORDER BY rank ASC").fetchall()
            return [str(r["ticker"]) for r in rows]
