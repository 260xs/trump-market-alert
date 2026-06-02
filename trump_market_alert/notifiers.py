from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Iterable

import requests

from .models import Alert, RelatedAsset

LOG = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
RETRY_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "Unknown"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")


def _format_assets(assets: Iterable[RelatedAsset]) -> str:
    lines: list[str] = []
    for asset in assets:
        symbol = asset.symbol or "Unknown"
        name = asset.name or asset.asset_type
        rel = asset.relationship or "related"
        lines.append(f"- {symbol}: {name} ({rel})")
    return "\n".join(lines) if lines else "- No direct asset mapping found"


def format_alert(alert: Alert) -> str:
    return (
        "🚨 Trump Market Alert\n\n"
        "Quote:\n"
        f"“{alert.quote}”\n\n"
        "Source:\n"
        f"{alert.source_name}\n{alert.source_url}\n\n"
        "Time published:\n"
        f"{_format_dt(alert.time_published)}\n\n"
        "Time detected:\n"
        f"{_format_dt(alert.time_detected)}\n\n"
        "Mentioned entity:\n"
        f"{alert.entity_name} ({alert.entity_type})\n\n"
        "Related assets:\n"
        f"{_format_assets(alert.related_assets)}\n\n"
        "Signal:\n"
        f"{alert.signal}\n\n"
        "Confidence:\n"
        f"{alert.confidence}\n\n"
        "Type:\n"
        f"{alert.alert_type}\n\n"
        "Reason:\n"
        f"{alert.reason}\n\n"
        "Warning:\n"
        "Not financial advice. Verify before trading."
    )


def _post_with_retry(url: str, *, data: dict[str, str], timeout: int = 20) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(url, data=data, timeout=timeout)
            if response.status_code in RETRY_STATUS_CODES and attempt < 3:
                time.sleep(attempt * 2)
                continue
            response.raise_for_status()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Telegram send failed after retries: {last_error}")


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        raise ValueError("Telegram token and chat ID are required")

    chunks = [text[i : i + 3900] for i in range(0, len(text), 3900)] or [text]
    for chunk in chunks:
        _post_with_retry(
            TELEGRAM_API.format(token=token),
            data={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": "false"},
        )


def send_alert(token: str, chat_id: str, alert: Alert) -> None:
    send_telegram_message(token, chat_id, format_alert(alert))


def send_discord_message(webhook_url: str, text: str) -> None:
    response = requests.post(webhook_url, json={"content": text[:1900]}, timeout=20)
    response.raise_for_status()
