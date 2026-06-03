from __future__ import annotations

from datetime import datetime, timezone

from config import load_settings
from alerts.telegram import TelegramClient


def main() -> int:
    settings = load_settings()
    tg = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)
    tg.send_text(
        "✅ Market alert Telegram test\n\n"
        "Your bot token and chat ID work.\n"
        "This is not a market alert."
    )
    print("Telegram test sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
