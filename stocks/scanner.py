from __future__ import annotations

import argparse
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from alerts.telegram import TelegramClient
from stocks.indicators import atr, ema, macd, rsi, sma
from stocks.market_data import fetch_bars
from stocks.research_db import StockResearchDB

log = logging.getLogger(__name__)

CONFIDENCE_RANK = {"None": 0, "Low": 1, "Medium": 2, "High": 3}


@dataclass
class StockSetup:
    ticker: str
    name: str
    signal: str  # Good, Bad, Neutral
    setup_type: str  # Entry, Exit/Risk, None
    model_view: str  # Buy, Sell, Hold. Research label only, not advice.
    confidence: str  # High, Medium, Low, None
    timeframe: str
    last_price: float
    trigger_level: float | None
    exit_level: float | None
    target_level: float | None
    rsi_14: float | None
    ema_8: float | None
    ema_21: float | None
    ema_50: float | None
    daily_ema_20: float | None
    daily_sma_50: float | None
    atr_14: float | None
    volume_ratio_20: float | None
    risk_reward: float | None
    risk_pct: float | None
    reason: str
    setup_key: str
    technical_score: int = 0
    max_technical_score: int = 0
    confirmations: str = ""

    @property
    def actionable(self) -> bool:
        return (
            self.signal in {"Good", "Bad"}
            and self.setup_type in {"Entry", "Exit/Risk"}
            and self.model_view in {"Buy", "Sell"}
            and self.confidence in {"High", "Medium"}
            and self.trigger_level is not None
            and self.exit_level is not None
            and self.risk_reward is not None
            and self.risk_pct is not None
        )


def load_stock_config(path: str | Path = "config/stocks.yaml") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _volume_ratio(bars: list[dict[str, Any]], period: int = 20) -> float | None:
    vols = [float(b.get("volume", 0.0) or 0.0) for b in bars]
    if len(vols) < period + 1:
        return None
    baseline = _avg([v for v in vols[-period - 1 : -1] if v >= 0])
    if not baseline:
        return None
    return vols[-1] / baseline


def _return_pct(values: list[float], period: int) -> float | None:
    if len(values) <= period or not values[-period - 1]:
        return None
    return (values[-1] / values[-period - 1] - 1) * 100


def _slope_pct(values: list[float], period: int) -> float | None:
    if len(values) <= period or not values[-period - 1]:
        return None
    return (values[-1] - values[-period - 1]) / values[-period - 1] * 100


