from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db

logger = logging.getLogger(__name__)

_CONCURRENCY = 20
_MAX_RETRIES = 3


def _build_markup(button_text: str | None, button_url: str | None) -> InlineKeyboardMarkup | None:
    if not button_text or not button_url:
        return None
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=button_text, url=button_url))
    return builder.as_markup()


async def run_broadcast(
    bot: Bot,
    broadcast_id: int,
    text: str,
    button_text: str | None,
    button_url: str | None,
) -> None:
    user_ids = await db.get_active_user_ids()
    markup = _build_markup(button_text, button_url)

    await db.update_broadcast_progress(broadcast_id, 0, 0, status="running")

    sent = 0
    failed = 0
    counters_lock = asyncio.Lock()
    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def _send(telegram_id: int) -> None:
        nonlocal sent, failed
        ok = False
        async with semaphore:
            for attempt in range(_MAX_RETRIES):
                try:
                    await bot.send_message(telegram_id, text, reply_markup=markup)
                    ok = True
                    break
                except TelegramRetryAfter as exc:
                    await asyncio.sleep(exc.retry_after)
                except TelegramForbiddenError:
                    await db.mark_blocked(telegram_id)
                    break
                except TelegramBadRequest as exc:
                    logger.warning("Broadcast %s: bad request for %s: %s", broadcast_id, telegram_id, exc)
                    break
                except Exception:
                    logger.exception("Broadcast %s: failed to send to %s", broadcast_id, telegram_id)
                    break

        async with counters_lock:
            if ok:
                sent += 1
            else:
                failed += 1
            await db.update_broadcast_progress(broadcast_id, sent, failed)

    await asyncio.gather(*(_send(uid) for uid in user_ids))
    await db.update_broadcast_progress(broadcast_id, sent, failed, status="done")
