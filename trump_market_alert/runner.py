from __future__ import annotations

import argparse
import json
import logging
import signal
import time
from datetime import timedelta

from dateutil import parser as date_parser

from .config import Settings, load_yaml
from .db import Database
from .extract import build_alerts
from .mapping import EntityMapper
from .models import Event
from .notifiers import Notifier
from .sources import RssSource, Source, TruthSocialSource, XApiSource, YouTubeSource
from .utils import now_utc, setup_logging

log = logging.getLogger(__name__)


class AlertRunner:
    def __init__(self, settings: Settings):
        self.s = settings
        self.db = Database(settings.database_url, settings.root_dir)
        self.mapper = EntityMapper.from_yaml(settings.entity_config)
        self.notifier = Notifier(settings)
        self.sources = self._build_sources()
        self.stop = False

    def _build_sources(self) -> list[Source]:
        data = load_yaml(self.s.source_config)
        srcs: list[Source] = []

        if self.s.truth_social_enabled:
            items = data.get("truth_social") or [
                {
                    "name": "Truth Social - Donald Trump",
                    "handle": self.s.truth_social_handle,
                    "user_id": self.s.truth_social_user_id,
                }
            ]
            for item in items:
                srcs.append(
                    TruthSocialSource(
                        name=str(item.get("name", "Truth Social")),
                        handle=str(item.get("handle", self.s.truth_social_handle)),
                        user_id=str(item.get("user_id", self.s.truth_social_user_id)),
                        include_reposts=self.s.include_truth_reposts,
                    )
                )

        if self.s.x_enabled:
            if not self.s.x_bearer_token:
                log.warning("X_ENABLED=true but X_BEARER_TOKEN is empty; skipping X")
            else:
                items = data.get("x_accounts") or [
                    {"name": "X - Donald Trump", "username": self.s.x_username, "user_id": self.s.x_user_id}
                ]
                for item in items:
                    srcs.append(
                        XApiSource(
                            name=str(item.get("name", "X")),
                            bearer_token=self.s.x_bearer_token,
                            username=str(item.get("username", self.s.x_username)),
                            user_id=str(item.get("user_id", self.s.x_user_id)),
                        )
                    )

        if self.s.youtube_enabled:
            for item in data.get("youtube_channels", []):
                channel_id = str(item.get("channel_id", "")).strip()
                if not channel_id or channel_id.startswith("REPLACE"):
                    continue
                srcs.append(
                    YouTubeSource(
                        name=str(item.get("name", channel_id)),
                        channel_id=channel_id,
                        check_transcripts=self.s.youtube_check_transcripts,
                        languages=self.s.youtube_transcript_langs,
                    )
                )

        if self.s.rss_enabled:
            for item in data.get("rss_feeds", []):
                url = str(item.get("url", "")).strip()
                if not url:
                    continue
                srcs.append(
                    RssSource(
                        name=str(item.get("name", url)),
                        url=url,
                        fetch_article=bool(item.get("fetch_article", False)) and self.s.fetch_rss_articles,
                    )
                )

        log.info("enabled sources: %s", ", ".join(getattr(x, "name", type(x).__name__) for x in srcs))
        return srcs

    def open(self) -> None:
        self.db.connect()
        if self.s.send_startup_message:
            self.notifier.send_text("Trump Market Alert bot started.")

    def close(self) -> None:
        self.db.close()

    def handle_signal(self, *_args) -> None:
        log.info("stop requested")
        self.stop = True

    def run_forever(self) -> None:
        self.open()
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        try:
            while not self.stop:
                self.run_once()
                if self.s.run_once:
                    break
                self._maybe_heartbeat()
                for _ in range(self.s.poll_seconds):
                    if self.stop:
                        break
                    time.sleep(1)
        finally:
            self.close()

    def _state_recent(self, key: str, min_age: timedelta) -> bool:
        raw = self.db.get_state(key)
        if not raw:
            return False
        try:
            dt = date_parser.parse(raw)
            return now_utc() - dt < min_age
        except Exception:
            return False

    def _maybe_heartbeat(self) -> None:
        if self.s.heartbeat_hours <= 0:
            return
        key = "last_heartbeat"
        if self._state_recent(key, timedelta(hours=self.s.heartbeat_hours)):
            return
        if self.notifier.send_text("Trump Market Alert bot heartbeat: running."):
            self.db.set_state(key, now_utc().isoformat())

    def _maybe_send_error_summary(self, errors: list[dict[str, str]]) -> None:
        if not errors or not self.s.send_error_alerts:
            return
        key = "last_error_alert"
        if self._state_recent(key, timedelta(hours=self.s.error_alert_hours)):
            return
        lines = ["Trump Market Alert warning: one or more sources failed this run.", ""]
        for err in errors[:6]:
            lines.append(f"- {err.get('source', 'unknown')}: {err.get('error', 'error')[:220]}")
        lines.append("")
        lines.append("The bot will keep checking on the next scheduled run.")
        if self.notifier.send_text("\n".join(lines)):
            self.db.set_state(key, now_utc().isoformat())

    def run_once(self) -> None:
        started = now_utc()
        cutoff = started - timedelta(minutes=self.s.alert_lookback_minutes)
        errors: list[dict[str, str]] = []
        sources_checked = 0
        events_seen = 0
        new_items = 0
        alerts_saved = 0

        try:
            for source in self.sources:
                name = getattr(source, "name", type(source).__name__)
                try:
                    events = list(source.fetch(limit=self.s.max_items_per_source))
                    sources_checked += 1
                except Exception as e:
                    log.exception("source failed: %s: %s", name, e)
                    errors.append({"source": str(name), "error": str(e)})
                    continue

                events.sort(key=lambda ev: ev.published_at or ev.detected_at)
                events_seen += len(events)
                log.info("%s returned %d events", name, len(events))

                for ev in events:
                    try:
                        is_new = self.db.add_raw_item(ev)
                        if not is_new:
                            continue
                        new_items += 1
                        if ev.published_at and ev.published_at < cutoff:
                            log.info("skipping old item %s %s", ev.src, ev.item_id)
                            continue
                        alerts_saved += self._process_event(ev)
                    except Exception as e:
                        log.exception("event failed: %s %s: %s", ev.src, ev.item_id, e)
                        errors.append({"source": str(name), "error": f"event {ev.item_id}: {e}"})

            cleaned_raw = self.db.cleanup_old_raw_items(self.s.retention_days)
            cleaned_runs = self.db.cleanup_old_check_runs(self.s.check_run_retention_days)
            if cleaned_raw or cleaned_runs:
                log.info("cleanup removed raw_items=%d check_runs=%d", cleaned_raw, cleaned_runs)

        finally:
            status = "ok" if not errors else "error"
            finished = now_utc()
            self.db.record_check_run(
                started_at=started.isoformat(),
                finished_at=finished.isoformat(),
                status=status,
                sources_checked=sources_checked,
                events_seen=events_seen,
                new_items=new_items,
                alerts_saved=alerts_saved,
                errors=errors,
            )
            log.info(
                "run finished status=%s sources=%d events=%d new_items=%d alerts=%d errors=%d",
                status,
                sources_checked,
                events_seen,
                new_items,
                alerts_saved,
                len(errors),
            )
            self._maybe_send_error_summary(errors)

    def _process_event(self, ev: Event) -> int:
        alerts = build_alerts(
            ev,
            self.mapper,
            self.s.min_quote_chars,
            self.s.allow_article_snippets,
            self.s.trusted_transcript_domains,
        )
        if not alerts:
            return 0
        saved = 0
        for alert in alerts:
            if self.db.alert_exists(alert.dedupe_key):
                continue
            sent_ok = self.notifier.send_alert(alert)
            if self.db.save_alert(alert, sent_ok=sent_ok):
                saved += 1
            log.info(
                "alert %s sent_ok=%s signal=%s confidence=%s",
                alert.dedupe_key[:10],
                sent_ok,
                alert.signal,
                alert.confidence,
            )
        return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trump Market Alert monitor")
    parser.add_argument("--once", action="store_true", help="Run one polling cycle and exit")
    parser.add_argument("--test-sample", action="store_true", help="Process a built-in sample alert")
    parser.add_argument("--status", action="store_true", help="Print database status and exit")
    args = parser.parse_args(argv)

    settings = Settings.load()
    if args.once:
        settings.run_once = True
    setup_logging(settings.log_level)

    runner = AlertRunner(settings)
    if args.status:
        runner.open()
        try:
            print(json.dumps(runner.db.stats(), indent=2, sort_keys=True))
        finally:
            runner.close()
        return 0

    if args.test_sample:
        runner.open()
        try:
            ev = Event(
                src="sample",
                platform="Sample",
                item_id=f"sample-{int(time.time())}",
                text="Dell is doing a great job.",
                url="https://example.com/sample",
                published_at=now_utc(),
                kind="sample",
            )
            runner._process_event(ev)
        finally:
            runner.close()
        return 0

    runner.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
