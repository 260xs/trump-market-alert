from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode

import requests

from trump_market_alert.models import SourceItem
from trump_market_alert.utils import clean_text, parse_dt, stable_hash
from .base import BaseSource

LOG = logging.getLogger(__name__)


class XAPISource(BaseSource):
    """Official X API source. This intentionally does not scrape logged-in pages."""

    name = "x_api"

    def __init__(self, queries: list[str], bearer_token: str | None = None, timeout: int = 25):
        self.queries = queries
        self.bearer_token = bearer_token or os.getenv("X_BEARER_TOKEN", "")
        self.timeout = timeout

    def fetch(self) -> list[SourceItem]:
        if not self.bearer_token:
            LOG.info("X API skipped: X_BEARER_TOKEN is not configured.")
            return []
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        out: list[SourceItem] = []
        for query in self.queries:
            params = {
                "query": query,
                "max_results": "20",
                "tweet.fields": "created_at,author_id,lang,entities,context_annotations",
                "expansions": "author_id",
                "user.fields": "username,name",
            }
            url = "https://api.x.com/2/tweets/search/recent?" + urlencode(params)
            try:
                r = requests.get(url, headers=headers, timeout=self.timeout)
                if r.status_code == 429:
                    LOG.warning("X API rate limited for query: %s", query)
                    continue
                r.raise_for_status()
                data = r.json()
                users = {u.get("id"): u for u in data.get("includes", {}).get("users", [])}
                for tw in data.get("data", []) or []:
                    txt = clean_text(tw.get("text") or "")
                    if not txt:
                        continue
                    user = users.get(tw.get("author_id"), {})
                    username = user.get("username") or tw.get("author_id") or "unknown"
                    link = f"https://x.com/{username}/status/{tw.get('id')}" if tw.get("id") else "https://x.com"
                    out.append(
                        SourceItem(
                            source="x_api:recent_search",
                            source_id=str(tw.get("id") or stable_hash(query, txt)),
                            platform="X API",
                            author=str(user.get("name") or username),
                            text=txt,
                            url=link,
                            published_at=parse_dt(tw.get("created_at")),
                            source_type="text",
                            raw=tw,
                        )
                    )
            except Exception as exc:
                LOG.exception("X API query failed: %s", exc)
        return out
