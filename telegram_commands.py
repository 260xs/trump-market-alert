from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from alerts.telegram import TelegramClient

log = logging.getLogger(__name__)

AsyncTextCallback = Callable[[], Awaitable[str]]
TextCallback = Callable[[], str]


MENU_TEXT = """Telegram control menu

/status - runner, last runs, and pause state
/last_alert - latest public or stock alert
/last_public - latest public-figure alert
/last_stock - latest stock setup alert
/run_public_now - run the public scanner once
/run_stock_now - run the stock scanner once
/pause - pause scheduled runner jobs
/resume - resume scheduled runner jobs
/menu - show this menu

Cannot do:
- trade or connect to a broker
- loosen alert rules from Telegram
- show or change secrets
- bypass public-source rules
- guarantee free data/API uptime
"""


@dataclass
class CommandContext:
    public_db_path: Path
    stock_db_path: Path
    status: TextCallback
    run_public_now: AsyncTextCallback
    run_stock_now: AsyncTextCallback
    pause: TextCallback
    resume: TextCallback


class TelegramCommandCenter:
    def __init__(self, token: str, chat_id: str, context: CommandContext, poll_timeout: int = 25):
        self.token = token
        self.chat_id = str(chat_id)
        self.context = context
        self.poll_timeout = poll_timeout
        self.offset = 0
        self.telegram = TelegramClient(token, chat_id)

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        if not self.enabled:
            log.info("Telegram command center disabled because Telegram is not configured")
            return
        log.info("Telegram command center started")
        while not stop_event.is_set():
            try:
                updates = await asyncio.to_thread(self._get_updates)
                for update in updates:
                    self.offset = max(self.offset, int(update.get("update_id", 0)) + 1)
                    await self._handle_update(update)
            except Exception as exc:
                log.warning("Telegram command polling failed: %s", exc)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=10)
                except asyncio.TimeoutError:
                    pass
        log.info("Telegram command center stopped")

    def _get_updates(self) -> list[dict[str, Any]]:
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        response = requests.get(
            url,
            params={
                "offset": self.offset,
                "timeout": self.poll_timeout,
                "allowed_updates": json.dumps(["message"]),
            },
            timeout=self.poll_timeout + 10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram getUpdates failed: {data}")
        result = data.get("result") or []
        return result if isinstance(result, list) else []

    async def _handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat = message.get("chat") or {}
        incoming_chat_id = str(chat.get("id", ""))
        if incoming_chat_id != self.chat_id:
            log.warning("Ignoring Telegram command from unauthorized chat_id=%s", incoming_chat_id)
            return
        text = str(message.get("text") or "").strip()
        if not text.startswith("/"):
            return
        response = await self.dispatch(text.split()[0].split("@", 1)[0].lower())
        if response:
            await asyncio.to_thread(self.telegram.send_text, response[:3900])

    async def dispatch(self, command: str) -> str:
        if command in {"/menu", "/help", "/start"}:
            return MENU_TEXT
        if command == "/status":
            return self.context.status()
        if command == "/last_alert":
            return self._last_alert()
        if command == "/last_public":
            return self._last_public_alert()
        if command == "/last_stock":
            return self._last_stock_alert()
        if command == "/run_public_now":
            return await self.context.run_public_now()
        if command == "/run_stock_now":
            return await self.context.run_stock_now()
        if command == "/pause":
            return self.context.pause()
        if command == "/resume":
            return self.context.resume()
        return "Unknown command. Send /menu to see what I can do."

    def _last_alert(self) -> str:
        public = self._last_public_alert()
        stock = self._last_stock_alert()
        if "No public" in public and "No stock" in stock:
            return "No alerts recorded yet."
        return f"{public}\n\n{stock}"

    def _last_public_alert(self) -> str:
        if not self.context.public_db_path.exists():
            return "No public alert database found yet."
        query = """
            SELECT speaker_name, ticker, asset, signal, confidence, lane, sent_at, reason
            FROM alerts
            WHERE telegram_sent=1
            ORDER BY sent_at DESC
            LIMIT 1
        """
        row = self._fetch_one(self.context.public_db_path, query)
        if not row:
            return "No public-figure alerts recorded yet."
        return (
            "Last public alert\n"
            f"Speaker: {row['speaker_name']}\n"
            f"Asset: {row['asset']} ({row['ticker']})\n"
            f"Signal: {row['signal']}\n"
            f"Confidence: {row['confidence']}\n"
            f"Lane: {row['lane']}\n"
            f"Sent: {row['sent_at']}\n"
            f"Reason: {row['reason']}"
        )

    def _last_stock_alert(self) -> str:
        if not self.context.stock_db_path.exists():
            return "No stock alert database found yet."
        query = """
            SELECT ticker, signal, setup_key, payload_json, sent_at
            FROM stock_alerts
            ORDER BY sent_at DESC
            LIMIT 1
        """
        row = self._fetch_one(self.context.stock_db_path, query)
        if not row:
            return "No stock alerts recorded yet."
        payload = self._json(row["payload_json"])
        return (
            "Last stock alert\n"
            f"Ticker: {row['ticker']}\n"
            f"Signal: {row['signal']}\n"
            f"Model view: {payload.get('model_view', 'n/a')}\n"
            f"Confidence: {payload.get('confidence', 'n/a')}\n"
            f"Trigger: {payload.get('trigger_level', 'n/a')}\n"
            f"Invalidation: {payload.get('exit_level', 'n/a')}\n"
            f"Sent: {row['sent_at']}"
        )

    @staticmethod
    def _fetch_one(path: Path, query: str) -> sqlite3.Row | None:
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        try:
            return con.execute(query).fetchone()
        finally:
            con.close()

    @staticmethod
    def _json(value: str) -> dict[str, Any]:
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
