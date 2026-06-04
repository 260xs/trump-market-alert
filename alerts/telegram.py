from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any
import time

import requests

from database.models import Statement, EntityMatch, Signal


def _fmt_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def build_market_alert_text(stmt: Statement, entity: EntityMatch, signal: Signal, lane: str, reason: str) -> str:
    if lane == "live_provisional":
        title = "⚠️ LIVE PROVISIONAL Market Alert"
        conf = "Provisional"
        warning = "Live transcript may be imperfect. Verify the clip/source before acting. Not financial advice."
    else:
        title = "🚨 High-Confidence Market Alert"
        conf = "High"
        warning = "Not financial advice. Verify before acting."

    live_line = ""
    if stmt.is_live:
        live_line = f"\nApprox live minute:\n{escape(stmt.transcript_timestamp or 'Unknown')}\n"

    return (
        f"{title}\n\n"
        f"Speaker:\n{escape(stmt.speaker_name)}\n\n"
        f"Quote:\n“{escape(stmt.statement_text.strip())}”\n\n"
        f"Signal:\n{escape(signal.signal)}\n\n"
        f"Direct mention:\n{escape(entity.mapped_name)}\n\n"
        f"Related ticker/asset:\n{escape(entity.ticker)}\n\n"
        f"Source:\n{escape(stmt.platform)} - {escape(stmt.source_url)}\n"
        f"{live_line}\n"
        f"Time published:\n{_fmt_time(stmt.published_at)}\n\n"
        f"Time detected:\n{_fmt_time(stmt.detected_at)}\n\n"
        f"Confidence:\n{conf}\n"
        f"Source {stmt.source_confidence:.2f} | Speaker {stmt.speaker_confidence:.2f} | Quote {stmt.quote_confidence:.2f} | Entity {entity.entity_confidence:.2f}\n\n"
        f"Why this alert was sent:\n{escape(reason)}\n\n"
        f"Warning:\n{escape(warning)}"
    )


class TelegramClient:
    def __init__(self, token: str, chat_id: str, timeout: int = 20):
        self.token = token
        self.chat_id = chat_id
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def send_text(self, text: str) -> str:
        if not self.enabled:
            raise RuntimeError("Telegram is not configured")
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    url,
                    data={"chat_id": self.chat_id, "text": text[:3900], "disable_web_page_preview": "false"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                if not data.get("ok"):
                    raise RuntimeError(f"Telegram API error: {data}")
                result = data.get("result") or {}
                return str(result.get("message_id", ""))
            except Exception as exc:
                last_error = exc
                if attempt == 3:
                    break
                time.sleep(2 * attempt)
        raise RuntimeError(f"Telegram send failed after retries: {last_error}")

    def send_failure(self, message: str) -> None:
        if not self.enabled:
            return
        try:
            self.send_text("🚨 Market alert workflow failed\n\n" + message[:3500])
        except Exception:
            return
