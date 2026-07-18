from __future__ import annotations

import requests

from alerts.telegram import TelegramClient


def test_telegram_send_errors_redact_token_and_chat_id(monkeypatch):
    attempts = []

    def fake_post(url, data, timeout):
        attempts.append((url, data, timeout))
        raise requests.HTTPError(
            f"400 Client Error for url: {url} chat_id={data['chat_id']}"
        )

    monkeypatch.setattr("alerts.telegram.requests.post", fake_post)
    monkeypatch.setattr("alerts.telegram.time.sleep", lambda _: None)

    client = TelegramClient("123456:SECRET", "-100987654321", timeout=1)

    try:
        client.send_text("hello")
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("Telegram send should fail")

    assert len(attempts) == 3
    assert "123456:SECRET" not in message
    assert "-100987654321" not in message
    assert "[REDACTED_TELEGRAM_BOT_TOKEN]" in message
    assert "[REDACTED_TELEGRAM_CHAT_ID]" in message
