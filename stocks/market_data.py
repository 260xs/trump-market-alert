from __future__ import annotations

from datetime import timezone
from typing import Any


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


def fetch_bars(ticker: str, period: str, interval: str) -> list[dict[str, Any]]:
    try:
        import yfinance as yf  # type: ignore
    except Exception as exc:
        raise RuntimeError("yfinance is not installed. Install requirements.txt") from exc

    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return []

    df = df.reset_index()
    out: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        ts = row.get("Datetime") if "Datetime" in row else row.get("Date")
        try:
            if getattr(ts, "tzinfo", None) is None:
                ts = ts.tz_localize(timezone.utc) if hasattr(ts, "tz_localize") else ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.tz_convert(timezone.utc) if hasattr(ts, "tz_convert") else ts.astimezone(timezone.utc)
        except Exception:
            pass
        out.append(
            {
                "timestamp": ts,
                "open": _col(row, "Open"),
                "high": _col(row, "High"),
                "low": _col(row, "Low"),
                "close": _col(row, "Close"),
                "volume": _col(row, "Volume") if "Volume" in row or any(isinstance(k, tuple) and k[0] == "Volume" for k in row.keys()) else 0.0,
            }
        )
    return out
