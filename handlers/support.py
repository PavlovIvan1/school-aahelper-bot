from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message

import keyboard
import omnidesk
from texts import SUPPORT_CALL_BOOKING_TEXT, SUPPORT_CHAT_PROMPT

router = Router()


class SupportChat(StatesGroup):
    waiting_question = State()
    in_chat = State()


async def _edit_or_answer(
    call: CallbackQuery,
    text: str,
    reply_markup=None,
) -> Message:
    try:
        if call.message.text or call.message.caption:
            return await call.message.edit_text(text=text, reply_markup=reply_markup)
    except Exception:
        pass
    return await call.message.answer(text=text, reply_markup=reply_markup)


@router.callback_query(F.data == "get_support:call")
async def order_call(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.clear()
    await _edit_or_answer(
        call,
        SUPPORT_CALL_BOOKING_TEXT,
        reply_markup=keyboard.support_call_booking_keyboard(),
    )


@router.callback_query(F.data == "get_support:chat")
async def write_support(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(SupportChat.waiting_question)
    msg = await _edit_or_answer(
        call,
        SUPPORT_CHAT_PROMPT,
        reply_markup=keyboard.back_to_main_keyboard(),
    )
    await state.update_data(prompt_message_id=msg.message_id)


@router.message(StateFilter(SupportChat.waiting_question, SupportChat.in_chat))
async def support_message_to_omnidesk(message: Message, state: FSMContext) -> None:
    update = omnidesk.message_to_telegram_update(message)
    handled = await omnidesk.forward_to_omnidesk(update)

    if handled:
        current = await state.get_state()
        if current == SupportChat.waiting_question.state:
            await state.set_state(SupportChat.in_chat)
        return

    await message.answer(
        "Не удалось отправить сообщение в поддержку. "
        "Попробуйте ещё раз или нажмите «Назад».",
        reply_markup=keyboard.back_to_main_keyboard(),
    )
