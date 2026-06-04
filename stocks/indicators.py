from __future__ import annotations

from statistics import mean


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return float(mean(values[-period:]))


def ema_series(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [float(values[0])]
    for value in values[1:]:
        out.append((float(value) * k) + (out[-1] * (1 - k)))
    return out


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return ema_series(values, period)[-1]


def rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for prev, cur in zip(values[-period - 1 : -1], values[-period:]):
        diff = cur - prev
        gains.append(max(diff, 0.0))
        losses.append(abs(min(diff, 0.0)))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(highs) <= period or len(lows) <= period or len(closes) <= period:
        return None
    trs: list[float] = []
    start = len(closes) - period
    for i in range(start, len(closes)):
        prev_close = closes[i - 1]
        tr = max(highs[i] - lows[i], abs(highs[i] - prev_close), abs(lows[i] - prev_close))
        trs.append(tr)
    return sum(trs) / period
