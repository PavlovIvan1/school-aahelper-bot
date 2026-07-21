from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📩 Написать в поддержку",
            callback_data="get_support:chat",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📞 Заказать звонок",
            callback_data="get_support:call",
        )
    )
    return builder.as_markup()


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main"))
    return builder.as_markup()


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🛠 Открыть панель",
            web_app=WebAppInfo(url=config.ADMIN_WEBAPP_URL),
        )
    )
    return builder.as_markup()


def support_call_booking_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="Записаться",
            url=config.SUPPORT_CALL_FORM_URL,
        )
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main"))
    return builder.as_markup()
