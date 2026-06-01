from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in TRUE_VALUES


def int_env(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return int(val)


def list_env(name: str, default: list[str] | None = None) -> list[str]:
    val = os.getenv(name)
    if not val:
        return default or []
    return [x.strip() for x in val.split(",") if x.strip()]


@dataclass(slots=True)
class Settings:
    root_dir: Path
    source_config: Path
    entity_config: Path
    database_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    discord_webhook_url: str
    email_enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str
    email_to: str
    poll_seconds: int
    run_once: bool
    alert_lookback_minutes: int
    max_items_per_source: int
    log_level: str
    truth_social_enabled: bool
    truth_social_handle: str
    truth_social_user_id: str
    include_truth_reposts: bool
    x_enabled: bool
    x_bearer_token: str
    x_username: str
    x_user_id: str
    youtube_enabled: bool
    youtube_check_transcripts: bool
    youtube_transcript_langs: list[str]
    rss_enabled: bool
    fetch_rss_articles: bool
    min_quote_chars: int
    max_telegram_quote_chars: int
    allow_article_snippets: bool
    trusted_transcript_domains: list[str]
    send_startup_message: bool
    heartbeat_hours: int
    retention_days: int
    check_run_retention_days: int
    send_error_alerts: bool
    error_alert_hours: int

    @classmethod
    def load(cls) -> "Settings":
        root = Path(__file__).resolve().parents[1]
        env_path = root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        source_config = Path(os.getenv("SOURCE_CONFIG", root / "config" / "sources.yaml"))
        entity_config = Path(os.getenv("ENTITY_CONFIG", root / "config" / "entities.yaml"))

        return cls(
            root_dir=root,
            source_config=source_config,
            entity_config=entity_config,
            database_url=os.getenv("DATABASE_URL", "sqlite:///data/alerts.db"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            email_enabled=bool_env("EMAIL_ENABLED", False),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int_env("SMTP_PORT", 587),
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            email_from=os.getenv("EMAIL_FROM", ""),
            email_to=os.getenv("EMAIL_TO", ""),
            poll_seconds=max(20, int_env("POLL_SECONDS", 90)),
            run_once=bool_env("RUN_ONCE", False),
            alert_lookback_minutes=int_env("ALERT_LOOKBACK_MINUTES", 1440),
            max_items_per_source=max(1, int_env("MAX_ITEMS_PER_SOURCE", 20)),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            truth_social_enabled=bool_env("TRUTH_SOCIAL_ENABLED", True),
            truth_social_handle=os.getenv("TRUTH_SOCIAL_HANDLE", "realDonaldTrump"),
            truth_social_user_id=os.getenv("TRUTH_SOCIAL_USER_ID", "107780257626128497"),
            include_truth_reposts=bool_env("INCLUDE_TRUTH_REPOSTS", False),
            x_enabled=bool_env("X_ENABLED", False),
            x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
            x_username=os.getenv("X_USERNAME", "realDonaldTrump"),
            x_user_id=os.getenv("X_USER_ID", ""),
            youtube_enabled=bool_env("YOUTUBE_ENABLED", True),
            youtube_check_transcripts=bool_env("YOUTUBE_CHECK_TRANSCRIPTS", True),
            youtube_transcript_langs=list_env("YOUTUBE_TRANSCRIPT_LANGS", ["en", "en-US"]),
            rss_enabled=bool_env("RSS_ENABLED", True),
            fetch_rss_articles=bool_env("FETCH_RSS_ARTICLES", True),
            min_quote_chars=int_env("MIN_QUOTE_CHARS", 6),
            max_telegram_quote_chars=int_env("MAX_TELEGRAM_QUOTE_CHARS", 1800),
            allow_article_snippets=bool_env("ALLOW_ARTICLE_SNIPPETS", False),
            trusted_transcript_domains=list_env(
                "TRUSTED_TRANSCRIPT_DOMAINS",
                ["rev.com", "weforum.org", "trump-archive.com", "whitehouse.gov"],
            ),
            send_startup_message=bool_env("SEND_STARTUP_MESSAGE", False),
            heartbeat_hours=int_env("HEARTBEAT_HOURS", 0),
            retention_days=int_env("RETENTION_DAYS", 180),
            check_run_retention_days=int_env("CHECK_RUN_RETENTION_DAYS", 30),
            send_error_alerts=bool_env("SEND_ERROR_ALERTS", True),
            error_alert_hours=int_env("ERROR_ALERT_HOURS", 6),
        )


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data
