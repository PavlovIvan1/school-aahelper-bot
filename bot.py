import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import start_router, support_router

bot_session = AiohttpSession(proxy=config.TELEGRAM_PROXY_URL)


async def main() -> None:
    bot = Bot(
        token=config.BOT_TOKEN,
        session=bot_session,
        default=DefaultBotProperties(),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(start_router, support_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
