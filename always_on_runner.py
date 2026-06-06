from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from alerts.telegram import TelegramClient
from config import load_settings, load_watchlist
from database.db import Database
from main import setup_logging
from scheduler import Scheduler
from stocks.scanner import discover_candidates, hourly_scan, load_stock_config
from stocks.research_db import StockResearchDB


@dataclass
class JobState:
    name: str
    interval_seconds: int
    next_run_monotonic: float
    running: bool = False


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        return max(1, int(value))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


class AlwaysOnRunner:
    def __init__(self) -> None:
        self.settings = load_settings()
        setup_logging(self.settings.log_level)
        self.log = logging.getLogger(__name__)
        self.stop_event = asyncio.Event()

        self.public_interval = _env_int("RUNNER_PUBLIC_INTERVAL_SECONDS", 300)
        self.stock_interval = _env_int("RUNNER_STOCK_INTERVAL_SECONDS", 3600)
        self.candidate_interval = _env_int("RUNNER_CANDIDATE_INTERVAL_SECONDS", 259200)
        self.run_stock_scan = _env_bool("RUNNER_ENABLE_STOCK_SCAN", True)
        self.run_candidate_refresh = _env_bool("RUNNER_ENABLE_CANDIDATE_REFRESH", True)
        self.sleep_seconds = _env_int("RUNNER_LOOP_SLEEP_SECONDS", 5)

        self.public_db = Database(self.settings.sqlite_path)
        self.public_db.init()
        self.public_db.upsert_watchlist(load_watchlist().get("people", []))
        self.scheduler = Scheduler(self.public_db, self.settings)

        stock_db_path = os.getenv("STOCK_SQLITE_PATH", "data/stocks.sqlite3")
        self.stock_db = StockResearchDB(stock_db_path)
        self.stock_db.init()
        self.stock_cfg = load_stock_config()
        self.telegram = TelegramClient(self.settings.telegram_bot_token, self.settings.telegram_chat_id)

        now = time.monotonic()
        self.jobs: list[tuple[JobState, Callable[[], Awaitable[int]]]] = [
            (JobState("public-figure-scan", self.public_interval, now), self._run_public_scan),
        ]
        if self.run_stock_scan:
            self.jobs.append((JobState("stock-hourly-scan", self.stock_interval, now), self._run_stock_scan))
        if self.run_candidate_refresh:
            self.jobs.append((JobState("stock-candidate-refresh", self.candidate_interval, now), self._run_candidate_refresh))

    def install_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.stop_event.set)
            except NotImplementedError:
                pass

    async def run_forever(self) -> int:
        self.install_signal_handlers()
        self.log.info(
            "Always-on runner started: public_interval=%ss stock_interval=%ss candidate_interval=%ss stock_enabled=%s candidate_enabled=%s",
            self.public_interval,
            self.stock_interval,
            self.candidate_interval,
            self.run_stock_scan,
            self.run_candidate_refresh,
        )

        while not self.stop_event.is_set():
            now = time.monotonic()
            for state, func in self.jobs:
                if state.running or now < state.next_run_monotonic:
                    continue
                await self._run_job(state, func)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.sleep_seconds)
            except asyncio.TimeoutError:
                pass

        self.log.info("Always-on runner stopped")
        return 0

    async def _run_job(self, state: JobState, func: Callable[[], Awaitable[int]]) -> None:
        state.running = True
        started = time.monotonic()
        self.log.info("Starting job: %s", state.name)
        try:
            rc = await func()
            elapsed = time.monotonic() - started
            if rc == 0:
                self.log.info("Job finished: %s rc=%s elapsed=%.1fs", state.name, rc, elapsed)
            else:
                self.log.warning("Job finished with non-zero status: %s rc=%s elapsed=%.1fs", state.name, rc, elapsed)
        except Exception:
            self.log.exception("Job failed: %s", state.name)
        finally:
            state.running = False
            state.next_run_monotonic = started + state.interval_seconds
            if state.next_run_monotonic <= time.monotonic():
                state.next_run_monotonic = time.monotonic() + self.sleep_seconds

    async def _run_public_scan(self) -> int:
        return await self.scheduler.run_once()

    async def _run_stock_scan(self) -> int:
        return await asyncio.to_thread(hourly_scan, self.stock_cfg, self.stock_db, self.telegram)

    async def _run_candidate_refresh(self) -> int:
        return await asyncio.to_thread(discover_candidates, self.stock_cfg, self.stock_db, self.telegram)


def main() -> int:
    return asyncio.run(AlwaysOnRunner().run_forever())


if __name__ == "__main__":
    raise SystemExit(main())
