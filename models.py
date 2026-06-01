from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from trump_market_alert.models import SourceItem
from trump_market_alert.utils import clean_text, now_utc, stable_hash
from .base import BaseSource

LOG = logging.getLogger(__name__)


class LiveAudioSource(BaseSource):
    """Experimental free live-audio sampler.

    It uses yt-dlp to resolve a public live stream, ffmpeg to capture a short current audio clip,
    and faster-whisper to transcribe it locally on the GitHub runner.

    This is not enabled by default because it is slow and can miss audio between scheduled runs.
    """

    name = "live_audio"

    def __init__(self, sources: list[dict[str, Any]], seconds: int = 90, model_size: str = "tiny.en"):
        self.sources = sources
        self.seconds = max(15, min(int(seconds), 600))
        self.model_size = model_size

    def fetch(self) -> list[SourceItem]:
        if not _tool_exists("yt-dlp"):
            LOG.warning("Live audio skipped: yt-dlp command not available.")
            return []
        if not _tool_exists("ffmpeg"):
            LOG.warning("Live audio skipped: ffmpeg command not available.")
            return []
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:
            LOG.warning("Live audio skipped: faster-whisper is not installed: %s", exc)
            return []

        model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        items: list[SourceItem] = []
        for src in self.sources:
            if not src.get("enabled", True):
                continue
            name = str(src.get("name") or "Live audio")
            page_url = str(src.get("url") or "")
            if not page_url:
                continue
            try:
                media_url = _resolve_audio_url(page_url)
                if not media_url:
                    continue
                wav = _capture_audio(media_url, self.seconds)
                segments, info = model.transcribe(str(wav), language="en", vad_filter=True)
                text = clean_text(" ".join(seg.text for seg in segments))
                if not text:
                    continue
                sid = stable_hash(page_url, text, now_utc().strftime("%Y-%m-%dT%H:%M"), n=32)
                items.append(
                    SourceItem(
                        source=f"live_audio:{name}",
                        source_id=sid,
                        platform=f"Live audio - {name}",
                        author=name,
                        text=text,
                        url=page_url,
                        published_at=now_utc(),
                        source_type="live_audio",
                        raw={"seconds": self.seconds, "model": self.model_size},
                    )
                )
            except Exception as exc:
                LOG.exception("Live audio source failed for %s: %s", name, exc)
        return items


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def _resolve_audio_url(page_url: str) -> str | None:
    cmd = ["yt-dlp", "-g", "-f", "bestaudio/best", "--no-playlist", page_url]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if res.returncode != 0:
        LOG.warning("yt-dlp failed for %s: %s", page_url, res.stderr[-500:])
        return None
    lines = [x.strip() for x in res.stdout.splitlines() if x.strip().startswith("http")]
    return lines[-1] if lines else None


def _capture_audio(media_url: str, seconds: int) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="tma_live_audio_"))
    out = tmpdir / "clip.wav"
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-t",
        str(seconds),
        "-i",
        media_url,
        "-ac",
        "1",
        "-ar",
        "16000",
        str(out),
    ]
    subprocess.run(cmd, check=True, timeout=seconds + 90)
    return out
