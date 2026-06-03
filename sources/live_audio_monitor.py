from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from database.models import SourceConfig, Statement
from sources.base import SourceMonitor, utc_now


def _fmt_offset(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class LiveAudioMonitor(SourceMonitor):
    def __init__(self, source: SourceConfig, sample_seconds: int = 90):
        super().__init__(source)
        self.sample_seconds = max(20, min(sample_seconds, 300))

    def fetch(self) -> list[Statement]:
        if not shutil.which("yt-dlp") or not shutil.which("ffmpeg"):
            return []
        try:
            info = self._video_info()
            stream_url = self._stream_url()
            if not stream_url:
                return []
            with tempfile.TemporaryDirectory() as td:
                audio = Path(td) / "sample.wav"
                self._record_audio(stream_url, audio)
                segments = self._transcribe(audio)
            return self._segments_to_statements(info, segments)
        except Exception as exc:
            # Source-level errors are handled by scheduler. Return no statements for unsupported streams.
            raise RuntimeError(f"live audio monitor failed for {self.source.id}: {exc}") from exc

    def _video_info(self) -> dict:
        cmd = ["yt-dlp", "--dump-single-json", "--no-warnings", self.source.url]
        raw = subprocess.check_output(cmd, text=True, timeout=45)
        return json.loads(raw)

    def _stream_url(self) -> str:
        cmd = ["yt-dlp", "-g", "-f", "ba/b", "--no-warnings", self.source.url]
        raw = subprocess.check_output(cmd, text=True, timeout=45).strip().splitlines()
        return raw[0] if raw else ""

    def _record_audio(self, stream_url: str, audio_path: Path) -> None:
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", stream_url,
            "-t", str(self.sample_seconds),
            "-ac", "1", "-ar", "16000",
            str(audio_path),
        ]
        subprocess.run(cmd, check=True, timeout=self.sample_seconds + 60)

    def _transcribe(self, audio_path: Path) -> list[dict]:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except Exception as exc:
            raise RuntimeError("faster-whisper is not installed. Install requirements-live.txt") from exc
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(audio_path), beam_size=1, vad_filter=True)
        out = []
        for seg in segments:
            text = (getattr(seg, "text", "") or "").strip()
            if text:
                out.append({"start": float(seg.start), "end": float(seg.end), "text": text})
        return out

    def _segments_to_statements(self, info: dict, segments: list[dict]) -> list[Statement]:
        out: list[Statement] = []
        now = utc_now()
        webpage_url = info.get("webpage_url") or self.source.url
        video_id = info.get("id", "")
        live_start_ts = info.get("release_timestamp") or info.get("timestamp")
        base_offset = None
        if live_start_ts:
            try:
                base_offset = int(now.timestamp()) - int(live_start_ts)
            except Exception:
                base_offset = None
        for idx, seg in enumerate(segments):
            segment_offset = int(seg.get("start", 0))
            live_offset = base_offset + segment_offset if base_offset is not None else segment_offset
            ts = _fmt_offset(live_offset)
            source_link = webpage_url
            if video_id and live_offset is not None:
                source_link = f"https://www.youtube.com/watch?v={video_id}&t={max(0, live_offset)}s"
            out.append(
                Statement(
                    person_id=self.source.person_id,
                    source_id=self.source.id,
                    speaker_name=self.source.expected_speaker or self.source.extra.get("person_name", self.source.person_id),
                    statement_text=seg["text"],
                    source_url=source_link,
                    platform=self.source.platform,
                    published_at=now,
                    detected_at=now,
                    source_confidence=self.source.source_confidence,
                    speaker_confidence=self.source.speaker_confidence,
                    quote_confidence=0.68,
                    source_type="live_audio",
                    platform_item_id=f"{video_id}:{live_offset}:{idx}",
                    transcript_timestamp=ts,
                    live_offset_seconds=live_offset,
                    is_live=True,
                    raw_metadata={"live_title": info.get("title", ""), "segment_start": seg.get("start"), "segment_end": seg.get("end")},
                )
            )
        return out
