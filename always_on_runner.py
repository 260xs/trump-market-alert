from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timezone
from pathlib import Path
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from alerts.telegram import TelegramClient
from config import load_settings, load_watchlist
from database.db import Database
from main import setup_logging
from scheduler import Scheduler
from stocks.scanner import discover_candidates, hourly_scan, load_stock_config
from stocks.research_db import StockResearchDB
from telegram_commands import CommandContext, TelegramCommandCenter


@dataclass
class JobState:
    name: str
    interval_seconds: int
    next_run_monotonic: float
    healthcheck_url: str = ""
    running: bool = False
    last_rc: int | None = None
    last_error: str = ""
    last_started_at: str = ""
    last_finished_at: str = ""


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


def _env_time(name: str, default: str) -> dt_time:
    value = os.getenv(name, default).strip() or default
    try:
        hour, minute = value.split(":", 1)
        return dt_time(hour=int(hour), minute=int(minute))
    except Exception:
        fallback_hour, fallback_minute = default.split(":", 1)
        return dt_time(hour=int(fallback_hour), minute=int(fallback_minute))


def _env_weekdays(name: str, default: str) -> set[int]:
    raw = os.getenv(name, default).strip() or default
    days: set[int] = set()
    for item in raw.split(","):
        try:
            day = int(item.strip())
        except ValueError:
            continue
        if 0 <= day <= 6:
            days.add(day)
    return days or {0, 1, 2, 3, 4}


