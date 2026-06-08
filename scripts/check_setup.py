from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

import requests


REQUIRED_ENV = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
OPTIONAL_ENV = (
    "X_BEARER_TOKEN",
    "HEALTHCHECKS_URL",
    "RUNNER_HEALTHCHECKS_URL",
    "STOCK_HEALTHCHECKS_URL",
    "CANDIDATE_HEALTHCHECKS_URL",
    "GITHUB_ACTIONS_TOKEN",
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ok(message: str) -> None:
    print(f"OK: {message}")


def _warn(message: str) -> None:
    print(f"WARN: {message}")


def _fail(message: str) -> None:
    print(f"FAIL: {message}")


def _check_env() -> int:
    errors = 0
    for key in REQUIRED_ENV:
        if os.getenv(key, "").strip():
            _ok(f"{key} is set")
        else:
            _fail(f"{key} is missing")
            errors += 1
    for key in OPTIONAL_ENV:
        if os.getenv(key, "").strip():
            _ok(f"{key} is set")
        else:
            _warn(f"{key} is not set")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if chat_id and not chat_id.lstrip("-").isdigit():
        _fail("TELEGRAM_CHAT_ID must be numeric")
        errors += 1
    return errors


def _check_paths() -> int:
    errors = 0
    for key, default in (
        ("SQLITE_PATH", "data/market_alerts.sqlite3"),
        ("STOCK_SQLITE_PATH", "data/stocks.sqlite3"),
    ):
        path = Path(os.getenv(key, default))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(path)
            con.execute("CREATE TABLE IF NOT EXISTS setup_probe (id INTEGER PRIMARY KEY)")
            con.execute("DROP TABLE setup_probe")
            con.close()
            _ok(f"{key} is writable at {path}")
        except Exception as exc:
            _fail(f"{key} is not writable at {path}: {exc}")
            errors += 1
    return errors


def _telegram_api(method: str, payload: dict[str, Any] | None = None) -> requests.Response:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    url = f"https://api.telegram.org/bot{token}/{method}"
    if payload is None:
        return requests.get(url, timeout=20)
    return requests.post(url, data=payload, timeout=20)


def _check_telegram(send_test: bool, clear_webhook: bool) -> int:
    if not os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or not os.getenv("TELEGRAM_CHAT_ID", "").strip():
        _warn("Skipping Telegram API checks because Telegram env values are missing")
        return 0
    errors = 0
    try:
        response = _telegram_api("getMe")
        response.raise_for_status()
        data = response.json()
        if data.get("ok"):
            username = (data.get("result") or {}).get("username", "unknown")
            _ok(f"Telegram bot token works (@{username})")
        else:
            _fail(f"Telegram getMe returned not ok: {data}")
            errors += 1
    except Exception as exc:
        _fail(f"Telegram getMe failed: {exc}")
        errors += 1

    if clear_webhook:
        try:
            response = _telegram_api("deleteWebhook", {"drop_pending_updates": "true"})
            response.raise_for_status()
            _ok("Telegram webhook removed and pending updates dropped")
        except Exception as exc:
            _fail(f"Telegram deleteWebhook failed: {exc}")
            errors += 1

    if send_test:
        try:
            response = _telegram_api(
                "sendMessage",
                {
                    "chat_id": os.getenv("TELEGRAM_CHAT_ID", "").strip(),
                    "text": "✅ Telegram test successful",
                    "disable_web_page_preview": "true",
                },
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                _ok("Telegram test message sent")
            else:
                _fail(f"Telegram sendMessage returned not ok: {data}")
                errors += 1
        except Exception as exc:
            _fail(f"Telegram sendMessage failed: {exc}")
            errors += 1
    return errors


def _check_github() -> int:
    token = os.getenv("GITHUB_ACTIONS_TOKEN", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "260xs/trump-market-alert").strip()
    if not token:
        _warn("Skipping GitHub workflow check because GITHUB_ACTIONS_TOKEN is not set")
        return 0
    try:
        response = requests.get(
            f"https://api.github.com/repos/{repo}/actions/workflows",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20,
        )
        response.raise_for_status()
        _ok("GitHub token can read workflow metadata")
        return 0
    except Exception as exc:
        _fail(f"GitHub workflow metadata check failed: {exc}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Check market-alert setup without printing secrets.")
    parser.add_argument("--env-file", default="/etc/market-alert.env")
    parser.add_argument("--send-telegram-test", action="store_true")
    parser.add_argument("--clear-telegram-webhook", action="store_true")
    args = parser.parse_args()

    _load_env_file(Path(args.env_file))
    errors = 0
    errors += _check_env()
    errors += _check_paths()
    errors += _check_telegram(args.send_telegram_test, args.clear_telegram_webhook)
    errors += _check_github()

    if errors:
        _fail(f"setup check completed with {errors} problem(s)")
        return 1
    _ok("setup check completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
