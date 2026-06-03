from __future__ import annotations

import requests


class DiscordClient:
    def __init__(self, webhook_url: str, timeout: int = 20):
        self.webhook_url = webhook_url
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.webhook_url)

    def send_text(self, text: str) -> None:
        if not self.enabled:
            return
        requests.post(self.webhook_url, json={"content": text[:1900]}, timeout=self.timeout).raise_for_status()
