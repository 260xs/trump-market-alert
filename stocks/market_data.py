from __future__ import annotations

import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger(__name__)

_CACHE: dict[tuple[str, str, str], tuple[datetime, list[dict[str, Any]]]] = {}


def _cache_ttl_seconds() -> int:
    return max(int(os.getenv("MARKET_DATA_CACHE_TTL_SECONDS", "900")), 0)


def _retry_count() -> int:
    return max(int(os.getenv("MARKET_DATA_RETRIES", "3")), 1)


def _retry_sleep_seconds() -> float:
    return max(float(os.getenv("MARKET_DATA_RETRY_SLEEP_SECONDS", "2")), 0.0)


def _col(row: Any, key: str) -> float:
    value = row.get(key)
    if value is None:
        for k, v in row.items():
            if isinstance(k, tuple) and k[0] == key:
                value = v
                break
    if hasattr(value, "item"):
        value = value.item()
    return float(value)


def _normalize_timestamp(ts: Any) -> datetime:
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if not isinstance(ts, datetime):
        raise ValueError(f"invalid market-data timestamp: {ts!r}")
    if ts.tzinfo is None:
        raise ValueError(f"market-data timestamp must include timezone: {ts!r}")
    return ts.astimezone(timezone.utc)


def _valid_ohlcv(bar: dict[str, Any]) -> bool:
    open_price = float(bar["open"])
    high_price = float(bar["high"])
    low_price = float(bar["low"])
    close_price = float(bar["close"])
    volume = float(bar["volume"])
    prices = [open_price, high_price, low_price, close_price]
    if any(not math.isfinite(value) or value <= 0 for value in prices):
        return False
    if not math.isfinite(volume) or volume < 0:
        return False
    return low_price <= open_price <= high_price and low_price <= close_price <= high_price


def _rows_from_dataframe(df: Any) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []

    df = df.reset_index()
    out: list[dict[str, Any]] = []
    seen_timestamps: set[datetime] = set()
    for _, row in df.iterrows():
        ts = row.get("Datetime") if "Datetime" in row else row.get("Date")
        try:
            timestamp = _normalize_timestamp(ts)
            bar = {
                "timestamp": timestamp,
                "open": _col(row, "Open"),
                "high": _col(row, "High"),
                "low": _col(row, "Low"),
                "close": _col(row, "Close"),
                "volume": _col(row, "Volume") if "Volume" in row or any(isinstance(k, tuple) and k[0] == "Volume" for k in row.keys()) else 0.0,
            }
        except Exception as exc:
            log.warning("Skipping malformed market-data row: %s", exc)
            continue
        if timestamp in seen_timestamps:
            log.warning("Skipping duplicate market-data timestamp: %s", timestamp.isoformat())
            continue
        if not _valid_ohlcv(bar):
            log.warning("Skipping impossible market-data row at %s", timestamp.isoformat())
            continue
        seen_timestamps.add(timestamp)
        out.append(bar)
    out.sort(key=lambda bar: bar["timestamp"])
    return out


def _get_cached(key: tuple[str, str, str]) -> list[dict[str, Any]] | None:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return None
    cached = _CACHE.get(key)
    if not cached:
        return None
    stored_at, bars = cached
    if datetime.now(timezone.utc) - stored_at > timedelta(seconds=ttl):
        _CACHE.pop(key, None)
        return None
    return list(bars)


def _set_cached(key: tuple[str, str, str], bars: list[dict[str, Any]]) -> None:
    ttl = _cache_ttl_seconds()
    if ttl <= 0:
        return
    _CACHE[key] = (datetime.now(timezone.utc), list(bars))


def fetch_bars(ticker: str, period: str, interval: str) -> list[dict[str, Any]]:
    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:
        raise RuntimeError("yfinance is not installed. Install requirements.txt") from exc

    key = (ticker.upper(), str(period), str(interval))
    cached = _get_cached(key)
    if cached is not None:
        return cached

    last_error: Exception | None = None
    for attempt in range(1, _retry_count() + 1):
        try:
            df = yf.download(
                ticker,
                period=period,
                interval=interval,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            bars = _rows_from_dataframe(df)
            if bars:
                _set_cached(key, bars)
                return bars
            log.warning("No market data returned for %s period=%s interval=%s attempt=%s", ticker, period, interval, attempt)
        except Exception as exc:
            last_error = exc
            log.warning("Market data fetch failed for %s period=%s interval=%s attempt=%s: %s", ticker, period, interval, attempt, exc)
        if attempt < _retry_count() and _retry_sleep_seconds() > 0:
            time.sleep(_retry_sleep_seconds())

    if last_error is not None:
        raise RuntimeError(f"Market data fetch failed for {ticker} after {_retry_count()} attempts") from last_error
    return []
