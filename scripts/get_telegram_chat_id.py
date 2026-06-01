from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    tok = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not tok:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in .env first.")

    url = f"https://api.telegram.org/bot{tok}/getUpdates"
    r = requests.get(url, timeout=20)
    print(r.text)
    print("\nSend /start to your bot in Telegram first. Then run this again and copy message.chat.id into TELEGRAM_CHAT_ID.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
