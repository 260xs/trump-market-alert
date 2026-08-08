from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


BLOCK_REASONS = {
    "major_event_pending",
    "event_time_uncertain",
    "earnings_risk",
    "corporate_action_pending",
    "competing_catalyst",
    "market_regime_uncertain",
    "event_data_stale",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).astimezone(timezone.utc).isoformat()


def parse_utc(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local_to_utc(local_time: str, timezone_name: str) -> str:
    dt = datetime.fromisoformat(local_time)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(timezone_name))
    return iso(dt)


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    event_type: str
    source_url: str
    source_confidence: float
    expected_impact: str
    event_time_utc: str | None = None
    window_start_utc: str | None = None
    window_end_utc: str | None = None
    time_confirmed: bool = False
    affected_country: str | None = None
    market: str | None = None
    sector: str | None = None
    company: str | None = None
    ticker: str | None = None
    asset: str | None = None
    status: str = "scheduled"
    source_name: str | None = None
    collection_cursor: str | None = None
    last_verified_at: str | None = None

    def normalized(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("event_time_utc", "window_start_utc", "window_end_utc", "last_verified_at"):
            if data[key]:
                data[key] = iso(parse_utc(data[key]))
        if not data["last_verified_at"]:
            data["last_verified_at"] = iso()
        if data["ticker"]:
            data["ticker"] = str(data["ticker"]).upper()
        if data["asset"]:
            data["asset"] = str(data["asset"]).upper()
        data["status"] = str(data["status"] or "scheduled").lower()
        return data


@dataclass(frozen=True)
class RegimeSnapshot:
    state: str
    confidence: float
    data_quality: str
    inputs: dict[str, Any]
    calculated_at: str | None = None

    def normalized(self) -> dict[str, Any]:
        state = self.state if self.state in {"Bullish", "Bearish", "Mixed", "Uncertain"} else "Uncertain"
        data = asdict(self)
        data["state"] = state
        data["calculated_at"] = iso(parse_utc(data["calculated_at"]))
        return data


@dataclass(frozen=True)
class RiskGateDecision:
    allowed: bool
    reason: str | None
    event_id: int | None = None
    details: str = ""


class EventRiskDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        return con

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS event_sources (
                    source_name TEXT PRIMARY KEY,
                    official_url TEXT NOT NULL,
                    official_status TEXT NOT NULL,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    update_frequency TEXT,
                    rate_limit TEXT,
                    parser_compatibility TEXT,
                    cursor_behavior TEXT,
                    duplicate_policy TEXT,
                    last_checked_at TEXT NOT NULL,
                    last_success_at TEXT,
                    last_error TEXT
                );

                CREATE TABLE IF NOT EXISTS event_calendar (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stable_key TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time_utc TEXT,
                    window_start_utc TEXT,
                    window_end_utc TEXT,
                    time_confirmed INTEGER NOT NULL,
                    source_url TEXT NOT NULL,
                    source_confidence REAL NOT NULL,
                    affected_country TEXT,
                    market TEXT,
                    sector TEXT,
                    company TEXT,
                    ticker TEXT,
                    asset TEXT,
                    expected_impact TEXT NOT NULL,
                    status TEXT NOT NULL,
                    last_verified_at TEXT NOT NULL,
                    collection_cursor TEXT,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_event_calendar_time ON event_calendar(event_time_utc, window_start_utc, window_end_utc);
                CREATE INDEX IF NOT EXISTS idx_event_calendar_asset ON event_calendar(ticker, asset, market, sector);

                CREATE TABLE IF NOT EXISTS event_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    stable_key TEXT NOT NULL,
                    revision_type TEXT NOT NULL,
                    previous_payload_json TEXT,
                    current_payload_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS market_regime_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    data_quality TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    calculated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_market_regime_time ON market_regime_snapshots(calculated_at);

                CREATE TABLE IF NOT EXISTS event_risk_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT,
                    signal TEXT,
                    model_view TEXT,
                    setup_key TEXT,
                    allowed INTEGER NOT NULL,
                    reason TEXT,
                    event_id INTEGER,
                    details TEXT,
                    decided_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_event_risk_decisions_time ON event_risk_decisions(decided_at);
                CREATE INDEX IF NOT EXISTS idx_event_risk_decisions_reason ON event_risk_decisions(reason, decided_at);
                """
            )

    def record_source_check(
        self,
        source_name: str,
        official_url: str,
        *,
        official_status: str = "official",
        timezone_name: str = "UTC",
        update_frequency: str | None = None,
        rate_limit: str | None = None,
        parser_compatibility: str | None = None,
        cursor_behavior: str | None = None,
        duplicate_policy: str | None = None,
        success: bool = True,
        error: str | None = None,
        checked_at: str | datetime | None = None,
    ) -> None:
        checked = iso(parse_utc(checked_at))
        success_at = checked if success else None
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO event_sources (
                    source_name, official_url, official_status, timezone, update_frequency, rate_limit,
                    parser_compatibility, cursor_behavior, duplicate_policy, last_checked_at, last_success_at, last_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_name) DO UPDATE SET
                    official_url=excluded.official_url,
                    official_status=excluded.official_status,
                    timezone=excluded.timezone,
                    update_frequency=excluded.update_frequency,
                    rate_limit=excluded.rate_limit,
                    parser_compatibility=excluded.parser_compatibility,
                    cursor_behavior=excluded.cursor_behavior,
                    duplicate_policy=excluded.duplicate_policy,
                    last_checked_at=excluded.last_checked_at,
                    last_success_at=COALESCE(excluded.last_success_at, event_sources.last_success_at),
                    last_error=excluded.last_error
                """,
                (
                    source_name,
                    official_url,
                    official_status,
                    timezone_name,
                    update_frequency,
                    rate_limit,
                    parser_compatibility,
                    cursor_behavior,
                    duplicate_policy,
                    checked,
                    success_at,
                    error,
                ),
            )

    def upsert_event(self, event: CalendarEvent) -> tuple[int, str]:
        data = event.normalized()
        stable_key = self._stable_key(data)
        payload = json.dumps(data, sort_keys=True)
        now = iso()
        with self.connect() as con:
            row = con.execute("SELECT * FROM event_calendar WHERE stable_key=?", (stable_key,)).fetchone()
            if row is None:
                cur = con.execute(
                    """
                    INSERT INTO event_calendar (
                        stable_key, title, event_type, event_time_utc, window_start_utc, window_end_utc,
                        time_confirmed, source_url, source_confidence, affected_country, market, sector,
                        company, ticker, asset, expected_impact, status, last_verified_at, collection_cursor, payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._event_row_values(stable_key, data, payload),
                )
                event_id = int(cur.lastrowid)
                con.execute(
                    "INSERT INTO event_revisions (event_id, stable_key, revision_type, current_payload_json, recorded_at) VALUES (?, ?, 'created', ?, ?)",
                    (event_id, stable_key, payload, now),
                )
                return event_id, "created"

            event_id = int(row["id"])
            old_payload = str(row["payload_json"])
            revision_type = self._revision_type(json.loads(old_payload), data)
            if revision_type != "unchanged":
                con.execute(
                    """
                    UPDATE event_calendar SET
                        title=?, event_type=?, event_time_utc=?, window_start_utc=?, window_end_utc=?,
                        time_confirmed=?, source_url=?, source_confidence=?, affected_country=?, market=?,
                        sector=?, company=?, ticker=?, asset=?, expected_impact=?, status=?,
                        last_verified_at=?, collection_cursor=?, payload_json=?
                    WHERE stable_key=?
                    """,
                    self._event_update_values(stable_key, data, payload),
                )
                con.execute(
                    """
                    INSERT INTO event_revisions (
                        event_id, stable_key, revision_type, previous_payload_json, current_payload_json, recorded_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, stable_key, revision_type, old_payload, payload, now),
                )
            return event_id, revision_type

    def store_regime_snapshot(self, snapshot: RegimeSnapshot) -> int:
        data = snapshot.normalized()
        with self.connect() as con:
            cur = con.execute(
                """
                INSERT INTO market_regime_snapshots (state, confidence, data_quality, inputs_json, calculated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data["state"],
                    float(data["confidence"]),
                    data["data_quality"],
                    json.dumps(data["inputs"], sort_keys=True, default=str),
                    data["calculated_at"],
                ),
            )
            return int(cur.lastrowid)

    def latest_regime(self) -> sqlite3.Row | None:
        with self.connect() as con:
            return con.execute("SELECT * FROM market_regime_snapshots ORDER BY calculated_at DESC LIMIT 1").fetchone()

    def record_gate_decision(self, setup: Any, decision: RiskGateDecision) -> None:
        payload = asdict(setup) if hasattr(setup, "__dataclass_fields__") else dict(setup)
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO event_risk_decisions (
                    ticker, signal, model_view, setup_key, allowed, reason, event_id, details, decided_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(getattr(setup, "ticker", payload.get("ticker", ""))).upper(),
                    getattr(setup, "signal", payload.get("signal")),
                    getattr(setup, "model_view", payload.get("model_view")),
                    getattr(setup, "setup_key", payload.get("setup_key")),
                    1 if decision.allowed else 0,
                    decision.reason,
                    decision.event_id,
                    decision.details,
                    iso(),
                    json.dumps(payload, sort_keys=True, default=str),
                ),
            )

    def source_data_fresh(self, *, max_age_hours: int, now: datetime | None = None) -> bool:
        cutoff = iso((now or utc_now()) - timedelta(hours=max_age_hours))
        with self.connect() as con:
            row = con.execute(
                "SELECT source_name FROM event_sources WHERE official_status='official' AND last_success_at>=? LIMIT 1",
                (cutoff,),
            ).fetchone()
            return bool(row)

    def relevant_pending_events(self, setup: Any, *, lookahead_hours: int, now: datetime | None = None) -> list[sqlite3.Row]:
        current = now or utc_now()
        horizon = current + timedelta(hours=lookahead_hours)
        ticker = str(getattr(setup, "ticker", "")).upper()
        with self.connect() as con:
            rows = con.execute(
                """
                SELECT * FROM event_calendar
                WHERE expected_impact IN ('High', 'Major')
                  AND status IN ('scheduled', 'postponed', 'changed')
                  AND (
                    ticker=? OR asset=? OR ticker IS NULL OR ticker=''
                  )
                ORDER BY COALESCE(event_time_utc, window_start_utc, window_end_utc) ASC
                """,
                (ticker, ticker),
            ).fetchall()
        return [row for row in rows if _event_overlaps(row, current, horizon) and _event_relevant(row, ticker)]

    def _stable_key(self, data: dict[str, Any]) -> str:
        subject = data.get("ticker") or data.get("asset") or data.get("market") or data.get("affected_country") or "global"
        return "|".join([str(data["source_url"]), str(data["event_type"]), str(subject), str(data["title"]).casefold()])

    def _event_row_values(self, stable_key: str, data: dict[str, Any], payload: str) -> tuple[Any, ...]:
        return (
            stable_key,
            data["title"],
            data["event_type"],
            data["event_time_utc"],
            data["window_start_utc"],
            data["window_end_utc"],
            1 if data["time_confirmed"] else 0,
            data["source_url"],
            float(data["source_confidence"]),
            data["affected_country"],
            data["market"],
            data["sector"],
            data["company"],
            data["ticker"],
            data["asset"],
            data["expected_impact"],
            data["status"],
            data["last_verified_at"],
            data["collection_cursor"],
            payload,
        )

    def _event_update_values(self, stable_key: str, data: dict[str, Any], payload: str) -> tuple[Any, ...]:
        values = self._event_row_values(stable_key, data, payload)
        return values[1:] + (stable_key,)

    def _revision_type(self, previous: dict[str, Any], current: dict[str, Any]) -> str:
        ignored = {"last_verified_at", "collection_cursor"}
        previous_core = {k: v for k, v in previous.items() if k not in ignored}
        current_core = {k: v for k, v in current.items() if k not in ignored}
        if previous_core == current_core:
            return "unchanged"
        if previous.get("status") != current.get("status") and current.get("status") == "cancelled":
            return "cancelled"
        if any(previous.get(k) != current.get(k) for k in ("event_time_utc", "window_start_utc", "window_end_utc", "time_confirmed")):
            return "time_changed"
        if previous.get("status") != current.get("status"):
            return "status_changed"
        return "updated"


def evaluate_event_risk(
    setup: Any,
    db: EventRiskDB,
    settings: dict[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> RiskGateDecision:
    settings = settings or {}
    current = now or utc_now()
    max_source_age = int(settings.get("event_risk_max_source_age_hours", 24))
    lookahead = int(settings.get("event_risk_lookahead_hours", 72))
    max_regime_age = int(settings.get("event_risk_max_regime_age_hours", 6))

    db.init()
    if not db.source_data_fresh(max_age_hours=max_source_age, now=current):
        return RiskGateDecision(False, "event_data_stale", details=f"No official calendar source succeeded within {max_source_age}h")

    regime = db.latest_regime()
    if not regime:
        return RiskGateDecision(False, "market_regime_uncertain", details="No market-regime snapshot is available")
    regime_time = parse_utc(str(regime["calculated_at"]))
    if not regime_time or current - regime_time > timedelta(hours=max_regime_age):
        return RiskGateDecision(False, "market_regime_uncertain", details=f"Market-regime snapshot is older than {max_regime_age}h")
    if str(regime["state"]) == "Uncertain" or str(regime["data_quality"]) != "fresh":
        return RiskGateDecision(False, "market_regime_uncertain", details=f"Regime={regime['state']} data_quality={regime['data_quality']}")

    for event in db.relevant_pending_events(setup, lookahead_hours=lookahead, now=current):
        if not bool(event["time_confirmed"]):
            return RiskGateDecision(False, "event_time_uncertain", int(event["id"]), str(event["title"]))
        event_type = str(event["event_type"]).lower()
        if event_type == "earnings":
            return RiskGateDecision(False, "earnings_risk", int(event["id"]), str(event["title"]))
        if event_type in {"dividend", "split", "shareholder_vote", "lockup_expiration", "merger_deadline", "corporate_action"}:
            return RiskGateDecision(False, "corporate_action_pending", int(event["id"]), str(event["title"]))
        return RiskGateDecision(False, "major_event_pending", int(event["id"]), str(event["title"]))

    return RiskGateDecision(True, None, details="Event risk known and no major unresolved catalyst is pending")


def apply_event_risk_gate(setup: Any, sqlite_path: str | Path, settings: dict[str, Any] | None = None) -> RiskGateDecision:
    db = EventRiskDB(sqlite_path)
    decision = evaluate_event_risk(setup, db, settings)
    db.record_gate_decision(setup, decision)
    return decision


def competing_catalyst_for_statement(
    ticker_or_asset: str,
    db: EventRiskDB,
    *,
    observed_at: datetime | None = None,
    lookback_hours: int = 24,
    lookahead_hours: int = 6,
) -> CalendarEvent | None:
    current = observed_at or utc_now()
    probe = type("ProbeSetup", (), {"ticker": str(ticker_or_asset).upper()})()
    events = db.relevant_pending_events(
        probe,
        lookahead_hours=lookback_hours + lookahead_hours,
        now=current - timedelta(hours=lookback_hours),
    )
    for row in events:
        if str(row["event_type"]).lower() in {"earnings", "filing", "regulatory_decision", "macro", "economic_release"}:
            return CalendarEvent(**json.loads(str(row["payload_json"])))
    return None


def _event_overlaps(row: sqlite3.Row, start: datetime, end: datetime) -> bool:
    exact = parse_utc(row["event_time_utc"])
    window_start = parse_utc(row["window_start_utc"])
    window_end = parse_utc(row["window_end_utc"])
    if exact:
        return start <= exact <= end
    if window_start and window_end:
        return window_start <= end and window_end >= start
    if window_start:
        return start <= window_start <= end
    if window_end:
        return start <= window_end <= end
    return False


def _event_relevant(row: sqlite3.Row, ticker: str) -> bool:
    row_ticker = str(row["ticker"] or "").upper()
    row_asset = str(row["asset"] or "").upper()
    if row_ticker and row_ticker != ticker:
        return False
    if row_asset and row_asset != ticker:
        return False
    if row_ticker == ticker or row_asset == ticker:
        return True
    market = str(row["market"] or "").casefold()
    country = str(row["affected_country"] or "").casefold()
    event_type = str(row["event_type"] or "").casefold()
    if ticker in {"USO", "XLE", "XOM", "CVX", "COP", "SLB", "OXY", "UNG"} and market in {"energy", "oil", "commodities"}:
        return True
    return market in {"us", "us equities", "equities", "broad market"} or country in {"us", "united states"} or event_type in {
        "macro",
        "economic_release",
        "central_bank",
        "commodity_policy",
        "market_holiday",
    }
