from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


SUPPORTED_ASSET_TYPES = {"common_stock", "adr", "etf"}
SUPPORTED_LISTING_STATUSES = {"active"}
UNSUPPORTED_SECURITY_TYPES = {
    "closed_end_fund",
    "delisted",
    "note",
    "otc",
    "preferred",
    "right",
    "test",
    "unit",
    "warrant",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).astimezone(timezone.utc).isoformat()


def parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    else:
        raise ValueError(f"Unsupported datetime value: {value!r}")
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp is missing timezone: {value!r}")
    return dt.astimezone(timezone.utc)


def _clean_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _security_type(raw: str) -> str:
    text = " ".join(str(raw or "").strip().lower().replace("-", " ").replace("_", " ").split())
    if text in {"common stock", "common share", "ordinary share", "ordinary shares"}:
        return "common_stock"
    if text in {"adr", "american depositary receipt", "american depository receipt"}:
        return "adr"
    if text in {"etf", "exchange traded fund"}:
        return "etf"
    if "warrant" in text:
        return "warrant"
    if text in {"right", "rights"} or " right" in f" {text}":
        return "right"
    if text in {"unit", "units"} or " unit" in f" {text}":
        return "unit"
    if "preferred" in text or text in {"pfd", "preference share"}:
        return "preferred"
    if "test" in text:
        return "test"
    if "delisted" in text:
        return "delisted"
    return text or "unknown"


@dataclass(frozen=True)
class ProviderSymbolRecord:
    provider: str
    provider_version: str
    provider_symbol_id: str
    ticker: str
    legal_name: str
    exchange: str
    currency: str
    asset_type: str
    listing_status: str
    first_seen_at: str
    last_seen_at: str
    share_class: str = ""
    provider_exchange_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(
        cls,
        row: dict[str, Any],
        *,
        provider: str,
        provider_version: str,
        observed_at: datetime | None = None,
    ) -> "ProviderSymbolRecord":
        now = iso(observed_at)
        ticker = _clean_symbol(row.get("ticker") or row.get("symbol"))
        exchange = str(row.get("exchange") or row.get("market") or "").strip().upper()
        asset_type = _security_type(str(row.get("asset_type") or row.get("security_type") or row.get("type") or ""))
        status = str(row.get("listing_status") or row.get("status") or "active").strip().lower()
        return cls(
            provider=provider,
            provider_version=provider_version,
            provider_symbol_id=str(row.get("provider_symbol_id") or row.get("figi") or row.get("cik") or ticker),
            ticker=ticker,
            legal_name=str(row.get("legal_name") or row.get("name") or "").strip(),
            exchange=exchange,
            currency=str(row.get("currency") or "USD").strip().upper(),
            asset_type=asset_type,
            listing_status=status,
            first_seen_at=str(row.get("first_seen_at") or now),
            last_seen_at=str(row.get("last_seen_at") or now),
            share_class=str(row.get("share_class") or "").strip().upper(),
            provider_exchange_id=str(row.get("provider_exchange_id") or row.get("exchange_id") or "").strip(),
            raw=dict(row),
        )


@dataclass(frozen=True)
class UniverseDecision:
    record: ProviderSymbolRecord
    status: str
    reason_code: str
    reason: str
    evidence_json: str = "{}"

    @property
    def eligible(self) -> bool:
        return self.status == "eligible"


def classify_symbol(record: ProviderSymbolRecord, seen: dict[str, ProviderSymbolRecord] | None = None) -> UniverseDecision:
    reasons: list[tuple[str, str]] = []
    if not record.ticker:
        reasons.append(("missing_ticker", "provider record has no ticker"))
    if not record.legal_name:
        reasons.append(("missing_legal_name", "provider record has no legal name"))
    if not record.exchange:
        reasons.append(("missing_exchange", "provider record has no exchange"))
    if record.currency != "USD":
        reasons.append(("unsupported_currency", f"currency {record.currency} is not supported by this stock scanner"))
    if record.listing_status not in SUPPORTED_LISTING_STATUSES:
        reasons.append(("inactive_listing", f"listing_status={record.listing_status}"))
    if record.asset_type not in SUPPORTED_ASSET_TYPES:
        code = "unsupported_security_type" if record.asset_type in UNSUPPORTED_SECURITY_TYPES else "unknown_security_type"
        reasons.append((code, f"asset_type={record.asset_type}"))
    if record.ticker and any(x in record.ticker for x in ("^", "/", "=")):
        reasons.append(("unsupported_symbol_format", f"ticker {record.ticker} uses an unsupported format"))
    if record.raw.get("is_test_issue") is True:
        reasons.append(("test_issue", "provider marks this as a test issue"))
    if record.raw.get("is_otc") is True:
        reasons.append(("otc_unsupported", "OTC symbols are not supported by this scanner"))

    prior = (seen or {}).get(record.ticker)
    if prior and (
        prior.provider_symbol_id != record.provider_symbol_id
        or prior.exchange != record.exchange
        or prior.asset_type != record.asset_type
    ):
        evidence = json.dumps({"prior": asdict(prior), "current": asdict(record)}, sort_keys=True)
        return UniverseDecision(record, "quarantined", "provider_disagreement", "same ticker has conflicting provider identity metadata", evidence)

    if reasons:
        code, reason = reasons[0]
        status = "excluded" if code in {"inactive_listing", "unsupported_security_type", "test_issue", "otc_unsupported"} else "quarantined"
        return UniverseDecision(record, status, code, reason, json.dumps({"reasons": reasons}, sort_keys=True))
    return UniverseDecision(record, "eligible", "eligible", "active supported common stock, ADR, or ETF")


