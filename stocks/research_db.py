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
