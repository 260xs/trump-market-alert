from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
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
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"datetime must be timezone-aware: {value!r}")
    return value.astimezone(UTC)


def eastern_to_utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ET).astimezone(UTC)


def iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def stable_event_uid(source_id: str, title: str, event_type: str, ticker: str | None, start_at: datetime | None, window_start: datetime | None) -> str:
    anchor = start_at or window_start
    raw = "|".join([source_id, event_type, title.strip().lower(), (ticker or "").upper(), iso_utc(anchor) or "unconfirmed"])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class EventRecord:
    title: str
    event_type: str
    source_id: str
    source_url: str
    source_confidence: float
    affected_country: str
    market: str
    sector: str | None = None
    company: str | None = None
    ticker_asset: str | None = None
    expected_impact: str = "Medium"
    time_confirmed: bool = False
    start_at_utc: datetime | None = None
    window_start_utc: datetime | None = None
    window_end_utc: datetime | None = None
    status: str = "scheduled"
    last_verified_at_utc: datetime = field(default_factory=utc_now)
    collection_cursor: str = ""
    uid: str | None = None

    def __post_init__(self) -> None:
        if self.expected_impact not in {"Low", "Medium", "High"}:
            raise ValueError("expected_impact must be Low, Medium, or High")
        if self.status not in {"scheduled", "cancelled", "postponed"}:
            raise ValueError("status must be scheduled, cancelled, or postponed")
        if self.time_confirmed and self.start_at_utc is None:
            raise ValueError("confirmed events must include start_at_utc")
        if not self.time_confirmed and self.start_at_utc is not None:
            raise ValueError("uncertain events must not store start_at_utc as confirmed")

    @property
    def event_uid(self) -> str:
        return self.uid or stable_event_uid(self.source_id, self.title, self.event_type, self.ticker_asset, self.start_at_utc, self.window_start_utc)

    def to_row(self) -> dict[str, Any]:
        return {
            "event_uid": self.event_uid,
            "title": self.title,
            "event_type": self.event_type,
            "start_at_utc": iso_utc(self.start_at_utc),
            "window_start_utc": iso_utc(self.window_start_utc),
            "window_end_utc": iso_utc(self.window_end_utc),
            "source_id": self.source_id,
            "source_url": self.source_url,
            "source_confidence": self.source_confidence,
            "affected_country": self.affected_country,
            "market": self.market,
            "sector": self.sector,
            "company": self.company,
            "ticker_asset": self.ticker_asset,
            "expected_impact": self.expected_impact,
            "time_confirmed": int(self.time_confirmed),
            "status": self.status,
            "last_verified_at_utc": iso_utc(self.last_verified_at_utc),
            "collection_cursor": self.collection_cursor,
        }


@dataclass(frozen=True)
class MarketRegimeSnapshot:
    state: str
    observed_at_utc: datetime
    confidence: float
    data_quality: str
    inputs: dict[str, Any]

    def __post_init__(self) -> None:
        if self.state not in {"Bullish", "Bearish", "Mixed", "Uncertain"}:
            raise ValueError("state must be Bullish, Bearish, Mixed, or Uncertain")


@dataclass(frozen=True)
class SetupContext:
    ticker: str
    model_view: str
    signal: str
    confidence: str
    trigger_level: float | None
    invalidation_level: float | None
    risk_reward: float | None
    sector: str | None = None
    market: str = "US equities"
    evaluated_at_utc: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    details: str
    matched_event_uid: str | None = None