def _env_zoneinfo(name: str, default: str) -> ZoneInfo:
    value = os.getenv(name, default).strip() or default
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError:
        return ZoneInfo(default)


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class AlwaysOnRunner:
    def __init__(self) -> None:
        self.settings = load_settings()
        setup_logging(self.settings.log_level)
        self.log = logging.getLogger(__name__)
        self.stop_event = asyncio.Event()
        self.active_tasks: set[asyncio.Task[None]] = set()
        self.scheduled_paused = False

        self.free_tier_mode = _env_bool("RUNNER_FREE_TIER_MODE", True)
        self.public_interval = _env_int("RUNNER_PUBLIC_INTERVAL_SECONDS", 300)
        self.stock_interval = _env_int("RUNNER_STOCK_INTERVAL_SECONDS", 3600)
        self.candidate_interval = _env_int("RUNNER_CANDIDATE_INTERVAL_SECONDS", 604800)
        self.run_stock_scan = _env_bool("RUNNER_ENABLE_STOCK_SCAN", True)
        self.run_candidate_refresh = _env_bool("RUNNER_ENABLE_CANDIDATE_REFRESH", True)
        self.enable_telegram_commands = _env_bool("RUNNER_ENABLE_TELEGRAM_COMMANDS", True)
        self.sleep_seconds = _env_int("RUNNER_LOOP_SLEEP_SECONDS", 5)
        self.stock_market_hours_only = _env_bool("RUNNER_STOCK_MARKET_HOURS_ONLY", True)
        self.stock_market_tz = _env_zoneinfo("RUNNER_STOCK_MARKET_TIMEZONE", "America/New_York")
        self.stock_market_open = _env_time("RUNNER_STOCK_MARKET_OPEN", "09:30")
        self.stock_market_close = _env_time("RUNNER_STOCK_MARKET_CLOSE", "16:15")
        self.stock_market_days = _env_weekdays("RUNNER_STOCK_MARKET_DAYS", "0,1,2,3,4")
        self.runner_healthcheck_url = os.getenv("RUNNER_HEALTHCHECKS_URL", "").strip()
        self.stock_healthcheck_url = os.getenv("STOCK_HEALTHCHECKS_URL", "").strip()
        self.candidate_healthcheck_url = os.getenv("CANDIDATE_HEALTHCHECKS_URL", "").strip()

        self.public_db = Database(self.settings.sqlite_path)
        self.public_db.init()
        self.public_db.upsert_watchlist(load_watchlist().get("people", []))
        self.scheduler = Scheduler(self.public_db, self.settings)

        stock_db_path = os.getenv("STOCK_SQLITE_PATH", "data/stocks.sqlite3")
        self.stock_db_path = Path(stock_db_path)
        self.stock_db: StockResearchDB | None = None
        self.stock_cfg = None
        if self.run_stock_scan or self.run_candidate_refresh:
            self.stock_db = StockResearchDB(self.stock_db_path)
            self.stock_db.init()
            self.stock_cfg = load_stock_config()
        self.telegram = TelegramClient(self.settings.telegram_bot_token, self.settings.telegram_chat_id)

        now = time.monotonic()
        self.jobs: list[tuple[JobState, Callable[[], Awaitable[int]]]] = [
            (
                JobState("public-figure-scan", self.public_interval, now, self.runner_healthcheck_url),
                self._run_public_scan,
            ),
        ]
        if self.run_stock_scan:
            self.jobs.append(
                (
                    JobState("stock-hourly-scan", self.stock_interval, now, self.stock_healthcheck_url),
                    self._run_stock_scan,
                )
            )
        if self.run_candidate_refresh:
            self.jobs.append(
                (
                    JobState("stock-candidate-refresh", self.candidate_interval, now, self.candidate_healthcheck_url),
                    self._run_candidate_refresh,
                )
            )
        self.command_center = self._build_command_center()

    def _build_command_center(self) -> TelegramCommandCenter | None:
        if not self.enable_telegram_commands:
            return None
        context = CommandContext(
            public_db_path=self.settings.sqlite_path,
            stock_db_path=self.stock_db_path,
            status=self._command_status,
            run_public_now=self._command_run_public_now,
            run_stock_now=self._command_run_stock_now,
            pause=self._command_pause,
            resume=self._command_resume,
        )
        return TelegramCommandCenter(self.settings.telegram_bot_token, self.settings.telegram_chat_id, context)

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
            "Always-on runner started: free_tier_mode=%s public_interval=%ss stock_interval=%ss candidate_interval=%ss stock_enabled=%s candidate_enabled=%s stock_market_hours_only=%s telegram_commands=%s",
            self.free_tier_mode,
            self.public_interval,
            self.stock_interval,
            self.candidate_interval,
            self.run_stock_scan,
            self.run_candidate_refresh,
            self.stock_market_hours_only,
            bool(self.command_center),
        )

        command_task: asyncio.Task[None] | None = None
        if self.command_center:
            command_task = asyncio.create_task(self.command_center.run_forever(self.stop_event))

        while not self.stop_event.is_set():
            self.active_tasks = {task for task in self.active_tasks if not task.done()}
            if not self.scheduled_paused:
                now = time.monotonic()
                for state, func in self.jobs:
                    if state.running or now < state.next_run_monotonic:
                        continue
                    task = asyncio.create_task(self._run_job(state, func))
                    self.active_tasks.add(task)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.sleep_seconds)
            except asyncio.TimeoutError:
                pass

        if command_task:
            await asyncio.gather(command_task, return_exceptions=True)
        if self.active_tasks:
            self.log.info("Waiting for %s active job(s) to finish before stopping", len(self.active_tasks))
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        self.log.info("Always-on runner stopped")
        return 0

    async def _run_job(self, state: JobState, func: Callable[[], Awaitable[int]]) -> None:
        state.running = True
        state.last_started_at = _utc_stamp()
        started = time.monotonic()
        state.last_error = ""
        self._health_start(state)
        self.log.info("Starting job: %s", state.name)
        try:
            rc = await func()
            state.last_rc = rc
            elapsed = time.monotonic() - started
            if rc == 0:
                self.log.info("Job finished: %s rc=%s elapsed=%.1fs", state.name, rc, elapsed)
                self._health_success(state)
            else:
                state.last_error = f"non-zero status {rc}"
                self.log.warning("Job finished with non-zero status: %s rc=%s elapsed=%.1fs", state.name, rc, elapsed)
                self._health_fail(state, state.last_error)
        except Exception as exc:
            state.last_rc = 1
            state.last_error = str(exc)
            self.log.exception("Job failed: %s", state.name)
            self._health_fail(state, state.last_error)
        finally:
            state.last_finished_at = _utc_stamp()
            state.running = False
            state.next_run_monotonic = started + state.interval_seconds
            if state.next_run_monotonic <= time.monotonic():
                state.next_run_monotonic = time.monotonic() + self.sleep_seconds

    def _ping(self, url: str, suffix: str = "", body: str = "") -> None:
        if not url:
            return
        target = url.rstrip("/") + suffix
        try:
            if body:
                requests.post(target, data=body[:10000].encode("utf-8"), timeout=10)
            else:
                requests.get(target, timeout=10)
        except Exception:
            self.log.warning("Healthcheck ping failed")

    def _health_start(self, state: JobState) -> None:
        self._ping(state.healthcheck_url, "/start")

    def _health_success(self, state: JobState) -> None:
        self._ping(state.healthcheck_url)

    def _health_fail(self, state: JobState, reason: str) -> None:
        self._ping(state.healthcheck_url, "/fail", f"{state.name}: {reason}")

    async def _run_public_scan(self) -> int:
        return await self.scheduler.run_once()

    async def _run_stock_scan(self) -> int:
        if self.stock_market_hours_only and not self._within_stock_market_window():
            self.log.info("Skipping stock scan outside configured stock market window")
            return 0
        if self.stock_cfg is None or self.stock_db is None:
            self.log.warning("Stock scan requested but stock scanner is not initialized")
            return 1
        return await asyncio.to_thread(hourly_scan, self.stock_cfg, self.stock_db, self.telegram)

    async def _run_candidate_refresh(self) -> int:
        if self.stock_cfg is None or self.stock_db is None:
            self.log.warning("Candidate refresh requested but stock scanner is not initialized")
            return 1
        return await asyncio.to_thread(discover_candidates, self.stock_cfg, self.stock_db, self.telegram)

    def _within_stock_market_window(self, now: datetime | None = None) -> bool:
        local_now = now.astimezone(self.stock_market_tz) if now else datetime.now(self.stock_market_tz)
        if local_now.weekday() not in self.stock_market_days:
            return False
        current = local_now.time().replace(second=0, microsecond=0)
        return self.stock_market_open <= current <= self.stock_market_close

    def _state_for(self, name: str) -> tuple[JobState, Callable[[], Awaitable[int]]] | None:
        for state, func in self.jobs:
            if state.name == name:
                return state, func
        return None

    async def _run_named_now(self, name: str) -> str:
        found = self._state_for(name)
        if not found:
            return f"{name} is disabled."
        state, func = found
        if state.running:
            return f"{name} is already running."
        await self._run_job(state, func)
        status = "OK" if state.last_rc == 0 else f"failed rc={state.last_rc}"
        if state.last_error:
            status += f" error={state.last_error[:300]}"
        return f"Manual {name} finished: {status}"

    def _command_status(self) -> str:
        lines = [
            "Market alert status",
            f"Scheduled jobs: {'paused' if self.scheduled_paused else 'running'}",
            f"Free-tier mode: {'enabled' if self.free_tier_mode else 'disabled'}",
            f"Stock market-hours only: {'enabled' if self.stock_market_hours_only else 'disabled'}",
            f"Telegram commands: {'enabled' if self.command_center else 'disabled'}",
        ]
        now = time.monotonic()
        for state, _ in self.jobs:
            if state.running:
                next_text = "running now"
            else:
                seconds = max(0, int(state.next_run_monotonic - now))
                next_text = f"next in {seconds}s"
            rc = "never" if state.last_rc is None else str(state.last_rc)
            lines.append(
                f"{state.name}: {next_text}, last rc={rc}, started={state.last_started_at or 'never'}, finished={state.last_finished_at or 'never'}"
            )
            if state.last_error:
                lines.append(f"last error: {state.last_error[:300]}")
        return "\n".join(lines)

    async def _command_run_public_now(self) -> str:
        return await self._run_named_now("public-figure-scan")

    async def _command_run_stock_now(self) -> str:
        return await self._run_named_now("stock-hourly-scan")

    def _command_pause(self) -> str:
        self.scheduled_paused = True
        return "Scheduled scans are paused. Manual /run_public_now and /run_stock_now still work."

    def _command_resume(self) -> str:
        self.scheduled_paused = False
        return "Scheduled scans are resumed."


def main() -> int:
    return asyncio.run(AlwaysOnRunner().run_forever())


if __name__ == "__main__":
    raise SystemExit(main())
