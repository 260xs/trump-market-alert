from __future__ import annotations

from pathlib import Path

import pytest

from telegram_commands import CommandContext, MENU_TEXT, TelegramCommandCenter


async def _public_done() -> str:
    return "public done"


async def _stock_done() -> str:
    return "stock done"


def _context(tmp_path: Path) -> CommandContext:
    return CommandContext(
        public_db_path=tmp_path / "public.sqlite3",
        stock_db_path=tmp_path / "stock.sqlite3",
        status=lambda: "status ok",
        run_public_now=_public_done,
        run_stock_now=_stock_done,
        pause=lambda: "paused",
        resume=lambda: "resumed",
    )


@pytest.mark.asyncio
async def test_command_menu_and_safe_controls(tmp_path: Path):
    center = TelegramCommandCenter("token", "123", _context(tmp_path))

    assert await center.dispatch("/menu") == MENU_TEXT
    assert await center.dispatch("/status") == "status ok"
    assert await center.dispatch("/run_public_now") == "public done"
    assert await center.dispatch("/run_stock_now") == "stock done"
    assert await center.dispatch("/pause") == "paused"
    assert await center.dispatch("/resume") == "resumed"
    assert "Unknown command" in await center.dispatch("/trade")