def _daily_context(daily_bars: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not daily_bars or len(daily_bars) < 50:
        return {"ema20": None, "sma50": None, "sma200": None, "up": None, "down": None, "ret20": None, "ret60": None}
    closes = [float(b["close"]) for b in daily_bars]
    last = closes[-1]
    e20 = ema(closes, 20)
    s50 = sma(closes, 50)
    s200 = sma(closes, 200)
    ret20 = _return_pct(closes, 20)
    ret60 = _return_pct(closes, 60)
    above_long = True if s200 is None else last > s200
    below_long = True if s200 is None else last < s200
    daily_up = bool(e20 is not None and s50 is not None and last > e20 and e20 >= s50 * 0.98 and above_long)
    daily_down = bool(e20 is not None and s50 is not None and last < e20 and e20 <= s50 * 1.02 and below_long)
    return {"ema20": e20, "sma50": s50, "sma200": s200, "up": daily_up, "down": daily_down, "ret20": ret20, "ret60": ret60}


def _score(bits: list[tuple[bool, str]]) -> tuple[int, str]:
    passed = [label for ok, label in bits if ok]
    return len(passed), "; ".join(passed)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _prior_entry_followup(current: StockSetup, prior: dict[str, Any] | None) -> StockSetup | None:
    if not prior:
        return None
    entry = _float_or_none(prior.get("trigger_level"))
    invalidation = _float_or_none(prior.get("exit_level"))
    target = _float_or_none(prior.get("target_level"))
    if entry is None or invalidation is None or entry <= 0:
        return None

    crossed_invalidation = current.last_price <= invalidation
    reached_target = target is not None and target > 0 and current.last_price >= target
    if not crossed_invalidation and not reached_target:
        return None

    risk_pct = abs(entry - invalidation) / entry * 100
    risk_reward = _float_or_none(prior.get("risk_reward")) or 2.0
    prior_key = str(prior.get("setup_key") or "prior-buy")
    if crossed_invalidation:
        reason = (
            "Prior Buy research setup follow-up: current price is at or below the stored exit/invalidation level. "
            "This is an automatic risk alert tied to the earlier Buy-style research alert, not a trading instruction."
        )
        key_kind = "invalidation"
        downside_reference = invalidation
    else:
        reason = (
            "Prior Buy research setup follow-up: current price reached or exceeded the stored research target. "
            "This is an automatic review/profit-risk alert tied to the earlier Buy-style research alert, not a trading instruction."
        )
        key_kind = "target-review"
        downside_reference = target

    return StockSetup(
        ticker=current.ticker,
        name=current.name,
        signal="Bad",
        setup_type="Exit/Risk",
        model_view="Sell",
        confidence="High" if crossed_invalidation else "Medium",
        timeframe=current.timeframe,
        last_price=current.last_price,
        trigger_level=current.last_price,
        exit_level=invalidation,
        target_level=downside_reference,
        rsi_14=current.rsi_14,
        ema_8=current.ema_8,
        ema_21=current.ema_21,
        ema_50=current.ema_50,
        daily_ema_20=current.daily_ema_20,
        daily_sma_50=current.daily_sma_50,
        atr_14=current.atr_14,
        volume_ratio_20=current.volume_ratio_20,
        risk_reward=risk_reward,
        risk_pct=risk_pct,
        reason=reason,
        setup_key=f"{current.ticker}:followup:{key_kind}:{prior_key}:{round(current.last_price, 2)}",
        technical_score=current.technical_score,
        max_technical_score=current.max_technical_score,
        confirmations=current.confirmations,
    )


def _neutral(
    ticker: str,
    name: str,
    last: float,
    reason: str,
    timeframe: str,
    rsi14: float | None = None,
    ema8: float | None = None,
    ema21: float | None = None,
    ema50: float | None = None,
    daily_ema20: float | None = None,
    daily_sma50: float | None = None,
    atr14: float | None = None,
    vol_ratio: float | None = None,
) -> StockSetup:
    return StockSetup(
        ticker=ticker,
        name=name,
        signal="Neutral",
        setup_type="None",
        model_view="Hold",
        confidence="None",
        timeframe=timeframe,
        last_price=last,
        trigger_level=None,
        exit_level=None,
        target_level=None,
        rsi_14=rsi14,
        ema_8=ema8,
        ema_21=ema21,
        ema_50=ema50,
        daily_ema_20=daily_ema20,
        daily_sma_50=daily_sma50,
        atr_14=atr14,
        volume_ratio_20=vol_ratio,
        risk_reward=None,
        risk_pct=None,
        reason=reason,
        setup_key=f"{ticker}:neutral",
    )


def analyze_bars(
    ticker: str,
    name: str,
    bars: list[dict[str, Any]],
    settings: dict[str, Any],
    daily_bars: list[dict[str, Any]] | None = None,
) -> StockSetup:
    timeframe = str(settings.get("timeframe_label", "Short-term swing focus: 1 week to 3 months"))
    if len(bars) < 60:
        last = float(bars[-1]["close"]) if bars else 0.0
        return _neutral(ticker, name, last, "Not enough hourly data for a high-quality setup.", timeframe)

    closes = [float(b["close"]) for b in bars]
    highs = [float(b["high"]) for b in bars]
    lows = [float(b["low"]) for b in bars]
    last = closes[-1]
    ema8 = ema(closes, 8)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    vol_ratio = _volume_ratio(bars, 20)
    macd_line, macd_signal, macd_hist = macd(closes)
    ret10 = _return_pct(closes, 10)
    ret20 = _return_pct(closes, 20)
    ema21_slope = _slope_pct([ema(closes[: i + 1], 21) or closes[i] for i in range(len(closes))], 5)
    daily = _daily_context(daily_bars)
    daily_ema20 = daily["ema20"]
    daily_sma50 = daily["sma50"]

    if ema8 is None or ema21 is None or ema50 is None or rsi14 is None or atr14 is None or atr14 <= 0:
        return _neutral(
            ticker,
            name,
            last,
            "Indicators unavailable, so no Telegram alert is sent.",
            timeframe,
            rsi14,
            ema8,
            ema21,
            ema50,
            daily_ema20,
            daily_sma50,
            atr14,
            vol_ratio,
        )

    lookback = int(settings.get("breakout_lookback_bars", 20))
    recent_high = max(highs[-lookback - 1 : -1]) if len(highs) > lookback else max(highs[:-1])
    recent_low = min(lows[-lookback - 1 : -1]) if len(lows) > lookback else min(lows[:-1])

    rr = float(settings.get("risk_reward_multiple", 2.0))
    atr_mult = float(settings.get("atr_multiple_stop", 1.4))
    breakout_buffer = float(settings.get("breakout_buffer_atr", 0.10)) * atr14
    near_trigger_atr = float(settings.get("near_trigger_atr_fraction", 0.35)) * atr14
    min_vol_high = float(settings.get("min_volume_ratio_high", 1.10))
    min_vol_medium = float(settings.get("min_volume_ratio_medium", 0.85))
    min_rr = float(settings.get("min_risk_reward", 1.8))
    max_risk_pct = min(float(settings.get("max_risk_pct", 12.0)), 14.99)

    entry_rsi_min = float(settings.get("entry_rsi_min", 50))
    entry_rsi_high_min = float(settings.get("entry_rsi_high_min", 55))
    entry_rsi_max = float(settings.get("entry_rsi_max", 72))
    exit_rsi_max = float(settings.get("exit_rsi_max", 46))
    exit_rsi_high_max = float(settings.get("exit_rsi_high_max", 40))

    volume_high = vol_ratio is not None and vol_ratio >= min_vol_high
    volume_ok = vol_ratio is not None and vol_ratio >= min_vol_medium

    entry_trigger = recent_high + breakout_buffer
    confirmed_breakout = last >= entry_trigger
    near_breakout = 0 <= (entry_trigger - last) <= near_trigger_atr
    uptrend = last > ema21 and ema8 > ema21 and ema21 >= ema50 * 0.985
    healthy_rsi = entry_rsi_min <= rsi14 <= entry_rsi_max
    macd_bullish = macd_hist is not None and macd_hist >= 0 and (macd_line or 0) >= (macd_signal or 0)
    momentum_ok = (ret10 is None or ret10 > -4.0) and (ret20 is None or ret20 > -6.0)
    ema_slope_ok = ema21_slope is None or ema21_slope >= -0.5
    daily_context_ok = daily["up"] is True

    entry_bits = [
        (uptrend, "EMA8 > EMA21 and price above EMA21"),
        (healthy_rsi, "RSI14 is constructive but not extremely overbought"),
        (daily_context_ok, "daily EMA/SMA context supports upside"),
        (volume_ok, "volume is acceptable versus 20-period average"),
        (confirmed_breakout or near_breakout, "clear breakout trigger exists"),
        (macd_bullish, "MACD confirms short-term momentum"),
        (momentum_ok, "10/20-period momentum is not weak"),
        (ema_slope_ok, "EMA21 slope is stable or rising"),
    ]
    entry_score, entry_summary = _score(entry_bits)

    if entry_score >= 6 and daily_context_ok and volume_ok and (confirmed_breakout or near_breakout):
        stop_candidate = min(ema21, recent_low + 0.20 * atr14)
        exit_level = min(stop_candidate, last - atr_mult * atr14)
        if exit_level >= entry_trigger:
            exit_level = entry_trigger - atr_mult * atr14
        risk = max(entry_trigger - exit_level, 0.01)
        target = entry_trigger + rr * risk
        rr_calc = (target - entry_trigger) / risk
        risk_pct = (risk / max(entry_trigger, 0.01)) * 100
        confidence = "High" if entry_score >= 7 and confirmed_breakout and rsi14 >= entry_rsi_high_min and volume_high else "Medium"
        if rr_calc < min_rr or risk_pct >= max_risk_pct:
            confidence = "Low"
        reason = (
            f"Research-only Buy setup passed {entry_score}/8 technical checks: {entry_summary}. "
            f"Risk is capped below {max_risk_pct:.2f}% by config; risk/reward is {_ratio(rr_calc)}x."
        )
        key = f"{ticker}:entry:{confidence}:{round(entry_trigger, 2)}:{round(exit_level, 2)}"
        return StockSetup(
            ticker,
            name,
            "Good",
            "Entry",
            "Buy",
            confidence,
            timeframe,
            last,
            entry_trigger,
            exit_level,
            target,
            rsi14,
            ema8,
            ema21,
            ema50,
            daily_ema20,
            daily_sma50,
            atr14,
            vol_ratio,
            rr_calc,
            risk_pct,
            reason,
            key,
            entry_score,
            8,
            entry_summary,
        )

    exit_trigger = recent_low - breakout_buffer
    confirmed_breakdown = last <= exit_trigger
    weak_near_breakdown = 0 <= (last - exit_trigger) <= near_trigger_atr
    downtrend = last < ema21 and ema8 < ema21 and ema21 <= ema50 * 1.015
    weak_rsi = rsi14 <= exit_rsi_max
    macd_bearish = macd_hist is not None and macd_hist <= 0 and (macd_line or 0) <= (macd_signal or 0)
    downside_momentum = (ret10 is None or ret10 < 4.0) and (ret20 is None or ret20 < 6.0)
    ema_slope_weak = ema21_slope is None or ema21_slope <= 0.5
    daily_risk_ok = daily["down"] is True

    exit_bits = [
        (downtrend, "price below EMA21 with EMA8 below EMA21"),
        (weak_rsi, "RSI14 is weak"),
        (daily_risk_ok, "daily EMA/SMA context shows risk"),
        (volume_ok, "volume is acceptable versus 20-period average"),
        (confirmed_breakdown or weak_near_breakdown, "clear exit/risk trigger exists"),
        (macd_bearish, "MACD confirms downside momentum"),
        (downside_momentum, "10/20-period momentum is not strong"),
        (ema_slope_weak, "EMA21 slope is flat or falling"),
    ]
    exit_score, exit_summary = _score(exit_bits)

    if exit_score >= 6 and daily_risk_ok and volume_ok and (confirmed_breakdown or weak_near_breakdown):
        risk_invalid = max(ema21, recent_high - 0.20 * atr14, last + atr_mult * atr14)
        risk = max(risk_invalid - exit_trigger, 0.01)
        downside_reference = exit_trigger - rr * risk
        rr_calc = (exit_trigger - downside_reference) / risk
        risk_pct = (risk / max(exit_trigger, 0.01)) * 100
        confidence = "High" if exit_score >= 7 and confirmed_breakdown and rsi14 <= exit_rsi_high_max and (volume_high or daily_risk_ok) else "Medium"
        if rr_calc < min_rr or risk_pct >= max_risk_pct:
            confidence = "Low"
        model_view = "Sell"
        reason = (
            f"Research-only Sell setup passed {exit_score}/8 technical checks: {exit_summary}. "
            f"Risk is capped below {max_risk_pct:.2f}% by config; risk/reward is {_ratio(rr_calc)}x."
        )
        key = f"{ticker}:exit:{model_view}:{confidence}:{round(exit_trigger, 2)}:{round(risk_invalid, 2)}"
        return StockSetup(
            ticker,
            name,
            "Bad",
            "Exit/Risk",
            model_view,
            confidence,
            timeframe,
            last,
            exit_trigger,
            risk_invalid,
            downside_reference,
            rsi14,
            ema8,
            ema21,
            ema50,
            daily_ema20,
            daily_sma50,
            atr14,
            vol_ratio,
            rr_calc,
            risk_pct,
            reason,
            key,
            exit_score,
            8,
            exit_summary,
        )

    return _neutral(
        ticker,
        name,
        last,
        "No high-quality short-term entry or exit/risk setup right now, so Telegram stays silent.",
        timeframe,
        rsi14,
        ema8,
        ema21,
        ema50,
        daily_ema20,
        daily_sma50,
        atr14,
        vol_ratio,
    )


def _action_message(setup: StockSetup) -> str:
    checks = f"{setup.technical_score}/{setup.max_technical_score}" if setup.max_technical_score else "n/a"
    reason = f"Technical checks: {checks}. {setup.reason}"
    if setup.setup_type == "Entry":
        return (
            "📈 Short-Term Stock Entry Setup\n\n"
            f"Ticker:\n{setup.ticker}\n\n"
            "Model view:\nBuy\n\n"
            "Signal:\nGood\n\n"
            f"Confidence:\n{setup.confidence}\n\n"
            f"Timeframe:\n{setup.timeframe}\n\n"
            f"Last price:\n{_money(setup.last_price)}\n\n"
            f"Entry trigger:\n{_money(setup.trigger_level)}\n\n"
            f"Exit / invalidation level:\n{_money(setup.exit_level)}\n\n"
            f"Research target:\n{_money(setup.target_level)}\n\n"
            f"Risk:\n{_pct(setup.risk_pct)} invalidation risk; risk/reward {_ratio(setup.risk_reward)}x\n\n"
            f"Reason:\n{reason}\n\n"
            "Warning:\nNot financial advice. This is a research signal, not an instruction to buy, sell, short, hold, or trade."
        )

    return (
        "📉 Short-Term Stock Exit/Risk Setup\n\n"
        f"Ticker:\n{setup.ticker}\n\n"
        f"Model view:\n{setup.model_view}\n\n"
        "Signal:\nBad\n\n"
        f"Confidence:\n{setup.confidence}\n\n"
        f"Timeframe:\n{setup.timeframe}\n\n"
        f"Last price:\n{_money(setup.last_price)}\n\n"
        f"Exit/risk trigger:\n{_money(setup.trigger_level)}\n\n"
        f"Invalidation / recovery level:\n{_money(setup.exit_level)}\n\n"
        f"Downside reference:\n{_money(setup.target_level)}\n\n"
        f"Risk:\n{_pct(setup.risk_pct)} invalidation/recovery risk; risk/reward {_ratio(setup.risk_reward)}x\n\n"
        f"Reason:\n{reason}\n\n"
        "Warning:\nNot financial advice. This is a research signal, not an instruction to buy, sell, short, hold, or trade."
    )


def _confidence_ok(confidence: str, minimum: str) -> bool:
    return CONFIDENCE_RANK.get(confidence, 0) >= CONFIDENCE_RANK.get(minimum, 2)


def _ticker_name_map(cfg: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in cfg.get("priority_stocks", []):
        out[str(item["ticker"]).upper()] = str(item.get("name", item["ticker"]))
    for t in cfg.get("universe", []):
        out.setdefault(str(t).upper(), str(t).upper())
    return out


def hourly_scan(cfg: dict[str, Any], db: StockResearchDB, telegram: TelegramClient) -> int:
    settings = cfg.get("settings", {})
    ticker_names = _ticker_name_map(cfg)
    priority = [str(x["ticker"]).upper() for x in cfg.get("priority_stocks", [])]
    candidates = db.load_candidate_tickers()
    tickers: list[str] = []
    for t in priority + candidates:
        if t and t not in tickers:
            tickers.append(t)
    if not tickers:
        tickers = priority

    min_conf = str(settings.get("min_setup_confidence", "High"))
    max_alerts = int(settings.get("max_alerts_per_run", 5))
    silence_hours = int(settings.get("duplicate_silence_hours", 24))
    min_successful_scans = int(settings.get("min_successful_scans", 1))
    max_risk_pct = min(float(settings.get("max_risk_pct", 12.0)), 14.99)
    sent = 0
    successful_data_scans = 0
    failed_scans = 0

    for ticker in tickers:
        try:
            bars = fetch_bars(ticker, settings.get("hourly_period", "30d"), settings.get("hourly_interval", "1h"))
            daily_bars = fetch_bars(ticker, settings.get("daily_period", "6mo"), settings.get("daily_interval", "1d"))
            if len(bars) >= 60:
                successful_data_scans += 1
            setup = analyze_bars(ticker, ticker_names.get(ticker, ticker), bars, settings, daily_bars)
            prior_entry = db.load_open_entry_setup(ticker)
            followup = _prior_entry_followup(setup, prior_entry)
            if followup is not None:
                setup = followup
            db.store_scan(ticker, asdict(setup))
            log.info(
                "Stock scan %s: signal=%s setup=%s model_view=%s confidence=%s checks=%s/%s actionable=%s reason=%s",
                ticker,
                setup.signal,
                setup.setup_type,
                setup.model_view,
                setup.confidence,
                setup.technical_score,
                setup.max_technical_score,
                setup.actionable,
                setup.reason,
            )
        except Exception as exc:
            failed_scans += 1
            log.exception("Stock fetch/analyze failed for %s: %s", ticker, exc)
            continue

        if not setup.actionable:
            continue
        if not _confidence_ok(setup.confidence, min_conf):
            continue
        if setup.risk_reward is None or setup.risk_reward < float(settings.get("min_risk_reward", 1.8)):
            continue
        if setup.risk_pct is None or setup.risk_pct >= max_risk_pct:
            continue
        if db.seen_recent(setup.setup_key, silence_hours):
            continue
        if db.seen_ticker_signal_recent(setup.ticker, setup.signal, silence_hours):
            continue
        if not telegram.enabled:
            log.warning("Actionable stock setup skipped because Telegram is not configured: %s", setup.setup_key)
            continue

        try:
            telegram.send_text(_action_message(setup))
        except Exception:
            log.exception("Telegram stock alert failed; setup will not be recorded as sent: %s", setup.setup_key)
            raise

        payload = asdict(setup)
        db.store_alert(setup.ticker, setup.signal, setup.setup_key, payload)
        if setup.setup_type == "Entry" and setup.model_view == "Buy":
            db.open_entry_setup(setup.ticker, setup.setup_key, payload)
        elif setup.setup_type == "Exit/Risk" and setup.model_view == "Sell":
            db.close_entry_setup(setup.ticker, payload)
        sent += 1
        if sent >= max_alerts:
            break

    log.info(
        "Hourly stock scan complete. successful_data_scans=%s failed_scans=%s Telegram stock alerts sent=%s",
        successful_data_scans,
        failed_scans,
        sent,
    )
    if successful_data_scans < min_successful_scans:
        log.error("Not enough successful market-data scans: %s < %s", successful_data_scans, min_successful_scans)
        return 1
    return 0


def _discovery_score(ticker: str, bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(bars) < 60:
        return None
    closes = [float(b["close"]) for b in bars]
    vols = [float(b.get("volume", 0)) for b in bars]
    last = closes[-1]
    ret20 = (closes[-1] / closes[-21] - 1) if len(closes) > 21 and closes[-21] else 0.0
    ret60 = (closes[-1] / closes[-61] - 1) if len(closes) > 61 and closes[-61] else ret20
    volatility = atr([float(b["high"]) for b in bars], [float(b["low"]) for b in bars], closes, 14) or 0.0
    vol_ratio = _volume_ratio(bars, 20) or 0.0
    avg_volume = _avg(vols[-20:]) or 0.0
    dollar_volume = avg_volume * last
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    trend_bonus = 0.0
    if e20 and e50 and last > e20 > e50:
        trend_bonus = 0.25
    elif e20 and e50 and last < e20 < e50:
        trend_bonus = 0.20
    liquidity_score = min(dollar_volume / 25_000_000, 2.0)
    motion_score = min(abs(ret20) * 8 + abs(ret60) * 3 + (volatility / max(last, 0.01)) * 20, 3.0)
    volume_score = min(vol_ratio, 2.0)
    score = liquidity_score + motion_score + volume_score + trend_bonus
    return {
        "ticker": ticker,
        "score": score,
        "last_price": last,
        "ret20": ret20,
        "ret60": ret60,
        "volume_ratio": vol_ratio,
        "avg_dollar_volume": dollar_volume,
    }


def discover_candidates(cfg: dict[str, Any], db: StockResearchDB, telegram: TelegramClient) -> int:
    settings = cfg.get("settings", {})
    universe = [str(x).upper() for x in cfg.get("universe", [])]
    limit = int(settings.get("max_scan_symbols_per_run", 40))
    top_n = int(settings.get("top_candidate_count", 10))
    scored: list[dict[str, Any]] = []
    failures = 0
    for ticker in universe[:limit]:
        try:
            bars = fetch_bars(ticker, settings.get("discovery_period", "6mo"), settings.get("discovery_interval", "1d"))
            item = _discovery_score(ticker, bars)
            if item:
                scored.append(item)
        except Exception as exc:
            failures += 1
            log.warning("Discovery scan failed for %s: %s", ticker, exc)
            continue
    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_n]
    db.replace_candidates(top)
    log.info("Candidate refresh complete. scanned=%s scored=%s failures=%s top=%s", min(limit, len(universe)), len(scored), failures, [x["ticker"] for x in top])
    if settings.get("send_candidate_refresh_telegram", False) and telegram.enabled:
        lines = ["Stock candidate refresh", "", "Top candidates:"]
        lines.extend(f"{i+1}. {x['ticker']} score={x['score']:.2f}" for i, x in enumerate(top))
        telegram.send_text("\n".join(lines))
    return 0 if scored else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["hourly", "discover"], default="hourly")
    parser.add_argument("--config", default="config/stocks.yaml")
    args = parser.parse_args(argv)
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    cfg = load_stock_config(args.config)
    db = StockResearchDB(os.getenv("STOCK_SQLITE_PATH", "data/stocks.sqlite3"))
    db.init()
    telegram = TelegramClient(os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", ""))
    if args.mode == "discover":
        return discover_candidates(cfg, db, telegram)
    return hourly_scan(cfg, db, telegram)


if __name__ == "__main__":
    raise SystemExit(main())
