from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(slots=True)
class AppConfig:
    root: Path
    database_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    discord_webhook_url: str | None
    email_enabled: bool
    log_level: str
    run_once: bool
    max_item_age_hours: int
    error_alert_min_interval_minutes: int
    cleanup_raw_days: int
    cleanup_runs_days: int
    sources: dict[str, Any]
    entities: dict[str, Any]

    @classmethod
    def load(cls, root: str | Path | None = None) -> "AppConfig":
        root_path = Path(root or os.getenv("APP_ROOT") or Path.cwd()).resolve()
        sources_file = Path(os.getenv("SOURCES_FILE", root_path / "config" / "sources.yaml"))
        entities_file = Path(os.getenv("ENTITIES_FILE", root_path / "config" / "entities.yaml"))

        with sources_file.open("r", encoding="utf-8") as f:
            sources = yaml.safe_load(f) or {}
        with entities_file.open("r", encoding="utf-8") as f:
            entities = yaml.safe_load(f) or {}

        polling = sources.get("polling", {}) or {}
        return cls(
            root=root_path,
            database_url=os.getenv("DATABASE_URL", "sqlite:///data/alerts.db"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL") or None,
            email_enabled=env_bool("EMAIL_ENABLED", False),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            run_once=env_bool("RUN_ONCE", True),
            max_item_age_hours=env_int("MAX_ITEM_AGE_HOURS", int(polling.get("max_item_age_hours", 72))),
            error_alert_min_interval_minutes=env_int("ERROR_ALERT_MIN_INTERVAL_MINUTES", 360),
            cleanup_raw_days=env_int("CLEANUP_RAW_DAYS", int(polling.get("cleanup_raw_days", 180))),
            cleanup_runs_days=env_int("CLEANUP_RUNS_DAYS", int(polling.get("cleanup_runs_days", 30))),
            sources=sources,
            entities=entities,
        )


def source_enabled(cfg: dict[str, Any], env_name: str, default: bool = True) -> bool:
    return env_bool(env_name, bool(cfg.get("enabled", default)))
