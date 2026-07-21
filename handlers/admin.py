from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import config
import keyboard

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if message.from_user is None or message.from_user.id not in config.ADMIN_IDS:
        return
    if not config.ADMIN_WEBAPP_URL:
        await message.answer("ADMIN_WEBAPP_URL не задан в .env")
        return
    await message.answer(
        "Панель администратора:",
        reply_markup=keyboard.admin_panel_keyboard(),
    )
