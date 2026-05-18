"""Aiogram bot entrypoint."""
from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from ..config import get_settings
from ..logging_setup import configure_logging, get_logger
from .handlers import build_root_router

log = get_logger("bot")


async def amain() -> None:
    configure_logging()
    settings = get_settings()
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not configured")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(build_root_router())

    log.info("bot.start")
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
