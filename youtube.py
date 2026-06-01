from __future__ import annotations

import logging
from typing import Any

import requests

from trump_market_alert.models import SourceItem
from trump_market_alert.utils import clean_html, parse_dt, stable_hash
from .base import BaseSource

LOG = logging.getLogger(__name__)


class TruthSocialSource(BaseSource):
    name = "truth_social"

    def __init__(self, accounts: list[dict[str, Any]], timeout: int = 25):
        self.accounts = accounts
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 TrumpMarketAlert/2.0 (+public monitoring; no trading)",
                "Accept": "application/json,text/plain,*/*",
            }
        )

    def fetch(self) -> list[SourceItem]:
        items: list[SourceItem] = []
        for acct in self.accounts:
            if not acct.get("enabled", True):
                continue
            name = str(acct.get("name") or "Truth Social")
            url = str(acct.get("api_url") or "")
            if not url:
                continue
            try:
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "error" in data:
                    raise RuntimeError(str(data))
                for status in data[: int(acct.get("limit", 20))]:
                    sid = str(status.get("id") or stable_hash(name, status))
                    text = clean_html(status.get("content") or status.get("text") or "")
                    if not text:
                        continue
                    link = str(status.get("url") or status.get("uri") or acct.get("profile_url") or "")
                    items.append(
                        SourceItem(
                            source=f"truth_social:{name}",
                            source_id=sid,
                            platform="Truth Social",
                            author=name,
                            text=text,
                            url=link,
                            published_at=parse_dt(status.get("created_at")),
                            source_type="truth_social",
                            raw=status,
                        )
                    )
            except Exception as exc:
                LOG.exception("Truth Social fetch failed for %s: %s", name, exc)
        return items
