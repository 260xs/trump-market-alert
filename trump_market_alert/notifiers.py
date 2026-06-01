from __future__ import annotations

import html
import logging
import smtplib
import time
from email.message import EmailMessage

import requests

from .config import Settings
from .models import Alert
from .utils import safe_truncate

log = logging.getLogger(__name__)


def fmt_dt(dt) -> str:
    if dt is None:
        return "Unknown"
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def format_alert(alert: Alert, max_quote_chars: int = 1800, html_mode: bool = True) -> str:
    q = safe_truncate(alert.quote, max_quote_chars)
    lines_assets: list[str] = []
    seen: set[str] = set()
    for ent in alert.entities:
        if not ent.assets:
            continue
        for a in ent.assets:
            k = f"{a.symbol}:{a.type}:{a.explanation}"
            if k in seen:
                continue
            seen.add(k)
            lines_assets.append(f"- {a.symbol}/{a.type}: {a.explanation}")
    assets = "\n".join(lines_assets) if lines_assets else "- No direct ticker/asset mapped"
    ents = ", ".join(f"{e.name} ({e.kind})" for e in alert.entities) or "Unknown"

    if html_mode:
        esc = html.escape
        return (
            "🚨 <b>Trump Market Alert</b>\n\n"
            "<b>Quote:</b>\n"
            f"“{esc(q)}”\n\n"
            "<b>Source:</b>\n"
            f"{esc(alert.source_platform)}\n{esc(alert.source_link)}\n\n"
            "<b>Time published:</b>\n"
            f"{esc(fmt_dt(alert.published_at))}\n\n"
            "<b>Time detected:</b>\n"
            f"{esc(fmt_dt(alert.detected_at))}\n\n"
            "<b>Mentioned entity:</b>\n"
            f"{esc(ents)}\n\n"
            "<b>Related assets:</b>\n"
            f"{esc(assets)}\n\n"
            "<b>Signal:</b>\n"
            f"{esc(alert.signal)}\n\n"
            "<b>Confidence:</b>\n"
            f"{esc(alert.confidence)}\n\n"
            "<b>Type:</b>\n"
            f"{esc(alert.alert_type)}\n\n"
            "<b>Warning:</b>\n"
            "Not financial advice. Verify before trading."
        )

    return (
        "🚨 Trump Market Alert\n\n"
        "Quote:\n"
        f"“{q}”\n\n"
        "Source:\n"
        f"{alert.source_platform}\n{alert.source_link}\n\n"
        "Time published:\n"
        f"{fmt_dt(alert.published_at)}\n\n"
        "Time detected:\n"
        f"{fmt_dt(alert.detected_at)}\n\n"
        "Mentioned entity:\n"
        f"{ents}\n\n"
        "Related assets:\n"
        f"{assets}\n\n"
        "Signal:\n"
        f"{alert.signal}\n\n"
        "Confidence:\n"
        f"{alert.confidence}\n\n"
        "Type:\n"
        f"{alert.alert_type}\n\n"
        "Warning:\n"
        "Not financial advice. Verify before trading."
    )


class Notifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_alert(self, alert: Alert) -> bool:
        ok = False
        msg_html = format_alert(alert, self.settings.max_telegram_quote_chars, html_mode=True)
        msg_plain = format_alert(alert, self.settings.max_telegram_quote_chars, html_mode=False)
        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            ok = self.send_telegram(msg_html) or ok
        if self.settings.discord_webhook_url:
            ok = self.send_discord(msg_plain) or ok
        if self.settings.email_enabled:
            ok = self.send_email("Trump Market Alert", msg_plain) or ok
        return ok

    def send_text(self, text: str) -> bool:
        ok = False
        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            ok = self.send_telegram(html.escape(text)) or ok
        if self.settings.discord_webhook_url:
            ok = self.send_discord(text) or ok
        if self.settings.email_enabled:
            ok = self.send_email("Trump Market Alert", text) or ok
        return ok

    def send_telegram(self, message: str) -> bool:
        url = f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        for attempt in range(3):
            try:
                r = requests.post(url, json=payload, timeout=15)
                if r.status_code == 200:
                    return True
                log.warning("Telegram send failed: %s %s", r.status_code, r.text[:300])
            except Exception as e:
                log.warning("Telegram send error: %s", e)
            time.sleep(2 + attempt * 2)
        return False

    def send_discord(self, message: str) -> bool:
        try:
            r = requests.post(self.settings.discord_webhook_url, json={"content": safe_truncate(message, 1900)}, timeout=15)
            if 200 <= r.status_code < 300:
                return True
            log.warning("Discord webhook failed: %s %s", r.status_code, r.text[:300])
        except Exception as e:
            log.warning("Discord webhook error: %s", e)
        return False

    def send_email(self, subject: str, body: str) -> bool:
        s = self.settings
        if not all([s.smtp_host, s.email_from, s.email_to]):
            return False
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = s.email_from
        msg["To"] = s.email_to
        msg.set_content(body)
        try:
            with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as server:
                server.starttls()
                if s.smtp_user:
                    server.login(s.smtp_user, s.smtp_password)
                server.send_message(msg)
            return True
        except Exception as e:
            log.warning("Email send error: %s", e)
            return False
