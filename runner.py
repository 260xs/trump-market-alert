from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

try:
    import psycopg
except Exception:  # allows SQLite-only tests before dependencies are installed
    psycopg = None

from .models import AlertRecord, SourceItem
from .utils import now_utc, stable_hash

LOG = logging.getLogger(__name__)


class AlertDB:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_sqlite = database_url.startswith("sqlite:///") or database_url in {"sqlite://", "sqlite"}
        self._sqlite_path: Path | None = None
        if self.is_sqlite:
            raw = database_url.replace("sqlite:///", "", 1).replace("sqlite://", "", 1) or "data/alerts.db"
            self._sqlite_path = Path(raw)
            if not self._sqlite_path.is_absolute():
                self._sqlite_path = Path.cwd() / self._sqlite_path
            self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[Any]:
        if self.is_sqlite:
            assert self._sqlite_path is not None
            conn = sqlite3.connect(str(self._sqlite_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        else:
            if psycopg is None:
                raise RuntimeError("psycopg is required for Postgres DATABASE_URL. Install requirements.txt.")
            conn = psycopg.connect(self.database_url, connect_timeout=20, prepare_threshold=None)
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            if self.is_sqlite:
                cur.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS raw_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        platform TEXT,
                        url TEXT,
                        text_hash TEXT NOT NULL,
                        text TEXT NOT NULL,
                        published_at TEXT,
                        detected_at TEXT,
                        source_type TEXT,
                        raw_json TEXT,
                        inserted_at TEXT NOT NULL,
                        UNIQUE(source, source_id)
                    );
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dedupe_key TEXT UNIQUE NOT NULL,
                        source TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        platform TEXT,
                        url TEXT,
                        quote TEXT NOT NULL,
                        published_at TEXT,
                        detected_at TEXT,
                        entities_json TEXT,
                        assets_json TEXT,
                        signal TEXT,
                        confidence TEXT,
                        alert_type TEXT,
                        reason TEXT,
                        created_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS source_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        items_seen INTEGER DEFAULT 0,
                        alerts_sent INTEGER DEFAULT 0,
                        error TEXT
                    );
                    """
                )
            else:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS raw_items (
                        id BIGSERIAL PRIMARY KEY,
                        source TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        platform TEXT,
                        url TEXT,
                        text_hash TEXT NOT NULL,
                        text TEXT NOT NULL,
                        published_at TIMESTAMPTZ,
                        detected_at TIMESTAMPTZ,
                        source_type TEXT,
                        raw_json TEXT,
                        inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        UNIQUE(source, source_id)
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        id BIGSERIAL PRIMARY KEY,
                        dedupe_key TEXT UNIQUE NOT NULL,
                        source TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        platform TEXT,
                        url TEXT,
                        quote TEXT NOT NULL,
                        published_at TIMESTAMPTZ,
                        detected_at TIMESTAMPTZ,
                        entities_json TEXT,
                        assets_json TEXT,
                        signal TEXT,
                        confidence TEXT,
                        alert_type TEXT,
                        reason TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS source_runs (
                        id BIGSERIAL PRIMARY KEY,
                        source TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        finished_at TIMESTAMPTZ,
                        items_seen INTEGER DEFAULT 0,
                        alerts_sent INTEGER DEFAULT 0,
                        error TEXT
                    )
                    """
                )

    def insert_raw_item(self, item: SourceItem) -> bool:
        h = stable_hash(item.text, n=40)
        with self.connect() as conn:
            cur = conn.cursor()
            if self.is_sqlite:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO raw_items
                    (source, source_id, platform, url, text_hash, text, published_at, detected_at, source_type, raw_json, inserted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.source,
                        item.source_id,
                        item.platform,
                        item.url,
                        h,
                        item.text,
                        _dt(item.published_at),
                        _dt(item.detected_at),
                        item.source_type,
                        json.dumps(item.raw, default=str),
                        _dt(now_utc()),
                    ),
                )
                return cur.rowcount > 0
            cur.execute(
                """
                INSERT INTO raw_items
                (source, source_id, platform, url, text_hash, text, published_at, detected_at, source_type, raw_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source, source_id) DO NOTHING
                """,
                (
                    item.source,
                    item.source_id,
                    item.platform,
                    item.url,
                    h,
                    item.text,
                    item.published_at,
                    item.detected_at,
                    item.source_type,
                    json.dumps(item.raw, default=str),
                ),
            )
            return cur.rowcount > 0

    def alert_exists(self, dedupe_key: str) -> bool:
        with self.connect() as conn:
            cur = conn.cursor()
            sql = "SELECT 1 FROM alerts WHERE dedupe_key = ? LIMIT 1" if self.is_sqlite else "SELECT 1 FROM alerts WHERE dedupe_key = %s LIMIT 1"
            cur.execute(sql, (dedupe_key,))
            return cur.fetchone() is not None

    def insert_alert(self, alert: AlertRecord) -> bool:
        d = alert.decision
        item = alert.item
        entities = [
            {
                "name": h.name,
                "kind": h.kind,
                "matched_alias": h.matched_alias,
                "assets": [{"symbol": a.symbol, "kind": a.kind, "explanation": a.explanation} for a in h.assets],
            }
            for h in d.entities
        ]
        assets = []
        for h in d.entities:
            for a in h.assets:
                assets.append({"symbol": a.symbol, "kind": a.kind, "explanation": a.explanation})
        with self.connect() as conn:
            cur = conn.cursor()
            vals = (
                alert.dedupe_key,
                item.source,
                item.source_id,
                item.platform,
                item.url,
                d.quote,
                _dt(item.published_at) if self.is_sqlite else item.published_at,
                _dt(item.detected_at) if self.is_sqlite else item.detected_at,
                json.dumps(entities, default=str),
                json.dumps(assets, default=str),
                d.signal,
                d.confidence,
                d.alert_type,
                d.reason,
                _dt(now_utc()) if self.is_sqlite else now_utc(),
            )
            if self.is_sqlite:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO alerts
                    (dedupe_key, source, source_id, platform, url, quote, published_at, detected_at,
                     entities_json, assets_json, signal, confidence, alert_type, reason, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    vals,
                )
                return cur.rowcount > 0
            cur.execute(
                """
                INSERT INTO alerts
                (dedupe_key, source, source_id, platform, url, quote, published_at, detected_at,
                 entities_json, assets_json, signal, confidence, alert_type, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (dedupe_key) DO NOTHING
                """,
                vals,
            )
            return cur.rowcount > 0

    def set_state(self, key: str, value: str) -> None:
        with self.connect() as conn:
            cur = conn.cursor()
            if self.is_sqlite:
                cur.execute("INSERT OR REPLACE INTO state (key, value, updated_at) VALUES (?, ?, ?)", (key, value, _dt(now_utc())))
            else:
                cur.execute(
                    """
                    INSERT INTO state (key, value, updated_at) VALUES (%s, %s, now())
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
                    """,
                    (key, value),
                )

    def get_state(self, key: str) -> str | None:
        with self.connect() as conn:
            cur = conn.cursor()
            sql = "SELECT value FROM state WHERE key = ?" if self.is_sqlite else "SELECT value FROM state WHERE key = %s"
            cur.execute(sql, (key,))
            row = cur.fetchone()
            if not row:
                return None
            return row[0]

    def cleanup(self, raw_days: int = 180, runs_days: int = 30) -> None:
        raw_cut = now_utc() - timedelta(days=raw_days)
        run_cut = now_utc() - timedelta(days=runs_days)
        with self.connect() as conn:
            cur = conn.cursor()
            if self.is_sqlite:
                cur.execute("DELETE FROM raw_items WHERE inserted_at < ?", (_dt(raw_cut),))
                cur.execute("DELETE FROM source_runs WHERE started_at < ?", (_dt(run_cut),))
            else:
                cur.execute("DELETE FROM raw_items WHERE inserted_at < %s", (raw_cut,))
                cur.execute("DELETE FROM source_runs WHERE started_at < %s", (run_cut,))


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
