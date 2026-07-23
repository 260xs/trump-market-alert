from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

log = logging.getLogger(__name__)

SUPPORTED_ASSET_TYPES = {"COMMON_STOCK", "ADR", "ETF"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).astimezone(timezone.utc).isoformat()


def _normalize_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def _clean(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class SymbolRecord:
    ticker: str
    legal_name: str
    exchange: str
    currency: str
    asset_type: str
    listing_status: str
    provider: str
    provider_symbol: str
    provider_id: str | None = None
    share_class: str | None = None
    first_seen_at: str | None = None
    last_seen_at: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SymbolExclusion:
    ticker: str
    provider: str
    exchange: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DataQualityFinding:
    ticker: str
    status: str
    reason: str
    evidence: dict[str, Any] = field(default_factory=dict)


def classify_asset_type(raw_type: str, name: str = "", ticker: str = "") -> str:
    text = f"{raw_type} {name} {ticker}".upper()
    if "TEST" in text or ticker.upper().startswith("TEST"):
        return "TEST"
    if "WARRANT" in text or ticker.endswith(("W", "WS", "WT")):
        return "WARRANT"
    if "RIGHT" in text or ticker.endswith("R"):
        return "RIGHT"
    if "UNIT" in text or ticker.endswith("U"):
        return "UNIT"
    if "PREFERRED" in text or " PFD" in text or ticker.endswith(("P", "PR")):
        return "PREFERRED"
    if "ETF" in text or "EXCHANGE TRADED FUND" in text:
        return "ETF"
    if "ADR" in text or "ADS" in text or "AMERICAN DEPOSIT" in text:
        return "ADR"
    if "COMMON" in text or "ORDINARY" in text or raw_type == "":
        return "COMMON_STOCK"
    return "UNKNOWN"


def parse_listing_rows(rows: Iterable[dict[str, Any]], *, provider: str, exchange: str, currency: str = "USD", seen_at: datetime | None = None) -> tuple[list[SymbolRecord], list[SymbolExclusion]]:
    records: list[SymbolRecord] = []
    exclusions: list[SymbolExclusion] = []
    seen_keys: set[tuple[str, str]] = set()
    now = iso(seen_at)
    for row in rows:
        ticker = _normalize_ticker(row.get("ticker") or row.get("symbol") or row.get("ACT Symbol"))
        name = _clean(row.get("legal_name") or row.get("security_name") or row.get("Security Name") or row.get("name"))
        status = _clean(row.get("listing_status") or row.get("status") or row.get("Listing Status") or "active").lower()
        raw_type = _clean(row.get("asset_type") or row.get("security_type") or row.get("Security Type"))
        provider_symbol = _normalize_ticker(row.get("provider_symbol") or row.get("nasdaq_symbol") or row.get("NASDAQ Symbol") or ticker)
        asset_type = classify_asset_type(raw_type, name, ticker)
        evidence = dict(row)
        if not ticker or not provider_symbol:
            exclusions.append(SymbolExclusion(ticker, provider, exchange, "missing_symbol", evidence))
            continue
        if status not in {"active", "listed", "trading"}:
            exclusions.append(SymbolExclusion(ticker, provider, exchange, "inactive_or_delisted", evidence))
            continue
        if asset_type not in SUPPORTED_ASSET_TYPES:
            exclusions.append(SymbolExclusion(ticker, provider, exchange, f"unsupported_asset_type:{asset_type}", evidence))
            continue
        duplicate_key = (exchange, provider_symbol)
        if duplicate_key in seen_keys:
            exclusions.append(SymbolExclusion(ticker, provider, exchange, "duplicate_provider_symbol", evidence))
            continue
        seen_keys.add(duplicate_key)
        records.append(SymbolRecord(ticker, name or ticker, exchange, currency, asset_type, "active", provider, provider_symbol, _clean(row.get("provider_id") or row.get("cik") or row.get("FIGI")) or None, _clean(row.get("share_class") or row.get("class")) or None, now, now, evidence))
    return records, exclusions


def load_listing_csv(path: str | Path, *, provider: str, exchange: str, currency: str = "USD") -> tuple[list[SymbolRecord], list[SymbolExclusion]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return parse_listing_rows(csv.DictReader(f), provider=provider, exchange=exchange, currency=currency)


class UniverseStore:
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
            con.executescript("""
                CREATE TABLE IF NOT EXISTS symbol_universe (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    legal_name TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    listing_status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_symbol TEXT NOT NULL,
                    provider_id TEXT,
                    share_class TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    UNIQUE(provider, exchange, provider_symbol)
                );
                CREATE INDEX IF NOT EXISTS idx_symbol_universe_ticker ON symbol_universe(ticker, exchange, listing_status);
                CREATE TABLE IF NOT EXISTS symbol_exclusions (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, provider TEXT NOT NULL, exchange TEXT NOT NULL, reason TEXT NOT NULL, evidence_json TEXT NOT NULL, recorded_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS symbol_quarantine (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, provider TEXT NOT NULL, exchange TEXT NOT NULL, reason TEXT NOT NULL, evidence_json TEXT NOT NULL, recorded_at TEXT NOT NULL, resolved_at TEXT);
                CREATE INDEX IF NOT EXISTS idx_symbol_quarantine_open ON symbol_quarantine(ticker, resolved_at);
                CREATE TABLE IF NOT EXISTS universe_batch_cursors (cursor_key TEXT PRIMARY KEY, next_offset INTEGER NOT NULL, updated_at TEXT NOT NULL, evidence_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS failed_symbols (id INTEGER PRIMARY KEY AUTOINCREMENT, cursor_key TEXT NOT NULL, ticker TEXT NOT NULL, reason TEXT NOT NULL, evidence_json TEXT NOT NULL, failed_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS corporate_actions (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, action_type TEXT NOT NULL, effective_at TEXT NOT NULL, provider TEXT NOT NULL, evidence_json TEXT NOT NULL, recorded_at TEXT NOT NULL);
            """)

    def upsert_symbols(self, records: Iterable[SymbolRecord]) -> int:
        count = 0
        with self.connect() as con:
            for record in records:
                now = iso()
                con.execute("""
                    INSERT INTO symbol_universe (ticker, legal_name, exchange, currency, asset_type, listing_status, provider, provider_symbol, provider_id, share_class, first_seen_at, last_seen_at, evidence_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider, exchange, provider_symbol) DO UPDATE SET ticker=excluded.ticker, legal_name=excluded.legal_name, currency=excluded.currency, asset_type=excluded.asset_type, listing_status=excluded.listing_status, provider_id=excluded.provider_id, share_class=excluded.share_class, last_seen_at=excluded.last_seen_at, evidence_json=excluded.evidence_json
                """, (record.ticker, record.legal_name, record.exchange, record.currency, record.asset_type, record.listing_status, record.provider, record.provider_symbol, record.provider_id, record.share_class, record.first_seen_at or now, record.last_seen_at or now, json.dumps(record.evidence, sort_keys=True, default=str)))
                count += 1
        return count

    def record_exclusions(self, exclusions: Iterable[SymbolExclusion]) -> int:
        count = 0
        with self.connect() as con:
            for exclusion in exclusions:
                con.execute("INSERT INTO symbol_exclusions (ticker, provider, exchange, reason, evidence_json, recorded_at) VALUES (?, ?, ?, ?, ?, ?)", (exclusion.ticker, exclusion.provider, exclusion.exchange, exclusion.reason, json.dumps(exclusion.evidence, sort_keys=True, default=str), iso()))
                count += 1
        return count

    def quarantine(self, finding: DataQualityFinding, provider: str, exchange: str) -> None:
        with self.connect() as con:
            con.execute("INSERT INTO symbol_quarantine (ticker, provider, exchange, reason, evidence_json, recorded_at) VALUES (?, ?, ?, ?, ?, ?)", (finding.ticker, provider, exchange, finding.reason, json.dumps(finding.evidence, sort_keys=True, default=str), iso()))

    def get_cursor(self, cursor_key: str) -> int:
        with self.connect() as con:
            row = con.execute("SELECT next_offset FROM universe_batch_cursors WHERE cursor_key=?", (cursor_key,)).fetchone()
            return int(row["next_offset"]) if row else 0

    def save_cursor(self, cursor_key: str, next_offset: int, evidence: dict[str, Any] | None = None) -> None:
        with self.connect() as con:
            con.execute("""
                INSERT INTO universe_batch_cursors (cursor_key, next_offset, updated_at, evidence_json) VALUES (?, ?, ?, ?)
                ON CONFLICT(cursor_key) DO UPDATE SET next_offset=excluded.next_offset, updated_at=excluded.updated_at, evidence_json=excluded.evidence_json
            """, (cursor_key, next_offset, iso(), json.dumps(evidence or {}, sort_keys=True, default=str)))

    def record_failed_symbol(self, cursor_key: str, ticker: str, reason: str, evidence: dict[str, Any] | None = None) -> None:
        with self.connect() as con:
            con.execute("INSERT INTO failed_symbols (cursor_key, ticker, reason, evidence_json, failed_at) VALUES (?, ?, ?, ?, ?)", (cursor_key, ticker, reason, json.dumps(evidence or {}, sort_keys=True, default=str), iso()))


def _as_utc(ts: Any) -> datetime | None:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return None
        return ts.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_price_bars(ticker: str, bars: list[dict[str, Any]], *, interval: str, now: datetime | None = None, require_adjusted_pair: bool = False) -> DataQualityFinding:
    check_time = (now or utc_now()).astimezone(timezone.utc)
    if not bars:
        return DataQualityFinding(ticker, "quarantine", "missing_bars")
    timestamps: list[datetime] = []
    for index, bar in enumerate(bars):
        ts = _as_utc(bar.get("timestamp"))
        if ts is None:
            return DataQualityFinding(ticker, "quarantine", "bad_timezone", {"index": index, "timestamp": str(bar.get("timestamp"))})
        timestamps.append(ts)
        try:
            prices = {field: float(bar.get(field)) for field in ("open", "high", "low", "close")}
            volume = float(bar.get("volume", 0))
        except (TypeError, ValueError):
            return DataQualityFinding(ticker, "quarantine", "non_numeric_price_or_volume", {"index": index, "bar": bar})
        if any(value <= 0 for value in prices.values()):
            return DataQualityFinding(ticker, "quarantine", "zero_or_negative_price", {"index": index, "bar": bar})
        if volume < 0:
            return DataQualityFinding(ticker, "quarantine", "negative_volume", {"index": index, "bar": bar})
        if prices["low"] > min(prices["open"], prices["close"], prices["high"]) or prices["high"] < max(prices["open"], prices["close"], prices["low"]):
            return DataQualityFinding(ticker, "quarantine", "impossible_ohlc", {"index": index, "bar": bar})
        if require_adjusted_pair and "adjusted_close" not in bar and "adj_close" not in bar:
            return DataQualityFinding(ticker, "quarantine", "missing_adjusted_price", {"index": index})
    if len(set(timestamps)) != len(timestamps):
        return DataQualityFinding(ticker, "quarantine", "duplicate_timestamps")
    if timestamps != sorted(timestamps):
        return DataQualityFinding(ticker, "quarantine", "non_monotonic_timestamps")
    max_age = timedelta(days=5) if interval.endswith("d") else timedelta(hours=8)
    if check_time - timestamps[-1] > max_age:
        return DataQualityFinding(ticker, "quarantine", "stale_candles", {"last_timestamp": timestamps[-1].isoformat(), "checked_at": check_time.isoformat()})
    for prev, current in zip(bars, bars[1:]):
        prev_close = float(prev["close"])
        current_close = float(current["close"])
        if prev_close > 0 and abs(current_close / prev_close - 1.0) >= 0.45:
            action = current.get("split") or current.get("corporate_action") or prev.get("split") or prev.get("corporate_action")
            if not action:
                return DataQualityFinding(ticker, "quarantine", "possible_unadjusted_split_gap", {"previous": prev, "current": current})
    return DataQualityFinding(ticker, "passed", "ok", {"bars": len(bars), "last_timestamp": timestamps[-1].isoformat()})


def compare_provider_metadata(primary: SymbolRecord, independent: SymbolRecord | None) -> DataQualityFinding:
    if independent is None:
        return DataQualityFinding(primary.ticker, "passed", "independent_metadata_unavailable", {"provider": primary.provider})
    disagreements: dict[str, tuple[Any, Any]] = {}
    for field_name in ("ticker", "legal_name", "exchange", "asset_type", "listing_status"):
        left = getattr(primary, field_name)
        right = getattr(independent, field_name)
        if str(left).strip().upper() != str(right).strip().upper():
            disagreements[field_name] = (left, right)
    if disagreements:
        return DataQualityFinding(primary.ticker, "quarantine", "provider_metadata_disagreement", {"primary": asdict(primary), "independent": asdict(independent), "disagreements": disagreements})
    return DataQualityFinding(primary.ticker, "passed", "metadata_agrees")


def process_batch(store: UniverseStore, cursor_key: str, symbols: list[SymbolRecord], handler: Callable[[SymbolRecord], DataQualityFinding], *, batch_size: int) -> dict[str, int]:
    start = store.get_cursor(cursor_key)
    end = min(start + batch_size, len(symbols))
    stats = {"processed": 0, "passed": 0, "quarantined": 0, "failed": 0, "remaining": max(len(symbols) - end, 0)}
    for offset in range(start, end):
        symbol = symbols[offset]
        try:
            finding = handler(symbol)
        except Exception as exc:
            stats["failed"] += 1
            store.record_failed_symbol(cursor_key, symbol.ticker, type(exc).__name__, {"message": str(exc), "offset": offset})
        else:
            if finding.status == "passed":
                stats["passed"] += 1
            else:
                stats["quarantined"] += 1
                store.quarantine(finding, symbol.provider, symbol.exchange)
        stats["processed"] += 1
        store.save_cursor(cursor_key, offset + 1, {"last_symbol": symbol.ticker})
    return stats


def write_report(path: str | Path, payload: dict[str, Any]) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Silent stock universe and data-quality maintenance helper.")
    parser.add_argument("--sqlite-path", default="data/stocks.sqlite3")
    parser.add_argument("--report-path", default="data/data_quality_report.json")
    parser.add_argument("--provider-version", default="not-run")
    args = parser.parse_args()
    store = UniverseStore(args.sqlite_path)
    store.init()
    report = {"generated_at": iso(), "provider_version": args.provider_version, "mode": "schema-and-report-only", "telegram": "disabled", "eligible_symbols": 0, "processed": 0, "passed": 0, "quarantined": 0, "failed": 0, "remaining": 0, "known_gaps": ["No provider listing file was supplied to this run.", "No live market-data validation was performed by this schema-only dry run."]}
    write_report(args.report_path, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