class EventRiskStore:
    def __init__(self, sqlite_path: str | Path):
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.sqlite_path)
        con.row_factory = sqlite3.Row
        return con

    def init(self) -> None:
        with self.connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS event_sources (
                    source_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    official_status TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    update_frequency TEXT NOT NULL,
                    rate_limit_notes TEXT NOT NULL DEFAULT '',
                    parser_notes TEXT NOT NULL DEFAULT '',
                    cursor_behavior TEXT NOT NULL DEFAULT '',
                    duplicate_handling TEXT NOT NULL DEFAULT '',
                    last_checked_at_utc TEXT
                );
                CREATE TABLE IF NOT EXISTS event_calendar (
                    event_uid TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    start_at_utc TEXT,
                    window_start_utc TEXT,
                    window_end_utc TEXT,
                    source_id TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    source_confidence REAL NOT NULL,
                    affected_country TEXT NOT NULL,
                    market TEXT NOT NULL,
                    sector TEXT,
                    company TEXT,
                    ticker_asset TEXT,
                    expected_impact TEXT NOT NULL,
                    time_confirmed INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    last_verified_at_utc TEXT NOT NULL,
                    collection_cursor TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS event_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_uid TEXT NOT NULL,
                    changed_at_utc TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    previous_json TEXT,
                    current_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_cursors (
                    source_id TEXT PRIMARY KEY,
                    cursor TEXT NOT NULL,
                    checked_at_utc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS market_regime_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    observed_at_utc TEXT NOT NULL,
                    state TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    data_quality TEXT NOT NULL,
                    inputs_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS risk_gate_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decided_at_utc TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    model_view TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    allowed INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    details TEXT NOT NULL,
                    matched_event_uid TEXT
                );
                CREATE TABLE IF NOT EXISTS competing_catalyst_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    checked_at_utc TEXT NOT NULL,
                    ticker_asset TEXT,
                    statement_source_url TEXT,
                    competing_event_uid TEXT,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL
                );
                """
            )

    def upsert_source(self, source: dict[str, str]) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO event_sources (
                    source_id, name, official_status, source_url, timezone, update_frequency,
                    rate_limit_notes, parser_notes, cursor_behavior, duplicate_handling, last_checked_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    name=excluded.name,
                    official_status=excluded.official_status,
                    source_url=excluded.source_url,
                    timezone=excluded.timezone,
                    update_frequency=excluded.update_frequency,
                    rate_limit_notes=excluded.rate_limit_notes,
                    parser_notes=excluded.parser_notes,
                    cursor_behavior=excluded.cursor_behavior,
                    duplicate_handling=excluded.duplicate_handling,
                    last_checked_at_utc=excluded.last_checked_at_utc
                """,
                (
                    source["source_id"], source["name"], source["official_status"], source["source_url"], source["timezone"], source["update_frequency"],
                    source.get("rate_limit_notes", ""), source.get("parser_notes", ""), source.get("cursor_behavior", ""), source.get("duplicate_handling", ""), iso_utc(utc_now()),
                ),
            )

    def upsert_event(self, event: EventRecord) -> str:
        row = event.to_row()
        with self.connect() as con:
            old = con.execute("SELECT * FROM event_calendar WHERE event_uid=?", (event.event_uid,)).fetchone()
            old_json = json.dumps({key: old[key] for key in row}, sort_keys=True) if old else None
            con.execute(
                """
                INSERT INTO event_calendar (
                    event_uid, title, event_type, start_at_utc, window_start_utc, window_end_utc,
                    source_id, source_url, source_confidence, affected_country, market, sector, company,
                    ticker_asset, expected_impact, time_confirmed, status, last_verified_at_utc, collection_cursor, active
                ) VALUES (
                    :event_uid, :title, :event_type, :start_at_utc, :window_start_utc, :window_end_utc,
                    :source_id, :source_url, :source_confidence, :affected_country, :market, :sector, :company,
                    :ticker_asset, :expected_impact, :time_confirmed, :status, :last_verified_at_utc, :collection_cursor, 1
                )
                ON CONFLICT(event_uid) DO UPDATE SET
                    title=excluded.title,
                    event_type=excluded.event_type,
                    start_at_utc=excluded.start_at_utc,
                    window_start_utc=excluded.window_start_utc,
                    window_end_utc=excluded.window_end_utc,
                    source_id=excluded.source_id,
                    source_url=excluded.source_url,
                    source_confidence=excluded.source_confidence,
                    affected_country=excluded.affected_country,
                    market=excluded.market,
                    sector=excluded.sector,
                    company=excluded.company,
                    ticker_asset=excluded.ticker_asset,
                    expected_impact=excluded.expected_impact,
                    time_confirmed=excluded.time_confirmed,
                    status=excluded.status,
                    last_verified_at_utc=excluded.last_verified_at_utc,
                    collection_cursor=excluded.collection_cursor,
                    active=1
                """,
                row,
            )
            current_json = json.dumps(row, sort_keys=True)
            if old_json != current_json:
                con.execute(
                    "INSERT INTO event_revisions (event_uid, changed_at_utc, change_type, previous_json, current_json) VALUES (?, ?, ?, ?, ?)",
                    (event.event_uid, iso_utc(utc_now()), "insert" if old is None else "update", old_json, current_json),
                )
        return event.event_uid

    def save_source_cursor(self, source_id: str, cursor: str, status: str, error: str = "") -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO source_cursors (source_id, cursor, checked_at_utc, status, error)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    cursor=excluded.cursor,
                    checked_at_utc=excluded.checked_at_utc,
                    status=excluded.status,
                    error=excluded.error
                """,
                (source_id, cursor, iso_utc(utc_now()), status, error[:1000]),
            )

    def save_regime(self, snapshot: MarketRegimeSnapshot) -> None:
        with self.connect() as con:
            con.execute(
                "INSERT INTO market_regime_snapshots (observed_at_utc, state, confidence, data_quality, inputs_json) VALUES (?, ?, ?, ?, ?)",
                (iso_utc(snapshot.observed_at_utc), snapshot.state, snapshot.confidence, snapshot.data_quality, json.dumps(snapshot.inputs, sort_keys=True)),
            )

    def latest_regime(self) -> MarketRegimeSnapshot | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM market_regime_snapshots ORDER BY observed_at_utc DESC, id DESC LIMIT 1").fetchone()
        if not row:
            return None
        return MarketRegimeSnapshot(row["state"], parse_utc(row["observed_at_utc"]) or utc_now(), float(row["confidence"]), row["data_quality"], json.loads(row["inputs_json"]))

    def upcoming_events(self, now: datetime, horizon: timedelta) -> list[sqlite3.Row]:
        now = ensure_utc(now)
        end = now + horizon
        with self.connect() as con:
            return list(con.execute(
                """
                SELECT * FROM event_calendar
                WHERE active=1 AND status != 'cancelled'
                  AND COALESCE(start_at_utc, window_start_utc) IS NOT NULL
                  AND COALESCE(window_end_utc, start_at_utc, window_start_utc) >= ?
                  AND COALESCE(start_at_utc, window_start_utc) <= ?
                ORDER BY COALESCE(start_at_utc, window_start_utc)
                """,
                (iso_utc(now), iso_utc(end)),
            ))

    def record_gate_decision(self, setup: SetupContext, decision: GateDecision) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO risk_gate_decisions
                    (decided_at_utc, ticker, model_view, signal, allowed, reason, details, matched_event_uid)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (iso_utc(setup.evaluated_at_utc), setup.ticker.upper(), setup.model_view, setup.signal, int(decision.allowed), decision.reason, decision.details, decision.matched_event_uid),
            )

    def gate_reason_counts(self) -> dict[str, int]:
        with self.connect() as con:
            rows = con.execute("SELECT reason, COUNT(*) AS count FROM risk_gate_decisions WHERE allowed=0 GROUP BY reason ORDER BY reason").fetchall()
        return {row["reason"]: int(row["count"]) for row in rows}


def calculate_market_regime(inputs: dict[str, Any], observed_at: datetime | None = None) -> MarketRegimeSnapshot:
    observed_at = ensure_utc(observed_at or utc_now())
    required = ["broad_index_trend", "volatility", "breadth", "sector_leadership", "risk_on_off"]
    states = [inputs.get(name, {}).get("state") for name in required]
    if any(not inputs.get(name, {}).get("fresh") for name in required) or any(state in {None, "Uncertain"} for state in states):
        return MarketRegimeSnapshot("Uncertain", observed_at, 0.0, "stale_or_incomplete", inputs)
    if states.count("Bullish") >= 4:
        return MarketRegimeSnapshot("Bullish", observed_at, 0.8, "complete", inputs)
    if states.count("Bearish") >= 4:
        return MarketRegimeSnapshot("Bearish", observed_at, 0.8, "complete", inputs)
    return MarketRegimeSnapshot("Mixed", observed_at, 0.6, "conflicting", inputs)


def _event_matches_setup(event: sqlite3.Row, setup: SetupContext) -> bool:
    ticker = (setup.ticker or "").upper()
    event_ticker = (event["ticker_asset"] or "").upper()
    if event_ticker and event_ticker == ticker:
        return True
    event_market = (event["market"] or "").lower()
    if event["event_type"] in {"macro_release", "central_bank", "treasury_auction", "market_holiday", "energy_inventory"}:
        return "us" in event_market or "broad" in event_market or setup.market.lower() in event_market
    if setup.sector and event["sector"] and setup.sector.lower() == event["sector"].lower():
        return True
    return False


def evaluate_event_risk(store: EventRiskStore, setup: SetupContext, now: datetime | None = None, event_horizon: timedelta = timedelta(hours=72), max_data_age: timedelta = timedelta(hours=24)) -> GateDecision:
    now = ensure_utc(now or setup.evaluated_at_utc)
    if setup.model_view not in {"Buy", "Sell"}:
        decision = GateDecision(False, "event_data_stale", "Only existing Buy/Sell setup views are eligible for this gate.")
        store.record_gate_decision(setup, decision)
        return decision
    if setup.trigger_level is None or setup.invalidation_level is None or setup.risk_reward is None:
        decision = GateDecision(False, "event_data_stale", "Setup lacks trigger, invalidation, or risk/reward.")
        store.record_gate_decision(setup, decision)
        return decision
    regime = store.latest_regime()
    if regime is None or now - regime.observed_at_utc > max_data_age:
        decision = GateDecision(False, "market_regime_uncertain", "No fresh market-regime snapshot is available.")
        store.record_gate_decision(setup, decision)
        return decision
    if regime.state == "Uncertain" or regime.data_quality != "complete":
        decision = GateDecision(False, "market_regime_uncertain", f"Market regime is {regime.state} with data quality {regime.data_quality}.")
        store.record_gate_decision(setup, decision)
        return decision
    events = store.upcoming_events(now, event_horizon)
    if not events:
        latest_cursor = _latest_source_cursor_time(store)
        if latest_cursor is None or now - latest_cursor > max_data_age:
            decision = GateDecision(False, "event_data_stale", "Event calendar has no fresh source cursor in the risk window.")
            store.record_gate_decision(setup, decision)
            return decision
        decision = GateDecision(True, "allowed", "No matching unresolved major event found in the risk window.")
        store.record_gate_decision(setup, decision)
        return decision
    for event in events:
        if not _event_matches_setup(event, setup) or event["expected_impact"] == "Low":
            continue
        if not bool(event["time_confirmed"]):
            reason = "event_time_uncertain"
        elif event["event_type"] == "earnings":
            reason = "earnings_risk"
        elif event["event_type"] in {"corporate_action", "shareholder_vote", "regulatory_decision", "court_ruling"}:
            reason = "corporate_action_pending"
        else:
            reason = "major_event_pending"
        decision = GateDecision(False, reason, f"{event['title']} is pending in the event-risk window.", event["event_uid"])
        store.record_gate_decision(setup, decision)
        return decision
    decision = GateDecision(True, "allowed", "Event risk is known and no matching unresolved major catalyst was found.")
    store.record_gate_decision(setup, decision)
    return decision


def _latest_source_cursor_time(store: EventRiskStore) -> datetime | None:
    with store.connect() as con:
        row = con.execute("SELECT checked_at_utc FROM source_cursors ORDER BY checked_at_utc DESC LIMIT 1").fetchone()
    return parse_utc(row["checked_at_utc"]) if row else None


def competing_catalyst_decision(store: EventRiskStore, ticker_asset: str | None, statement_source_url: str | None, now: datetime | None = None) -> GateDecision:
    now = ensure_utc(now or utc_now())
    setup = SetupContext(ticker=ticker_asset or "", model_view="Buy", signal="Good", confidence="High", trigger_level=1, invalidation_level=1, risk_reward=1, evaluated_at_utc=now)
    for event in store.upcoming_events(now - timedelta(hours=6), timedelta(hours=78)):
        if _event_matches_setup(event, setup) and event["expected_impact"] in {"Medium", "High"}:
            decision = GateDecision(False, "competing_catalyst", f"{event['title']} is a better scheduled catalyst candidate.", event["event_uid"])
            with store.connect() as con:
                con.execute(
                    "INSERT INTO competing_catalyst_checks (checked_at_utc, ticker_asset, statement_source_url, competing_event_uid, decision, reason) VALUES (?, ?, ?, ?, ?, ?)",
                    (iso_utc(now), ticker_asset, statement_source_url, event["event_uid"], "reject_attribution", decision.reason),
                )
            return decision
    decision = GateDecision(True, "allowed", "No stronger scheduled competing catalyst found.")
    with store.connect() as con:
        con.execute(
            "INSERT INTO competing_catalyst_checks (checked_at_utc, ticker_asset, statement_source_url, decision, reason) VALUES (?, ?, ?, ?, ?)",
            (iso_utc(now), ticker_asset, statement_source_url, "allow_attribution", decision.reason),
        )
    return decision


def source_registry() -> list[dict[str, str]]:
    return [
        {"source_id": "fed_fomc_calendar", "name": "Federal Reserve FOMC calendar", "official_status": "official .gov central-bank source", "source_url": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "timezone": "America/New_York", "update_frequency": "as Federal Reserve updates calendar", "parser_notes": "HTML calendar; convert ET dates/times to UTC; minutes release three weeks after decisions.", "cursor_behavior": "latest verified year and event key", "duplicate_handling": "stable event_uid from source_id, type, title, ticker, and UTC/window anchor"},
        {"source_id": "bls_release_schedule", "name": "BLS release schedule", "official_status": "official .gov source", "source_url": "https://www.bls.gov/schedule/2026/home.htm", "timezone": "America/New_York", "update_frequency": "published annual schedule, modified as needed", "parser_notes": "HTML table; all times on calendar are Eastern Time.", "cursor_behavior": "year/month/date/title/time", "duplicate_handling": "same title plus confirmed UTC release time"},
        {"source_id": "bea_release_schedule", "name": "BEA release schedule", "official_status": "official .gov source", "source_url": "https://www.bea.gov/news/schedule", "timezone": "America/New_York", "update_frequency": "upcoming release schedule; page exposes JSON link", "parser_notes": "HTML and machine-readable JSON available; convert ET to UTC.", "cursor_behavior": "date/time/release title", "duplicate_handling": "same title plus confirmed UTC release time"},
        {"source_id": "nyse_holidays", "name": "NYSE market-hours and holidays", "official_status": "official exchange source", "source_url": "https://www.nyse.com/trade/hours-calendars", "timezone": "America/New_York", "update_frequency": "annual holiday table", "parser_notes": "HTML holiday table; early closes use ET.", "cursor_behavior": "holiday year and name", "duplicate_handling": "holiday name plus date"},
        {"source_id": "eia_wpsr", "name": "EIA Weekly Petroleum Status Report", "official_status": "official .gov source", "source_url": "https://www.eia.gov/petroleum/supply/weekly/", "timezone": "America/New_York", "update_frequency": "weekly", "parser_notes": "HTML page lists release and next release date; clock time may require page text confirmation.", "cursor_behavior": "data week ending and next release date", "duplicate_handling": "report date and data week"},
        {"source_id": "nokia_ir_events", "name": "Nokia investor relations events", "official_status": "official company investor-relations source", "source_url": "https://www.nokia.com/about-us/investors/investor-relations-events/", "timezone": "Europe/Helsinki", "update_frequency": "company financial calendar", "parser_notes": "HTML financial calendar; dates can appear without release clock time.", "cursor_behavior": "financial-calendar year and report title", "duplicate_handling": "company, report period, and date/window"},
    ]


def build_seed_events(verified_at: datetime | None = None) -> list[EventRecord]:
    verified_at = ensure_utc(verified_at or utc_now())
    return [
        EventRecord("EIA Weekly Petroleum Status Report next release", "energy_inventory", "eia_wpsr", "https://www.eia.gov/petroleum/supply/weekly/", 0.95, "US", "energy commodities", sector="Energy", expected_impact="Medium", time_confirmed=False, window_start_utc=datetime(2026, 7, 22, tzinfo=UTC), window_end_utc=datetime(2026, 7, 23, tzinfo=UTC), last_verified_at_utc=verified_at, collection_cursor="2026-07-15 release; next release 2026-07-22"),
        EventRecord("Nokia Q2 and half-year 2026 financial report", "earnings", "nokia_ir_events", "https://www.nokia.com/about-us/investors/investor-relations-events/", 0.95, "FI", "US equities", sector="Technology", company="Nokia", ticker_asset="NOK", expected_impact="High", time_confirmed=False, window_start_utc=datetime(2026, 7, 23, tzinfo=UTC), window_end_utc=datetime(2026, 7, 24, tzinfo=UTC), last_verified_at_utc=verified_at, collection_cursor="financial calendar 2026 report for Q2 and half-year 2026"),
        EventRecord("FOMC meeting, July 2026", "central_bank", "fed_fomc_calendar", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", 0.95, "US", "broad US risk assets", expected_impact="High", time_confirmed=False, window_start_utc=datetime(2026, 7, 28, tzinfo=UTC), window_end_utc=datetime(2026, 7, 30, tzinfo=UTC), last_verified_at_utc=verified_at, collection_cursor="2026 FOMC meetings July 28-29"),
        EventRecord("BEA GDP advance estimate, Q2 2026", "macro_release", "bea_release_schedule", "https://www.bea.gov/news/schedule", 0.95, "US", "broad US risk assets", expected_impact="High", time_confirmed=True, start_at_utc=eastern_to_utc(2026, 7, 30, 8, 30), last_verified_at_utc=verified_at, collection_cursor="July 30 8:30 AM GDP (Advance Estimate), 2nd Quarter 2026"),
        EventRecord("BLS JOLTS, June 2026", "macro_release", "bls_release_schedule", "https://www.bls.gov/schedule/2026/home.htm", 0.95, "US", "broad US risk assets", expected_impact="Medium", time_confirmed=True, start_at_utc=eastern_to_utc(2026, 8, 4, 10, 0), last_verified_at_utc=verified_at, collection_cursor="August 04 10:00 AM Job Openings and Labor Turnover Survey for June 2026"),
        EventRecord("BLS Employment Situation, July 2026", "macro_release", "bls_release_schedule", "https://www.bls.gov/schedule/2026/home.htm", 0.95, "US", "broad US risk assets", expected_impact="High", time_confirmed=True, start_at_utc=eastern_to_utc(2026, 8, 7, 8, 30), last_verified_at_utc=verified_at, collection_cursor="August 07 8:30 AM Employment Situation for July 2026"),
        EventRecord("BLS Consumer Price Index, July 2026", "macro_release", "bls_release_schedule", "https://www.bls.gov/schedule/2026/home.htm", 0.95, "US", "broad US risk assets", expected_impact="High", time_confirmed=True, start_at_utc=eastern_to_utc(2026, 8, 12, 8, 30), last_verified_at_utc=verified_at, collection_cursor="August 12 8:30 AM Consumer Price Index for July 2026"),
        EventRecord("NYSE Labor Day market holiday", "market_holiday", "nyse_holidays", "https://www.nyse.com/trade/hours-calendars", 0.95, "US", "US equities", expected_impact="Medium", time_confirmed=True, start_at_utc=datetime(2026, 9, 7, tzinfo=UTC), last_verified_at_utc=verified_at, collection_cursor="2026 holiday table Labor Day Monday, September 7"),
    ]


def refresh_seed_calendar(store: EventRiskStore, verified_at: datetime | None = None) -> dict[str, Any]:
    verified_at = ensure_utc(verified_at or utc_now())
    store.init()
    for source in source_registry():
        store.upsert_source(source)
        store.save_source_cursor(source["source_id"], source.get("cursor_behavior", ""), "success")
    event_ids = [store.upsert_event(event) for event in build_seed_events(verified_at)]
    regime = calculate_market_regime(
        {
            "broad_index_trend": {"fresh": False, "state": "Uncertain", "source": "not available in this maintenance run"},
            "volatility": {"fresh": False, "state": "Uncertain", "source": "not available in this maintenance run"},
            "breadth": {"fresh": False, "state": "Uncertain", "source": "not available in this maintenance run"},
            "sector_leadership": {"fresh": False, "state": "Uncertain", "source": "not available in this maintenance run"},
            "risk_on_off": {"fresh": False, "state": "Uncertain", "source": "not available in this maintenance run"},
        },
        verified_at,
    )
    store.save_regime(regime)
    return {"events_upserted": len(event_ids), "event_ids": event_ids, "regime": asdict(regime)}
