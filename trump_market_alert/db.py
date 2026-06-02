from __future__ import annotations

import logging
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.types.json import Jsonb

from .extract import stable_hash
from .models import Alert, SourceItem

LOG = logging.getLogger(__name__)


class Database:
    """Small Postgres persistence layer for alert history and deduplication.

    The init() method is intentionally migration-safe. Earlier versions of this
    project created a different raw_items table. Because raw_items is only a
    scan cache, we safely rebuild it if the existing schema is incompatible.
    Alert history is kept in alert_history and is not dropped.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.conn: Connection[Any] | None = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def connect(self) -> None:
        # prepare_threshold=None avoids prepared-statement issues with common
        # hosted Postgres poolers, including Supabase pooler connections.
        self.conn = psycopg.connect(
            self.database_url,
            autocommit=True,
            connect_timeout=20,
            prepare_threshold=None,
        )

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def _conn(self) -> Connection[Any]:
        if self.conn is None:
            raise RuntimeError("Database is not connected")
        return self.conn

    def _table_exists(self, table_name: str) -> bool:
        with self._conn().cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
            row = cur.fetchone()
            return bool(row and row[0])

    def _columns(self, table_name: str) -> set[str]:
        with self._conn().cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table_name,),
            )
            return {str(row[0]) for row in cur.fetchall()}

    def _raw_items_schema_is_current(self) -> bool:
        if not self._table_exists("raw_items"):
            return True

        cols = self._columns("raw_items")
        required = {
            "item_key",
            "source_name",
            "source_type",
            "source_url",
            "title",
            "content_hash",
            "first_seen_at",
            "last_seen_at",
        }
        return required.issubset(cols)

    def init(self) -> None:
        conn = self._conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_history (
                    fingerprint TEXT PRIMARY KEY,
                    quote TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    time_published TIMESTAMPTZ,
                    time_detected TIMESTAMPTZ NOT NULL,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    matched_alias TEXT NOT NULL,
                    related_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
                    signal TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            # If raw_items was created by an older version, it may not contain
            # last_seen_at or item_key. Rebuild only this cache table so the
            # monitor can continue without manually resetting Supabase.
            if not self._raw_items_schema_is_current():
                LOG.warning("Rebuilding legacy raw_items table with current schema")
                cur.execute("DROP TABLE IF EXISTS raw_items")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_items (
                    item_key TEXT PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    title TEXT,
                    content_hash TEXT NOT NULL,
                    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS check_runs (
                    id BIGSERIAL PRIMARY KEY,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    finished_at TIMESTAMPTZ,
                    status TEXT NOT NULL DEFAULT 'running',
                    items_seen INTEGER NOT NULL DEFAULT 0,
                    alerts_sent INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                )
                """
            )

            # Migration safety for partially created check_runs tables.
            cur.execute("ALTER TABLE check_runs ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ")
            cur.execute("ALTER TABLE check_runs ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'running'")
            cur.execute("ALTER TABLE check_runs ADD COLUMN IF NOT EXISTS items_seen INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE check_runs ADD COLUMN IF NOT EXISTS alerts_sent INTEGER NOT NULL DEFAULT 0")
            cur.execute("ALTER TABLE check_runs ADD COLUMN IF NOT EXISTS error TEXT")

            cur.execute("CREATE INDEX IF NOT EXISTS idx_alert_history_created_at ON alert_history (created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_raw_items_last_seen_at ON raw_items (last_seen_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_check_runs_started_at ON check_runs (started_at DESC)")

    def start_run(self) -> int:
        with self._conn().cursor() as cur:
            cur.execute("INSERT INTO check_runs DEFAULT VALUES RETURNING id")
            row = cur.fetchone()
            if not row:
                raise RuntimeError("Failed to create check run")
            return int(row[0])

    def finish_run(self, run_id: int, status: str, items_seen: int, alerts_sent: int, error: str | None = None) -> None:
        with self._conn().cursor() as cur:
            cur.execute(
                """
                UPDATE check_runs
                SET finished_at = now(), status = %s, items_seen = %s, alerts_sent = %s, error = %s
                WHERE id = %s
                """,
                (status, items_seen, alerts_sent, error[:2000] if error else None, run_id),
            )

    def upsert_raw_item(self, item: SourceItem, content_hash: str) -> None:
        key = stable_hash(item.source_type, item.source_name, item.item_id)
        with self._conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO raw_items (item_key, source_name, source_type, source_url, title, content_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_key) DO UPDATE
                SET last_seen_at = now(), content_hash = EXCLUDED.content_hash, title = EXCLUDED.title
                """,
                (key, item.source_name, item.source_type, item.url, item.title[:500], content_hash),
            )

    def insert_alert_if_new(self, alert: Alert) -> bool:
        with self._conn().cursor() as cur:
            cur.execute(
                """
                INSERT INTO alert_history (
                    fingerprint, quote, source_name, source_type, source_url, time_published,
                    time_detected, entity_name, entity_type, matched_alias, related_assets,
                    signal, confidence, alert_type, reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO NOTHING
                """,
                (
                    alert.fingerprint,
                    alert.quote,
                    alert.source_name,
                    alert.source_type,
                    alert.source_url,
                    alert.time_published,
                    alert.time_detected,
                    alert.entity_name,
                    alert.entity_type,
                    alert.matched_alias,
                    Jsonb(alert.assets_as_dicts()),
                    alert.signal,
                    alert.confidence,
                    alert.alert_type,
                    alert.reason,
                ),
            )
            return cur.rowcount == 1

    def cleanup(self, raw_days: int = 180, run_days: int = 30) -> None:
        with self._conn().cursor() as cur:
            cur.execute("DELETE FROM raw_items WHERE last_seen_at < now() - (%s || ' days')::interval", (raw_days,))
            cur.execute("DELETE FROM check_runs WHERE started_at < now() - (%s || ' days')::interval", (run_days,))
