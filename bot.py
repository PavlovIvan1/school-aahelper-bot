import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

import admin_api
import config
import db
from handlers import admin_router, start_router, support_router
from middlewares import ActivityMiddleware

bot_session = AiohttpSession(proxy=config.TELEGRAM_PROXY_URL)


async def main() -> None:
    await db.init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        session=bot_session,
        default=DefaultBotProperties(),
    )
    dp = Dispatcher(storage=MemoryStorage())

    activity_middleware = ActivityMiddleware()
    dp.message.outer_middleware(activity_middleware)
    dp.callback_query.outer_middleware(activity_middleware)

    dp.include_routers(admin_router, start_router, support_router)

    await asyncio.gather(
        dp.start_polling(bot),
        admin_api.run_api_server(bot),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
