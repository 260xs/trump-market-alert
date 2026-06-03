from __future__ import annotations

from typing import Any

from config import Settings
from database.models import SourceConfig
from sources.base import SourceMonitor
from sources.rss_monitor import RssMonitor
from sources.youtube_monitor import YouTubeMonitor
from sources.x_monitor import XMonitor
from sources.live_audio_monitor import LiveAudioMonitor
from sources.truthsocial_monitor import TruthSocialMonitor


def source_from_dict(person: dict[str, Any], src: dict[str, Any]) -> SourceConfig:
    return SourceConfig(
        id=src["id"],
        person_id=person["id"],
        platform=src.get("platform", "unknown"),
        source_type=src.get("source_type", "unknown"),
        url=src.get("url", ""),
        priority=src.get("priority", "medium"),
        enabled=bool(src.get("enabled", True)),
        polling_interval_seconds=int(src.get("polling_interval_seconds", 600)),
        source_confidence=float(src.get("source_confidence", 0.80)),
        speaker_confidence=float(src.get("speaker_confidence", 0.95)),
        channel_id=src.get("channel_id", ""),
        expected_speaker=src.get("expected_speaker", person.get("full_name", "")),
        extra={**src, "person_name": person.get("full_name", person["id"])},
    )


def build_monitors(watchlist: dict[str, Any], settings: Settings) -> list[SourceMonitor]:
    monitors: list[SourceMonitor] = []
    for person in watchlist.get("people", []):
        if not person.get("enabled", True):
            continue
        if not person.get("allow_telegram_alerts", True):
            continue
        for src in person.get("sources", []):
            source = source_from_dict(person, src)
            if not source.enabled:
                continue
            if source.source_type == "rss":
                monitors.append(RssMonitor(source))
            elif source.source_type == "youtube_rss":
                monitors.append(YouTubeMonitor(source))
            elif source.source_type == "x_api":
                monitors.append(XMonitor(source, settings.x_bearer_token))
            elif source.source_type == "truthsocial":
                monitors.append(TruthSocialMonitor(source))
            elif source.source_type == "live_audio" and settings.enable_live_audio:
                monitors.append(LiveAudioMonitor(source, settings.live_sample_seconds))
    return monitors
