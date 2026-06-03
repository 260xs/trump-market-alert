from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Iterable

import requests

from config import Settings, load_watchlist
from database.db import Database
from pipeline import AlertPipeline
from sources.factory import build_monitors

log = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        self.watchlist = load_watchlist()
        self.monitors = build_monitors(self.watchlist, settings)
        self.pipeline = AlertPipeline(db, settings)
        self._locks: dict[str, asyncio.Lock] = {m.source.id: asyncio.Lock() for m in self.monitors}
        self._last_run: dict[str, float] = {}

    async def run_once(self) -> int:
        run_id = self.db.start_scheduler_run()
        sources_checked = 0
        statements_seen = 0
        alerts_sent = 0
        errors = 0
        self._health_start()
        try:
            for monitor in self.monitors:
                try:
                    sent, seen = await self._run_monitor(monitor)
                    sources_checked += 1
                    statements_seen += seen
                    alerts_sent += sent
                    self.db.update_source_success(monitor.source.id)
                except Exception as exc:
                    errors += 1
                    self.db.update_source_error(monitor.source.id, str(exc))
                    log.exception("Source check failed: %s", monitor.source.id)
            status = "success" if errors == 0 else "partial_failure"
            self.db.finish_scheduler_run(run_id, status, sources_checked, statements_seen, alerts_sent, errors)
            self._health_success()
            log.info("Scan complete: sources=%s statements=%s alerts=%s errors=%s", sources_checked, statements_seen, alerts_sent, errors)
            return 0 if errors == 0 else 1
        except Exception as exc:
            self.db.finish_scheduler_run(run_id, "failure", sources_checked, statements_seen, alerts_sent, errors + 1)
            self._health_fail(str(exc))
            raise

    async def run_forever(self) -> None:
        if not self.monitors:
            log.warning("No enabled monitors found.")
        while True:
            tasks = []
            now = time.monotonic()
            for monitor in self.monitors:
                last = self._last_run.get(monitor.source.id, 0)
                interval = monitor.source.polling_interval_seconds
                if now - last >= interval:
                    self._last_run[monitor.source.id] = now
                    tasks.append(asyncio.create_task(self._safe_monitor_loop(monitor)))
            if tasks:
                await asyncio.gather(*tasks)
            await asyncio.sleep(5)

    async def _safe_monitor_loop(self, monitor) -> None:
        try:
            await self._run_monitor(monitor)
            self.db.update_source_success(monitor.source.id)
        except Exception as exc:
            self.db.update_source_error(monitor.source.id, str(exc))
            log.exception("Scheduled source failed: %s", monitor.source.id)

    async def _run_monitor(self, monitor) -> tuple[int, int]:
        lock = self._locks[monitor.source.id]
        if lock.locked():
            log.info("Skipping overlapping source run: %s", monitor.source.id)
            return 0, 0
        async with lock:
            log.info("Checking source %s (%s)", monitor.source.id, monitor.source.source_type)
            statements = await asyncio.to_thread(monitor.fetch)
            sent = 0
            for stmt in statements:
                sent += self.pipeline.process_statement(stmt)
            return sent, len(statements)

    def _ping(self, suffix: str = "") -> None:
        if not self.settings.healthchecks_url:
            return
        url = self.settings.healthchecks_url.rstrip("/") + suffix
        try:
            requests.get(url, timeout=10)
        except Exception:
            log.warning("Healthchecks ping failed: %s", url)

    def _health_start(self) -> None:
        self._ping("/start")

    def _health_success(self) -> None:
        self._ping("")

    def _health_fail(self, reason: str) -> None:
        if not self.settings.healthchecks_url:
            return
        url = self.settings.healthchecks_url.rstrip("/") + "/fail"
        try:
            requests.post(url, data=reason[:10000].encode("utf-8"), timeout=10)
        except Exception:
            log.warning("Healthchecks failure ping failed")