def build_universe(records: Iterable[ProviderSymbolRecord]) -> list[UniverseDecision]:
    seen: dict[str, ProviderSymbolRecord] = {}
    decisions: list[UniverseDecision] = []
    for record in sorted(records, key=lambda r: (r.ticker, r.provider, r.provider_symbol_id)):
        decision = classify_symbol(record, seen)
        decisions.append(decision)
        if decision.eligible:
            seen[record.ticker] = record
    return decisions


@dataclass(frozen=True)
class DataQualityResult:
    ticker: str
    passed: bool
    reason_codes: list[str]
    metrics: dict[str, Any]


def validate_bars(
    ticker: str,
    daily_bars: list[dict[str, Any]],
    hourly_bars: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    max_daily_age_days: int = 5,
    max_hourly_age_hours: int = 8,
    min_daily_bars: int = 120,
    min_hourly_bars: int = 60,
) -> DataQualityResult:
    checked_at = (now or utc_now()).astimezone(timezone.utc)
    reasons: list[str] = []
    metrics: dict[str, Any] = {
        "daily_bars": len(daily_bars),
        "hourly_bars": len(hourly_bars),
        "checked_at": iso(checked_at),
    }

    def check_series(name: str, bars: list[dict[str, Any]], min_bars: int, max_age: timedelta) -> None:
        if len(bars) < min_bars:
            reasons.append(f"{name}_insufficient_history")
            return
        timestamps: list[datetime] = []
        dollar_values: list[float] = []
        for bar in bars:
            try:
                ts = parse_dt(bar.get("timestamp"))
            except Exception:
                reasons.append(f"{name}_bad_timezone")
                continue
            timestamps.append(ts)
            values = [bar.get(k) for k in ("open", "high", "low", "close")]
            try:
                prices = [float(v) for v in values]
                volume = float(bar.get("volume", 0))
            except (TypeError, ValueError):
                reasons.append(f"{name}_non_numeric_values")
                return
            if any(not math.isfinite(v) or v <= 0 for v in prices):
                reasons.append(f"{name}_invalid_price")
            if prices[1] < max(prices[0], prices[2], prices[3]) or prices[2] > min(prices[0], prices[1], prices[3]):
                reasons.append(f"{name}_impossible_ohlc")
            if not math.isfinite(volume) or volume < 0:
                reasons.append(f"{name}_invalid_volume")
            dollar_values.append(prices[3] * max(volume, 0.0))
        if not timestamps:
            return
        if len(set(timestamps)) != len(timestamps):
            reasons.append(f"{name}_duplicate_timestamp")
        if timestamps != sorted(timestamps):
            reasons.append(f"{name}_timestamps_not_ascending")
        latest = max(timestamps)
        metrics[f"{name}_latest_timestamp"] = iso(latest)
        metrics[f"{name}_average_dollar_volume_20"] = round(sum(dollar_values[-20:]) / min(20, len(dollar_values)), 2)
        if checked_at - latest > max_age:
            reasons.append(f"{name}_stale")

    check_series("daily", daily_bars, min_daily_bars, timedelta(days=max_daily_age_days))
    check_series("hourly", hourly_bars, min_hourly_bars, timedelta(hours=max_hourly_age_hours))
    return DataQualityResult(ticker=_clean_symbol(ticker), passed=not reasons, reason_codes=sorted(set(reasons)), metrics=metrics)


@dataclass(frozen=True)
class CorporateAction:
    ticker: str
    action_type: str
    effective_at: str
    provider_id: str
    details: dict[str, Any]


