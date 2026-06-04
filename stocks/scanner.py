from __future__ import annotations

import argparse
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from alerts.telegram import TelegramClient
from stocks.indicators import atr, ema, rsi, sma
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
    model_view: str  # Buy, Sell, Short, Hold. Research label only, not advice.
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

    @property
    def actionable(self) -> bool:
        return (
            self.signal in {"Good", "Bad"}
            and self.setup_type in {"Entry", "Exit/Risk"}
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


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}x"


def _ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


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


def _daily_context(daily_bars: list[dict[str, Any]] | None) -> tuple[float | None, float | None, bool | None, bool | None]:
    if not daily_bars or len(daily_bars) < 50:
        return None, None, None, None
    closes = [float(b["close"]) for b in daily_bars]
    last = closes[-1]
    e20 = ema(closes, 20)
    s50 = sma(closes, 50)
    daily_up = bool(e20 is not None and s50 is not None and last > e20 and e20 >= s50 * 0.98)
    daily_down = bool(e20 is not None and s50 is not None and last < e20 and e20 <= s50 * 1.02)
    return e20, s50, daily_up, daily_down


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
    daily_ema20, daily_sma50, daily_up, daily_down = _daily_context(daily_bars)

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
    max_risk_pct = float(settings.get("max_risk_pct", 9.0))

    entry_rsi_min = float(settings.get("entry_rsi_min", 50))
    entry_rsi_high_min = float(settings.get("entry_rsi_high_min", 55))
    entry_rsi_max = float(settings.get("entry_rsi_max", 72))
    exit_rsi_max = float(settings.get("exit_rsi_max", 46))
    exit_rsi_high_max = float(settings.get("exit_rsi_high_max", 40))

    entry_trigger = recent_high + breakout_buffer
    confirmed_breakout = last >= entry_trigger
    near_breakout = 0 <= (entry_trigger - last) <= near_trigger_atr
    uptrend = last > ema21 and ema8 > ema21 and ema21 >= ema50 * 0.985
    healthy_rsi = entry_rsi_min <= rsi14 <= entry_rsi_max
    daily_context_ok = daily_up is True
    volume_high = vol_ratio is not None and vol_ratio >= min_vol_high
    volume_ok = vol_ratio is not None and vol_ratio >= min_vol_medium

    if uptrend and healthy_rsi and daily_context_ok and volume_ok and (confirmed_breakout or near_breakout):
        stop_candidate = min(ema21, recent_low + 0.20 * atr14)
        exit_level = min(stop_candidate, last - atr_mult * atr14)
        if exit_level >= entry_trigger:
            exit_level = entry_trigger - atr_mult * atr14
        risk = max(entry_trigger - exit_level, 0.01)
        target = entry_trigger + rr * risk
        rr_calc = (target - entry_trigger) / risk
        risk_pct = (risk / max(entry_trigger, 0.01)) * 100
        confidence = "High" if confirmed_breakout and rsi14 >= entry_rsi_high_min and volume_high and daily_up is True else "Medium"
        if rr_calc < min_rr or risk_pct > max_risk_pct:
            confidence = "Low"
        reason_bits = [
            "short-term uptrend is confirmed by EMA8 > EMA21",
            "RSI is constructive but not extremely overbought",
            "a clear entry trigger and exit/invalidation level are available",
        ]
        if confirmed_breakout:
            reason_bits.append("price has confirmed the breakout trigger")
        else:
            reason_bits.append("price is close enough to the breakout trigger to monitor as an entry setup")
        if daily_up is True:
            reason_bits.append("daily context supports the short-term setup")
        if volume_high:
            reason_bits.append("volume confirms the move")
        reason = "; ".join(reason_bits) + "."
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
        )

    exit_trigger = recent_low - breakout_buffer
    confirmed_breakdown = last <= exit_trigger
    weak_near_breakdown = 0 <= (last - exit_trigger) <= near_trigger_atr
    downtrend = last < ema21 and ema8 < ema21 and ema21 <= ema50 * 1.015
    weak_rsi = rsi14 <= exit_rsi_max
    daily_risk_ok = daily_down is True

    if downtrend and weak_rsi and daily_risk_ok and volume_ok and (confirmed_breakdown or weak_near_breakdown):
        risk_invalid = max(ema21, recent_high - 0.20 * atr14, last + atr_mult * atr14)
        risk = max(risk_invalid - exit_trigger, 0.01)
        downside_reference = exit_trigger - rr * risk
        rr_calc = (exit_trigger - downside_reference) / risk
        risk_pct = (risk / max(exit_trigger, 0.01)) * 100
        confidence = "High" if confirmed_breakdown and rsi14 <= exit_rsi_high_max and (volume_high or daily_down is True) else "Medium"
        if rr_calc < min_rr or risk_pct > max_risk_pct:
            confidence = "Low"
        reason_bits = [
            "short-term risk is confirmed by price below EMA21",
            "EMA8 is below EMA21",
            "RSI is weak",
            "a clear exit/risk trigger and invalidation level are available",
        ]
        if confirmed_breakdown:
            reason_bits.append("price has confirmed the breakdown trigger")
        if daily_down is True:
            reason_bits.append("daily context also shows risk")
        reason = "; ".join(reason_bits) + "."
        model_view = "Short" if confirmed_breakdown and bool(settings.get("allow_short_model_view", True)) else "Sell"
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
    if setup.setup_type == "Entry":
        icon = "📈"
        title = "Short-Term Stock Entry Setup"
        trigger_label = "Entry trigger"
        exit_label = "Exit / invalidation level"
        target_label = "Research target"
    elif setup.model_view == "Short":
        icon = "📉"
        title = "Short-Term Stock Short Setup"
        trigger_label = "Short trigger"
        exit_label = "Short invalidation / cover level"
        target_label = "Downside reference"
    else:
        icon = "📉"
        title = "Short-Term Stock Exit/Risk Setup"
        trigger_label = "Sell/risk trigger"
        exit_label = "Recovery / invalidation level"
        target_label = "Downside reference"

    return (
        f"{icon} {title}\n\n"
        f"Ticker:\n{setup.ticker} — {setup.name}\n\n"
        f"Model view (research only):\n{setup.model_view}\n\n"
        f"Signal quality:\n{setup.signal}\n\n"
        f"Confidence:\n{setup.confidence}\n\n"
        f"Timeframe:\n{setup.timeframe}\n\n"
        f"Last price:\n{_money(setup.last_price)}\n\n"
        f"{trigger_label}:\n{_money(setup.trigger_level)}\n\n"
        f"{exit_label}:\n{_money(setup.exit_level)}\n\n"
        f"{target_label}:\n{_money(setup.target_level)}\n\n"
        f"Risk/reward reference:\n{_ratio(setup.risk_reward)}R\n\n"
        f"Trigger-to-exit risk:\n{_ratio(setup.risk_pct)}%\n\n"
        f"Indicators:\n"
        f"RSI14 {_money(setup.rsi_14)} | EMA8 {_money(setup.ema_8)} | EMA21 {_money(setup.ema_21)} | EMA50 {_money(setup.ema_50)} | Volume ratio {_pct(setup.volume_ratio_20)}\n\n"
        f"Why this alert was sent:\n{setup.reason}\n\n"
        "Warning:\nResearch only. This is not financial advice and not an instruction to buy, sell, short, hold, or trade. Verify chart, news, liquidity, spread, and risk before acting."
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

    min_conf = str(settings.get("min_setup_confidence", "Medium"))
    max_alerts = int(settings.get("max_alerts_per_run", 5))
    silence_hours = int(settings.get("duplicate_silence_hours", 24))
    min_successful_scans = int(settings.get("min_successful_scans", 1))
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
            db.store_scan(ticker, asdict(setup))
            log.info(
                "Stock scan %s: signal=%s setup=%s model_view=%s confidence=%s actionable=%s reason=%s",
                ticker,
                setup.signal,
                setup.setup_type,
                setup.model_view,
                setup.confidence,
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
        if setup.risk_pct is None or setup.risk_pct > float(settings.get("max_risk_pct", 9.0)):
            continue
        if db.seen_recent(setup.setup_key, silence_hours):
            continue
        if db.seen_ticker_signal_recent(setup.ticker, setup.signal, silence_hours):
            continue

        if telegram.enabled:
            telegram.send_text(_action_message(setup))
        db.store_alert(setup.ticker, setup.signal, setup.setup_key, asdict(setup))
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
    ret60 = (closes[-1] / closes[-61] - 1) if len(closes) > 61 and closes[-61] else 0.0
    s50 = sma(closes, 50) or last
    avg_vol20 = sum(vols[-20:]) / max(len(vols[-20:]), 1)
    trend_bonus = 1.0 if last > s50 else -0.5
    liquidity_score = min(avg_vol20 / 2_000_000, 3.0)
    momentum_score = (ret20 * 100) + (ret60 * 40)
    score = momentum_score + liquidity_score + trend_bonus
    return {
        "ticker": ticker,
        "score": round(score, 3),
        "last_price": round(last, 2),
        "return_20d_pct": round(ret20 * 100, 2),
        "return_60d_pct": round(ret60 * 100, 2),
        "above_sma50": last > s50,
        "avg_volume_20d": int(avg_vol20),
    }


def discover_candidates(cfg: dict[str, Any], db: StockResearchDB, telegram: TelegramClient) -> int:
    settings = cfg.get("settings", {})
    universe = [str(t).upper() for t in cfg.get("universe", [])]
    max_symbols = int(settings.get("max_scan_symbols_per_run", 35))
    top_n = int(settings.get("top_candidate_count", 5))
    priority = {str(x["ticker"]).upper() for x in cfg.get("priority_stocks", [])}
    scores: list[dict[str, Any]] = []
    for ticker in universe[:max_symbols]:
        try:
            bars = fetch_bars(ticker, settings.get("discovery_period", "6mo"), settings.get("discovery_interval", "1d"))
            scored = _discovery_score(ticker, bars)
            if scored:
                if ticker in priority:
                    scored["score"] += 2.0
                    scored["priority_boost"] = True
                scores.append(scored)
        except Exception as exc:
            log.warning("Discovery failed for %s: %s", ticker, exc)
    scores.sort(key=lambda x: x["score"], reverse=True)
    top = scores[:top_n]
    db.save_candidates(top)
    log.info("Saved %s top research candidates: %s", len(top), [x["ticker"] for x in top])

    # Candidate refresh is silent by default. Telegram is reserved for actionable
    # High/Medium confidence entry or exit/risk setups from the hourly scanner.
    if telegram.enabled and top and bool(settings.get("send_candidate_refresh_telegram", False)):
        lines = [f"{i}. {x['ticker']} — score {x['score']}, 20d {x['return_20d_pct']}%, 60d {x['return_60d_pct']}%" for i, x in enumerate(top, 1)]
        telegram.send_text(
            "🔎 3-Day Stock Candidate Refresh\n\n"
            + "\n".join(lines)
            + "\n\nThese are research candidates only. Hourly Telegram alerts are still sent only for High/Medium confidence entry or exit/risk setups."
        )
    return 0


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)sZ %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["hourly", "discover"], default="hourly")
    parser.add_argument("--config", default="config/stocks.yaml")
    args = parser.parse_args()

    cfg = load_stock_config(args.config)
    db = StockResearchDB(os.getenv("STOCK_SQLITE_PATH", "data/stocks.sqlite3"))
    db.init()
    telegram = TelegramClient(os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("TELEGRAM_CHAT_ID", ""))

    if args.mode == "discover":
        return discover_candidates(cfg, db, telegram)
    return hourly_scan(cfg, db, telegram)


if __name__ == "__main__":
    raise SystemExit(main())
