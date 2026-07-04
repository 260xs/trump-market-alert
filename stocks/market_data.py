from __future__ import annotations

import logging
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


def _normalize_timestamp(ts: Any) -> Any:
    try:
        if getattr(ts, "tzinfo", None) is None:
            return ts.tz_localize(timezone.utc) if hasattr(ts, "tz_localize") else ts.replace(tzinfo=timezone.utc)
        return ts.tz_convert(timezone.utc) if hasattr(ts, "tz_convert") else ts.astimezone(timezone.utc)
    except Exception:
        return ts


def _rows_from_dataframe(df: Any) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []

    df = df.reset_index()
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        ts = row.get("Datetime") if "Datetime" in row else row.get("Date")
        out.append(
            {
                "timestamp": _normalize_timestamp(ts),
                "open": _col(row, "Open"),
                "high": _col(row, "High"),
                "low": _col(row, "Low"),
                "close": _col(row, "Close"),
                "volume": _col(row, "Volume") if "Volume" in row or any(isinstance(k, tuple) and k[0] == "Volume" for k in row.keys()) else 0.0,
            }
        )
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
