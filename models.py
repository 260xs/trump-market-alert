from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_DIR = ROOT_DIR / "config"


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables.

    Secrets must come from GitHub Actions secrets or a local .env file.
    Public source/entity configuration lives in YAML files under config/.
    """

    telegram_bot_token: str
    telegram_chat_id: str
    database_url: str
    discord_webhook_url: str | None
    x_bearer_token: str | None
    log_level: str
    sources_path: Path
    entities_path: Path

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def discord_configured(self) -> bool:
        return bool(self.discord_webhook_url)

    @property
    def x_api_configured(self) -> bool:
        return bool(self.x_bearer_token)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _path_from_env(name: str, default: Path) -> Path:
    raw = _env(name)
    return Path(raw).expanduser() if raw else default


def load_settings(load_dotenv_file: bool = True) -> Settings:
    """Load environment-backed settings.

    GitHub Actions provides secrets as environment variables. The .env loader is
    only for local testing and does nothing if no .env file exists.
    """

    if load_dotenv_file:
        load_dotenv()

    return Settings(
        telegram_bot_token=_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
        database_url=_env("DATABASE_URL"),
        discord_webhook_url=_env("DISCORD_WEBHOOK_URL") or None,
        x_bearer_token=_env("X_BEARER_TOKEN") or None,
        log_level=_env("LOG_LEVEL", "INFO").upper(),
        sources_path=_path_from_env("SOURCES_PATH", DEFAULT_CONFIG_DIR / "sources.yaml"),
        entities_path=_path_from_env("ENTITIES_PATH", DEFAULT_CONFIG_DIR / "entities.yaml"),
    )


def require_settings(settings: Settings) -> None:
    """Fail fast when required secrets are missing or clearly invalid."""

    missing: list[str] = []
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if not settings.database_url:
        missing.append("DATABASE_URL")

    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

    if not settings.database_url.startswith(("postgresql://", "postgres://")):
        raise ConfigError("DATABASE_URL must start with postgresql:// or postgres://")

    if "://" not in settings.database_url or "@" not in settings.database_url:
        raise ConfigError("DATABASE_URL does not look like a complete Postgres connection string")


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from disk with clear error messages."""

    resolved = path.expanduser()
    if not resolved.exists():
        raise FileNotFoundError(f"Config file not found: {resolved}")

    with resolved.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a YAML mapping: {resolved}")

    return data


def get_mapping(data: Mapping[str, Any], key: str) -> dict[str, Any]:
    """Return a nested mapping or an empty dict.

    This keeps the rest of the project safe when optional YAML sections are
    missing or disabled.
    """

    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


__all__ = [
    "ConfigError",
    "DEFAULT_CONFIG_DIR",
    "ROOT_DIR",
    "Settings",
    "get_mapping",
    "load_settings",
    "load_yaml",
    "require_settings",
]
