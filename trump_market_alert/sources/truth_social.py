from __future__ import annotations

import logging
from collections.abc import Iterable

from ..models import Event
from ..utils import clean_html, now_utc, parse_dt
from .base import Source

log = logging.getLogger(__name__)

TRUTH_API = "https://truthsocial.com/api/v1/accounts/{user_id}/statuses"


class TruthSocialSource(Source):
    def __init__(self, name: str, handle: str, user_id: str, include_reposts: bool = False):
        self.name = name
        self.handle = handle
        self.user_id = user_id
        self.include_reposts = include_reposts
        self.headers = {
            "User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome Safari",
            "Accept": "application/json,text/plain,*/*",
        }
        try:
            from curl_cffi import requests as curl_requests

            self.http = curl_requests.Session()
            self.use_curl = True
        except Exception:
            import requests

            self.http = requests.Session()
            self.use_curl = False

    def _get(self, url: str, params: dict):
        if self.use_curl:
            return self.http.get(url, params=params, headers=self.headers, impersonate="chrome", timeout=20)
        return self.http.get(url, params=params, headers=self.headers, timeout=20)

    def fetch(self, limit: int = 20) -> Iterable[Event]:
        url = TRUTH_API.format(user_id=self.user_id)
        params = {
            "exclude_replies": "true",
            "with_muted": "true",
            "limit": str(min(max(limit, 1), 40)),
        }
        try:
            r = self._get(url, params=params)
            if r.status_code != 200:
                log.warning("Truth Social HTTP %s: %s", r.status_code, r.text[:300])
                return []
            data = r.json()
        except Exception as e:
            log.warning("Truth Social fetch error: %s", e)
            return []

        events: list[Event] = []
        for post in data if isinstance(data, list) else []:
            if post.get("reblog") and not self.include_reposts:
                continue
            source_post = post.get("reblog") if post.get("reblog") and self.include_reposts else post
            post_id = str(source_post.get("id") or post.get("id") or "")
            if not post_id:
                continue
            content = clean_html(str(source_post.get("content") or ""))
            if not content:
                continue
            post_url = source_post.get("url") or source_post.get("uri") or f"https://truthsocial.com/@{self.handle}/{post_id}"
            events.append(
                Event(
                    src="truth_social",
                    platform="Truth Social",
                    item_id=post_id,
                    text=content,
                    url=str(post_url),
                    published_at=parse_dt(source_post.get("created_at")),
                    detected_at=now_utc(),
                    kind="truth_social",
                    meta={"handle": self.handle},
                    raw=source_post,
                )
            )
        return events
