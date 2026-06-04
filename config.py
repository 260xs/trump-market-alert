from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    telegram_bot_token: str
    telegram_chat_id: str
    discord_webhook_url: str
    x_bearer_token: str
    healthchecks_url: str
    min_strict_confidence: float
    max_statement_age_hours: int
    enable_inferred_alerts: bool
    enable_live_audio: bool
    enable_provisional_live_alerts: bool
    live_sample_seconds: int
    live_min_source_confidence: float
    live_min_speaker_confidence: float
    live_min_quote_confidence: float
    run_once: bool
    log_level: str


def load_settings() -> Settings:
    sqlite_path = Path(os.getenv("SQLITE_PATH", "data/market_alerts.sqlite3"))
    return Settings(
        sqlite_path=sqlite_path,
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
        healthchecks_url=os.getenv("HEALTHCHECKS_URL", ""),
        min_strict_confidence=_env_float("MIN_STRICT_CONFIDENCE", 0.95),
        max_statement_age_hours=_env_int("MAX_STATEMENT_AGE_HOURS", 48),
        enable_inferred_alerts=_env_bool("ENABLE_INFERRED_ALERTS", False),
        enable_live_audio=_env_bool("ENABLE_LIVE_AUDIO", False),
        enable_provisional_live_alerts=_env_bool("ENABLE_PROVISIONAL_LIVE_ALERTS", True),
        live_sample_seconds=_env_int("LIVE_SAMPLE_SECONDS", 90),
        live_min_source_confidence=_env_float("LIVE_MIN_SOURCE_CONFIDENCE", 0.75),
        live_min_speaker_confidence=_env_float("LIVE_MIN_SPEAKER_CONFIDENCE", 0.70),
        live_min_quote_confidence=_env_float("LIVE_MIN_QUOTE_CONFIDENCE", 0.60),
        run_once=_env_bool("RUN_ONCE", False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Missing required config file: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def load_watchlist(path: str | Path = "watchlist.yaml") -> dict[str, Any]:
    return load_yaml(path)


def load_asset_map(path: str | Path = "config/asset_map.yaml") -> dict[str, Any]:
    return load_yaml(path)