def audit_corporate_actions(
    actions: Iterable[CorporateAction],
    adjusted_bars: list[dict[str, Any]],
    unadjusted_bars: list[dict[str, Any]],
) -> DataQualityResult:
    reasons: list[str] = []
    action_list = list(actions)
    if not action_list:
        return DataQualityResult("", True, [], {"corporate_actions": 0})
    if not adjusted_bars or not unadjusted_bars:
        return DataQualityResult(action_list[0].ticker, False, ["missing_adjusted_or_unadjusted_history"], {"corporate_actions": len(action_list)})
    if len(adjusted_bars) != len(unadjusted_bars):
        reasons.append("adjusted_unadjusted_length_mismatch")
    by_time = {iso(parse_dt(b["timestamp"])): b for b in unadjusted_bars}
    for bar in adjusted_bars:
        ts = iso(parse_dt(bar["timestamp"]))
        if ts not in by_time:
            reasons.append("adjusted_unadjusted_timestamp_mismatch")
            break
    for action in action_list:
        if action.action_type == "split":
            ratio = float(action.details.get("ratio", 0) or 0)
            if ratio <= 0:
                reasons.append("invalid_split_ratio")
        elif action.action_type == "dividend":
            amount = float(action.details.get("amount", 0) or 0)
            if amount < 0:
                reasons.append("invalid_dividend_amount")
        elif action.action_type not in {"ticker_change", "name_change", "merger", "spin_off", "delisting"}:
            reasons.append("unknown_corporate_action_type")
    return DataQualityResult(action_list[0].ticker, not reasons, sorted(set(reasons)), {"corporate_actions": len(action_list)})


class StockUniverseDB:
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
                CREATE TABLE IF NOT EXISTS stock_universe_symbols (
                    provider_symbol_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    legal_name TEXT NOT NULL,
                    share_class TEXT NOT NULL DEFAULT '',
                    listing_status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_version TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    evidence_json TEXT NOT NULL DEFAULT '{}',
                    PRIMARY KEY (provider, provider_symbol_id)
                );
                CREATE INDEX IF NOT EXISTS idx_stock_universe_symbols_status ON stock_universe_symbols(status, ticker);

                CREATE TABLE IF NOT EXISTS stock_symbol_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    provider_symbol_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    legal_name TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    listing_status TEXT NOT NULL,
                    status TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_stock_symbol_history_symbol ON stock_symbol_history(provider_symbol_id, observed_at);

                CREATE TABLE IF NOT EXISTS stock_universe_cursor (
                    job_name TEXT PRIMARY KEY,
                    cursor_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    processed_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0
                );
                """
            )

    def save_decisions(self, decisions: Iterable[UniverseDecision]) -> None:
        observed_at = iso()
        with self.connect() as con:
            for decision in decisions:
                r = decision.record
                con.execute(
                    """
                    INSERT INTO stock_universe_symbols (
                        provider_symbol_id, ticker, exchange, currency, asset_type, legal_name, share_class,
                        listing_status, provider, provider_version, first_seen_at, last_seen_at, status,
                        reason_code, evidence_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider, provider_symbol_id) DO UPDATE SET
                        ticker=excluded.ticker,
                        exchange=excluded.exchange,
                        currency=excluded.currency,
                        asset_type=excluded.asset_type,
                        legal_name=excluded.legal_name,
                        share_class=excluded.share_class,
                        listing_status=excluded.listing_status,
                        provider_version=excluded.provider_version,
                        last_seen_at=excluded.last_seen_at,
                        status=excluded.status,
                        reason_code=excluded.reason_code,
                        evidence_json=excluded.evidence_json
                    """,
                    (
                        r.provider_symbol_id,
                        r.ticker,
                        r.exchange,
                        r.currency,
                        r.asset_type,
                        r.legal_name,
                        r.share_class,
                        r.listing_status,
                        r.provider,
                        r.provider_version,
                        r.first_seen_at,
                        r.last_seen_at,
                        decision.status,
                        decision.reason_code,
                        decision.evidence_json,
                    ),
                )
                con.execute(
                    """
                    INSERT INTO stock_symbol_history (
                        provider, provider_symbol_id, ticker, legal_name, exchange, asset_type,
                        listing_status, status, reason_code, observed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.provider,
                        r.provider_symbol_id,
                        r.ticker,
                        r.legal_name,
                        r.exchange,
                        r.asset_type,
                        r.listing_status,
                        decision.status,
                        decision.reason_code,
                        observed_at,
                    ),
                )

    def eligible_tickers(self) -> list[str]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT ticker FROM stock_universe_symbols WHERE status='eligible' ORDER BY ticker"
            ).fetchall()
        return [str(row["ticker"]) for row in rows]

    def update_cursor(self, job_name: str, cursor_value: str, *, processed: int = 0, failed: int = 0) -> None:
        with self.connect() as con:
            con.execute(
                """
                INSERT INTO stock_universe_cursor (job_name, cursor_value, updated_at, processed_count, failed_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(job_name) DO UPDATE SET
                    cursor_value=excluded.cursor_value,
                    updated_at=excluded.updated_at,
                    processed_count=stock_universe_cursor.processed_count + excluded.processed_count,
                    failed_count=stock_universe_cursor.failed_count + excluded.failed_count
                """,
                (job_name, cursor_value, iso(), processed, failed),
            )

    def load_cursor(self, job_name: str) -> dict[str, Any] | None:
        with self.connect() as con:
            row = con.execute("SELECT * FROM stock_universe_cursor WHERE job_name=?", (job_name,)).fetchone()
        return dict(row) if row else None
