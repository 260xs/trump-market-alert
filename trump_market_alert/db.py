from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from .models import Alert, Event
from .utils import now_utc

log = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str, root_dir: Path):
        self.database_url = database_url
        self.root_dir = root_dir
        self.kind = "postgres" if database_url.startswith(("postgres://", "postgresql://")) else "sqlite"
        self.conn: Any = None

    def connect(self) -> None:
        if self.kind == "postgres":
            import psycopg

            # sslmode=require is normally included in Supabase/Neon connection strings.
            self.conn = psycopg.connect(self.database_url, connect_timeout=20, prepare_threshold=None)
            self.conn.autocommit = True
        else:
            path = self._sqlite_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(path)
            self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def _sqlite_path(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            raw = url.replace("sqlite:///", "", 1)
        elif url.startswith("sqlite://"):
            raw = url.replace("sqlite://", "", 1)
        else:
            raw = url
        p = Path(raw)
        if not p.is_absolute():
            p = self.root_dir / p
        return p

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()

    def _sql(self, sql: str) -> str:
        if self.kind == "postgres":
            return sql.replace("?", "%s")
        return sql

    def execute(self, sql: str, params: tuple[Any, ...] = ()):  # noqa: ANN201
        cur = self.conn.cursor()
        cur.execute(self._sql(sql), params)
        if self.kind == "sqlite":
            self.conn.commit()
        return cur

    def init_schema(self) -> None:
        if self.kind == "postgres":
            stmts = [
                """
                CREATE TABLE IF NOT EXISTS raw_items (
                    id BIGSERIAL PRIMARY KEY,
                    src TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    url TEXT,
                    published_at TEXT,
                    detected_at TEXT,
                    text TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    UNIQUE(src, item_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id BIGSERIAL PRIMARY KEY,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    quote TEXT NOT NULL,
                    source_platform TEXT,
                    source_link TEXT,
                    published_at TEXT,
                    detected_at TEXT,
                    entities_json TEXT,
                    signal TEXT,
                    confidence TEXT,
                    alert_type TEXT,
                    reason TEXT,
                    sent_ok BOOLEAN DEFAULT false,
                    sent_at TIMESTAMPTZ DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS state (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT now()
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS check_runs (
                    id BIGSERIAL PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sources_checked INTEGER DEFAULT 0,
                    events_seen INTEGER DEFAULT 0,
                    new_items INTEGER DEFAULT 0,
                    alerts_saved INTEGER DEFAULT 0,
                    errors_json TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
                """,
            ]
        else:
            stmts = [
                """
                CREATE TABLE IF NOT EXISTS raw_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    src TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    url TEXT,
                    published_at TEXT,
                    detected_at TEXT,
                    text TEXT,
                    raw_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(src, item_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    quote TEXT NOT NULL,
                    source_platform TEXT,
                    source_link TEXT,
                    published_at TEXT,
                    detected_at TEXT,
                    entities_json TEXT,
                    signal TEXT,
                    confidence TEXT,
                    alert_type TEXT,
                    reason TEXT,
                    sent_ok INTEGER DEFAULT 0,
                    sent_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS state (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS check_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sources_checked INTEGER DEFAULT 0,
                    events_seen INTEGER DEFAULT 0,
                    new_items INTEGER DEFAULT 0,
                    alerts_saved INTEGER DEFAULT 0,
                    errors_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """,
            ]
        for stmt in stmts:
            self.execute(stmt)

    def add_raw_item(self, ev: Event) -> bool:
        raw_json = json.dumps(ev.raw or {}, ensure_ascii=False, default=str)
        payload = (
            ev.src,
            ev.item_id,
            ev.url,
            ev.published_at.isoformat() if ev.published_at else None,
            ev.detected_at.isoformat(),
            ev.text,
            raw_json,
        )
        if self.kind == "postgres":
            cur = self.execute(
                """
                INSERT INTO raw_items(src, item_id, url, published_at, detected_at, text, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(src, item_id) DO NOTHING
                """,
                payload,
            )
            return cur.rowcount == 1

        cur = self.execute(
            """
            INSERT OR IGNORE INTO raw_items(src, item_id, url, published_at, detected_at, text, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        return cur.rowcount == 1

    def alert_exists(self, dedupe_key: str) -> bool:
        cur = self.execute("SELECT 1 FROM alerts WHERE dedupe_key = ? LIMIT 1", (dedupe_key,))
        return cur.fetchone() is not None

    def save_alert(self, alert: Alert, sent_ok: bool) -> bool:
        ents = [
            {
                "name": e.name,
                "kind": e.kind,
                "relation": e.relation,
                "assets": [{"symbol": a.symbol, "type": a.type, "explanation": a.explanation} for a in e.assets],
            }
            for e in alert.entities
        ]
        payload = (
            alert.dedupe_key,
            alert.quote,
            alert.source_platform,
            alert.source_link,
            alert.published_at.isoformat() if alert.published_at else None,
            alert.detected_at.isoformat(),
            json.dumps(ents, ensure_ascii=False),
            alert.signal,
            alert.confidence,
            alert.alert_type,
            alert.reason,
            bool(sent_ok) if self.kind == "postgres" else int(bool(sent_ok)),
        )
        if self.kind == "postgres":
            cur = self.execute(
                """
                INSERT INTO alerts(dedupe_key, quote, source_platform, source_link, published_at,
                                   detected_at, entities_json, signal, confidence, alert_type, reason, sent_ok)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(dedupe_key) DO NOTHING
                """,
                payload,
            )
            return cur.rowcount == 1
        cur = self.execute(
            """
            INSERT OR IGNORE INTO alerts(dedupe_key, quote, source_platform, source_link, published_at,
                                         detected_at, entities_json, signal, confidence, alert_type, reason, sent_ok)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            payload,
        )
        return cur.rowcount == 1

    def get_state(self, key: str) -> str | None:
        cur = self.execute("SELECT v FROM state WHERE k = ?", (key,))
        row = cur.fetchone()
        if row is None:
            return None
        return row[0] if self.kind == "postgres" else row["v"]

    def set_state(self, key: str, value: str) -> None:
        if self.kind == "postgres":
            self.execute(
                """
                INSERT INTO state(k, v, updated_at) VALUES (?, ?, now())
                ON CONFLICT(k) DO UPDATE SET v = EXCLUDED.v, updated_at = now()
                """,
                (key, value),
            )
        else:
            self.execute(
                """
                INSERT INTO state(k, v, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(k) DO UPDATE SET v = excluded.v, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )

    def record_check_run(
        self,
        *,
        started_at: str,
        finished_at: str,
        status: str,
        sources_checked: int,
        events_seen: int,
        new_items: int,
        alerts_saved: int,
        errors: list[dict[str, str]],
    ) -> None:
        self.execute(
            """
            INSERT INTO check_runs(started_at, finished_at, status, sources_checked, events_seen,
                                   new_items, alerts_saved, errors_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started_at,
                finished_at,
                status,
                sources_checked,
                events_seen,
                new_items,
                alerts_saved,
                json.dumps(errors, ensure_ascii=False),
            ),
        )
        self.set_state("last_check_started_at", started_at)
        self.set_state("last_check_finished_at", finished_at)
        self.set_state("last_check_status", status)
        self.set_state("last_check_errors", json.dumps(errors, ensure_ascii=False))

    def cleanup_old_raw_items(self, retention_days: int) -> int:
        if retention_days <= 0:
            return 0
        if self.kind == "postgres":
            cur = self.execute(
                "DELETE FROM raw_items WHERE created_at < now() - (? * interval '1 day')",
                (retention_days,),
            )
            return int(cur.rowcount or 0)
        cur = self.execute(
            "DELETE FROM raw_items WHERE created_at < datetime('now', ?)",
            (f"-{retention_days} days",),
        )
        return int(cur.rowcount or 0)

    def cleanup_old_check_runs(self, retention_days: int = 30) -> int:
        if retention_days <= 0:
            return 0
        if self.kind == "postgres":
            cur = self.execute(
                "DELETE FROM check_runs WHERE created_at < now() - (? * interval '1 day')",
                (retention_days,),
            )
            return int(cur.rowcount or 0)
        cur = self.execute(
            "DELETE FROM check_runs WHERE created_at < datetime('now', ?)",
            (f"-{retention_days} days",),
        )
        return int(cur.rowcount or 0)

    def stats(self) -> dict[str, Any]:
        def count(table: str) -> int:
            cur = self.execute(f"SELECT COUNT(*) FROM {table}")
            row = cur.fetchone()
            return int(row[0] if self.kind == "postgres" else row[0])

        return {
            "database_kind": self.kind,
            "raw_items": count("raw_items"),
            "alerts": count("alerts"),
            "check_runs": count("check_runs"),
            "last_check_finished_at": self.get_state("last_check_finished_at"),
            "last_check_status": self.get_state("last_check_status"),
            "reported_at": now_utc().isoformat(),
        }
