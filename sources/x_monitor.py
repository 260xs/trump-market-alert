from __future__ import annotations

from datetime import timezone

import requests
from dateutil import parser as date_parser

from database.models import SourceConfig, Statement
from sources.base import SourceMonitor, utc_now


class XMonitor(SourceMonitor):
    """Official X API monitor.

    This intentionally uses the official API only. If X_BEARER_TOKEN is empty,
    the monitor returns no statements instead of scraping or bypassing access controls.
    """

    def __init__(self, source: SourceConfig, bearer_token: str):
        super().__init__(source)
        self.bearer_token = bearer_token

    def fetch(self) -> list[Statement]:
        if not self.bearer_token:
            return []
        query = self.source.extra.get("query")
        if not query:
            username = self.source.extra.get("username")
            if not username:
                return []
            query = f"from:{username} -is:retweet"
        url = "https://api.twitter.com/2/tweets/search/recent"
        params = {
            "query": query,
            "max_results": str(int(self.source.extra.get("max_results", 10))),
            "tweet.fields": "created_at,author_id,referenced_tweets,entities",
        }
        headers = {"Authorization": f"Bearer {self.bearer_token}", "User-Agent": "PublicFigureMarketAlert/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code in {401, 403, 429}:
            return []
        resp.raise_for_status()
        data = resp.json().get("data", [])
        out: list[Statement] = []
        for item in data[:20]:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            created_at = item.get("created_at")
            published = utc_now()
            if created_at:
                try:
                    dt = date_parser.parse(created_at)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    published = dt.astimezone(timezone.utc)
                except Exception:
                    pass
            tweet_id = str(item.get("id", ""))
            username = self.source.extra.get("username", "")
            link = f"https://x.com/{username}/status/{tweet_id}" if username and tweet_id else self.source.url
            out.append(
                Statement(
                    person_id=self.source.person_id,
                    source_id=self.source.id,
                    speaker_name=self.source.extra.get("person_name", self.source.person_id),
                    statement_text=text,
                    source_url=link,
                    platform=self.source.platform,
                    published_at=published,
                    detected_at=utc_now(),
                    source_confidence=self.source.source_confidence,
                    speaker_confidence=self.source.speaker_confidence,
                    quote_confidence=0.98,
                    source_type=self.source.source_type,
                    platform_item_id=tweet_id,
                    raw_metadata={"x_api": True},
                )
            )
        return out
