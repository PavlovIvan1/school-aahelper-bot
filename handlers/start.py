import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

import keyboard
from banner import resolve_banner_path
from texts import WELCOME_CAPTION

router = Router()
logger = logging.getLogger(__name__)


async def send_welcome(target: Message) -> None:
    markup = keyboard.main_menu_keyboard()
    banner_path = resolve_banner_path()

    if banner_path is not None:
        try:
            await target.answer_photo(
                photo=FSInputFile(banner_path),
                caption=WELCOME_CAPTION,
                reply_markup=markup,
            )
            return
        except Exception as exc:
            logger.warning("Failed to send banner %s: %s", banner_path, exc)

    await target.answer(WELCOME_CAPTION, reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await send_welcome(message)


@router.callback_query(F.data == "main")
async def back_to_main(call: CallbackQuery) -> None:
    await call.answer()
    try:
        await call.message.delete()
    except Exception:
        pass
    await send_welcome(call.message)
