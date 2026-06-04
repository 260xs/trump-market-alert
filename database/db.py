from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterator, Any
from difflib import SequenceMatcher

from database.models import Statement, EntityMatch, Signal


def iso(dt: datetime | None = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA busy_timeout=30000")
            yield con
            con.commit()
        finally:
            con.close()

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS watched_people (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    aliases TEXT NOT NULL,
                    role TEXT NOT NULL,
                    market_impact_score INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    person_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    polling_interval_seconds INTEGER NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    last_checked_at TEXT,
                    FOREIGN KEY(person_id) REFERENCES watched_people(id)
                );

                CREATE TABLE IF NOT EXISTS raw_statements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    speaker_name TEXT NOT NULL,
                    statement_text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    transcript_timestamp TEXT,
                    source_confidence REAL NOT NULL,
                    speaker_confidence REAL NOT NULL,
                    quote_confidence REAL NOT NULL,
                    quote_hash TEXT NOT NULL,
                    normalized_quote_hash TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    platform_item_id TEXT,
                    is_live INTEGER NOT NULL DEFAULT 0,
                    live_offset_seconds INTEGER,
                    raw_metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS detected_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement_id INTEGER NOT NULL,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    mapped_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    entity_confidence REAL NOT NULL,
                    direct_or_inferred TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    FOREIGN KEY(statement_id) REFERENCES raw_statements(id)
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement_id INTEGER NOT NULL,
                    speaker_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    lane TEXT NOT NULL,
                    telegram_sent INTEGER NOT NULL DEFAULT 0,
                    telegram_message_id TEXT,
                    sent_at TEXT,
                    duplicate_key TEXT NOT NULL UNIQUE,
                    reason TEXT NOT NULL,
                    FOREIGN KEY(statement_id) REFERENCES raw_statements(id)
                );

                CREATE TABLE IF NOT EXISTS dedupe_keys (
                    key TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS source_state (
                    source_id TEXT PRIMARY KEY,
                    last_checked_at TEXT,
                    last_success_at TEXT,
                    last_error_at TEXT,
                    last_error TEXT,
                    run_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS scheduler_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    sources_checked INTEGER NOT NULL DEFAULT 0,
                    statements_seen INTEGER NOT NULL DEFAULT 0,
                    alerts_sent INTEGER NOT NULL DEFAULT 0,
                    errors INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_raw_statement_hash ON raw_statements(normalized_quote_hash);
                CREATE INDEX IF NOT EXISTS idx_raw_statement_speaker_time ON raw_statements(speaker_name, published_at);
                CREATE INDEX IF NOT EXISTS idx_alerts_duplicate_key ON alerts(duplicate_key);
                CREATE INDEX IF NOT EXISTS idx_alerts_speaker_ticker_time ON alerts(speaker_name, ticker, signal, sent_at);
                CREATE INDEX IF NOT EXISTS idx_source_state_last_checked ON source_state(last_checked_at);
                """
            )

    def upsert_watchlist(self, people: list[dict[str, Any]]) -> None:
        with self.connect() as con:
            for person in people:
                con.execute(
                    """
                    INSERT INTO watched_people (id, name, aliases, role, market_impact_score, enabled)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        aliases=excluded.aliases,
                        role=excluded.role,
                        market_impact_score=excluded.market_impact_score,
                        enabled=excluded.enabled
                    """,
                    (
                        person["id"],
                        person["full_name"],
                        json.dumps(person.get("aliases", [])),
                        person.get("role", ""),
                        int(person.get("market_impact_score", 0)),
                        1 if person.get("enabled", True) else 0,
                    ),
                )
                for src in person.get("sources", []):
                    url = src.get("url") or src.get("channel_id") or ""
                    con.execute(
                        """
                        INSERT INTO sources (id, person_id, platform, source_url, source_type, priority, polling_interval_seconds, enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            platform=excluded.platform,
                            source_url=excluded.source_url,
                            source_type=excluded.source_type,
                            priority=excluded.priority,
                            polling_interval_seconds=excluded.polling_interval_seconds,
                            enabled=excluded.enabled
                        """,
                        (
                            src["id"],
                            person["id"],
                            src.get("platform", "unknown"),
                            url,
                            src.get("source_type", "unknown"),
                            src.get("priority", "medium"),
                            int(src.get("polling_interval_seconds", 600)),
                            1 if src.get("enabled", True) else 0,
                        ),
                    )

    def start_scheduler_run(self) -> int:
        with self.connect() as con:
            cur = con.execute("INSERT INTO scheduler_runs (started_at, status) VALUES (?, 'running')", (iso(),))
            return int(cur.lastrowid)

    def finish_scheduler_run(self, run_id: int, status: str, sources_checked: int, statements_seen: int, alerts_sent: int, errors: int) -> None:
        with self.connect() as con:
            con.execute(
                """
                UPDATE scheduler_runs
                SET finished_at=?, status=?, sources_checked=?, statements_seen=?, alerts_sent=?, errors=?
                WHERE id=?
                """,
                (iso(), status, sources_checked, statements_seen, alerts_sent, errors, run_id),
            )

    def update_source_success(self, source_id: str) -> None:
        now = iso()
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO source_state (source_id, last_checked_at, last_success_at, run_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(source_id) DO UPDATE SET
                    last_checked_at=excluded.last_checked_at,
                    last_success_at=excluded.last_success_at,
                    run_count=source_state.run_count + 1
                """,
                (source_id, now, now),
            )
            con.execute("UPDATE sources SET last_checked_at=? WHERE id=?", (now, source_id))

    def update_source_error(self, source_id: str, error: str) -> None:
        now = iso()
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO source_state (source_id, last_checked_at, last_error_at, last_error, run_count, failure_count)
                VALUES (?, ?, ?, ?, 1, 1)
                ON CONFLICT(source_id) DO UPDATE SET
                    last_checked_at=excluded.last_checked_at,
                    last_error_at=excluded.last_error_at,
                    last_error=excluded.last_error,
                    run_count=source_state.run_count + 1,
                    failure_count=source_state.failure_count + 1
                """,
                (source_id, now, now, error[:1000]),
            )

    def dedupe_exists(self, key: str) -> bool:
        with self.connect() as con:
            row = con.execute("SELECT key FROM dedupe_keys WHERE key=?", (key,)).fetchone()
            return bool(row)

    def mark_dedupe(self, key: str, kind: str) -> None:
        now = iso()
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO dedupe_keys (key, kind, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    count=dedupe_keys.count + 1
                """,
                (key, kind, now, now),
            )

    def dedupe_seen(self, key: str, kind: str) -> bool:
        if self.dedupe_exists(key):
            self.mark_dedupe(key, kind)
            return True
        self.mark_dedupe(key, kind)
        return False

    def recent_similar_alert_exists(
        self,
        speaker_name: str,
        ticker: str,
        signal: str,
        normalized_text: str,
        hours: int = 48,
        threshold: float = 0.92,
    ) -> bool:
        cutoff = iso(datetime.now(timezone.utc) - timedelta(hours=hours))
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT rs.normalized_text
                FROM alerts a
                JOIN raw_statements rs ON rs.id = a.statement_id
                WHERE a.speaker_name=? AND a.ticker=? AND a.signal=? AND a.sent_at IS NOT NULL AND a.sent_at>=?
                ORDER BY a.sent_at DESC
                LIMIT 50
                """,
                (speaker_name, ticker, signal, cutoff),
            ).fetchall()
        return any(SequenceMatcher(None, normalized_text, str(row["normalized_text"])).ratio() >= threshold for row in rows)

    def store_statement(self, stmt: Statement, normalized_text: str, quote_hash: str, normalized_hash: str) -> int:
        with self.connect() as con:
            cur = con.execute(
                """
                INSERT INTO raw_statements (
                    person_id, source_id, speaker_name, statement_text, normalized_text,
                    source_url, platform, published_at, detected_at, transcript_timestamp,
                    source_confidence, speaker_confidence, quote_confidence, quote_hash,
                    normalized_quote_hash, source_type, platform_item_id, is_live,
                    live_offset_seconds, raw_metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stmt.person_id,
                    stmt.source_id,
                    stmt.speaker_name,
                    stmt.statement_text,
                    normalized_text,
                    stmt.source_url,
                    stmt.platform,
                    iso(stmt.published_at),
                    iso(stmt.detected_at),
                    stmt.transcript_timestamp,
                    stmt.source_confidence,
                    stmt.speaker_confidence,
                    stmt.quote_confidence,
                    quote_hash,
                    normalized_hash,
                    stmt.source_type,
                    stmt.platform_item_id,
                    1 if stmt.is_live else 0,
                    stmt.live_offset_seconds,
                    json.dumps(stmt.raw_metadata, ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def store_entity(self, statement_id: int, entity: EntityMatch) -> int:
        with self.connect() as con:
            cur = con.execute(
                """
                INSERT INTO detected_entities (
                    statement_id, entity_name, entity_type, mapped_name, ticker,
                    asset_type, entity_confidence, direct_or_inferred, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    statement_id,
                    entity.entity_name,
                    entity.entity_type,
                    entity.mapped_name,
                    entity.ticker,
                    entity.asset_type,
                    entity.entity_confidence,
                    entity.direct_or_inferred,
                    entity.reason,
                ),
            )
            return int(cur.lastrowid)

    def store_alert(self, statement_id: int, stmt: Statement, entity: EntityMatch, signal: Signal, lane: str, duplicate_key: str, reason: str, telegram_sent: bool, telegram_message_id: str = "") -> int | None:
        try:
            with self.connect() as con:
                cur = con.execute(
                    """
                    INSERT INTO alerts (
                        statement_id, speaker_name, ticker, asset, signal, confidence,
                        lane, telegram_sent, telegram_message_id, sent_at, duplicate_key, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        statement_id,
                        stmt.speaker_name,
                        entity.ticker,
                        entity.mapped_name,
                        signal.signal,
                        "High" if lane == "strict" else "Provisional",
                        lane,
                        1 if telegram_sent else 0,
                        telegram_message_id,
                        iso() if telegram_sent else None,
                        duplicate_key,
                        reason,
                    ),
                )
                return int(cur.lastrowid)
        except sqlite3.IntegrityError:
            return None


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
