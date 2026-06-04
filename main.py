from __future__ import annotations

import asyncio
import logging

from config import load_settings, load_watchlist
from database.db import Database
from scheduler import Scheduler


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)sZ %(levelname)s %(name)s: %(message)s",
    )
    logging.Formatter.converter = time_gmt


def time_gmt(*args):
    import time
    return time.gmtime(*args)


async def async_main() -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    db = Database(settings.sqlite_path)
    db.init()
    db.upsert_watchlist(load_watchlist().get("people", []))
    scheduler = Scheduler(db, settings)
    if settings.run_once:
        return await scheduler.run_once()
    await scheduler.run_forever()
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
