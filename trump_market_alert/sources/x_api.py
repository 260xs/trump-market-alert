from __future__ import annotations

import logging
from collections.abc import Iterable

import requests

from ..models import Event
from ..utils import now_utc, parse_dt
from .base import Source

log = logging.getLogger(__name__)


class XApiSource(Source):
    def __init__(self, name: str, bearer_token: str, username: str = "realDonaldTrump", user_id: str = ""):
        self.name = name
        self.bearer_token = bearer_token
        self.username = username
        self.user_id = user_id
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {bearer_token}"})

    def _resolve_user_id(self) -> str:
        if self.user_id:
            return self.user_id
        url = f"https://api.x.com/2/users/by/username/{self.username}"
        r = self.s.get(url, timeout=20)
        if r.status_code != 200:
            log.warning("X user lookup failed: %s %s", r.status_code, r.text[:300])
            return ""
        self.user_id = str((r.json().get("data") or {}).get("id") or "")
        return self.user_id

    def fetch(self, limit: int = 10) -> Iterable[Event]:
        if not self.bearer_token:
            return []
        uid = self._resolve_user_id()
        if not uid:
            return []
        url = f"https://api.x.com/2/users/{uid}/tweets"
        params = {
            "max_results": str(min(max(limit, 5), 100)),
            "tweet.fields": "created_at,edit_history_tweet_ids",
            "exclude": "retweets,replies",
        }
        try:
            r = self.s.get(url, params=params, timeout=20)
            if r.status_code == 429:
                log.warning("X API rate limited: %s", r.text[:200])
                return []
            if r.status_code != 200:
                log.warning("X API fetch failed: %s %s", r.status_code, r.text[:300])
                return []
            data = r.json().get("data") or []
        except Exception as e:
            log.warning("X API error: %s", e)
            return []

        out: list[Event] = []
        for tw in data:
            tid = str(tw.get("id") or "")
            text = str(tw.get("text") or "")
            if not tid or not text:
                continue
            out.append(
                Event(
                    src="x_api",
                    platform="X/Twitter",
                    item_id=tid,
                    text=text,
                    url=f"https://x.com/{self.username}/status/{tid}",
                    published_at=parse_dt(tw.get("created_at")),
                    detected_at=now_utc(),
                    kind="x_post",
                    meta={"username": self.username},
                    raw=tw,
                )
            )
        return out
