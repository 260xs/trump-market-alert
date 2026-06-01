from __future__ import annotations

from trump_market_alert.config import Settings
from trump_market_alert.notifiers import Notifier
from trump_market_alert.utils import setup_logging


def main() -> int:
    s = Settings.load()
    setup_logging(s.log_level)
    if not s.telegram_bot_token or not s.telegram_chat_id:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first.")

    ok = Notifier(s).send_text(
        "Test notification from Trump Market Alert. If you see this on iPhone, Telegram is ready."
    )
    print("sent" if ok else "failed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
