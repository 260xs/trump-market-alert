from __future__ import annotations

import requests

from database.models import SourceConfig, Statement
from sources.base import SourceMonitor, utc_now


class XMonitor(SourceMonitor):
    def __init__(self, source: SourceConfig, bearer_token: str):
        super().__init__(source)
        self.bearer_token = bearer_token

    def fetch(self) -> list[Statement]:
        if not self.bearer_token:
            return []
        username = self.source.extra.get("username")
        if not username:
            return []
        # Minimal official API placeholder. Enable only after adding user-id lookup or recent search config.
        return []
