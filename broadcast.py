from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
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


def _extract_ref(kind: str, message: Message) -> str | None:
    if kind == "photo" and message.photo:
        return message.photo[-1].file_id
    if kind == "animation" and message.animation:
        return message.animation.file_id
    if kind == "video" and message.video:
        return message.video.file_id
    return None


async def _send_single(
    bot: Bot,
    telegram_id: int,
    kind: str,
    ref: str | Path,
    text: str,
    markup: InlineKeyboardMarkup | None,
) -> Message:
    media = ref if isinstance(ref, str) else FSInputFile(ref)
    caption = text or None
    if kind == "photo":
        return await bot.send_photo(telegram_id, photo=media, caption=caption, parse_mode="HTML", reply_markup=markup)
    if kind == "animation":
        return await bot.send_animation(
            telegram_id, animation=media, caption=caption, parse_mode="HTML", reply_markup=markup
        )
    return await bot.send_video(telegram_id, video=media, caption=caption, parse_mode="HTML", reply_markup=markup)


async def _send_group(
    bot: Bot,
    telegram_id: int,
    items: list[tuple[str, str | Path]],
    text: str,
) -> list[Message]:
    media_list: list[InputMediaPhoto | InputMediaVideo] = []
    for i, (kind, ref) in enumerate(items):
        content = ref if isinstance(ref, str) else FSInputFile(ref)
        cls = InputMediaPhoto if kind == "photo" else InputMediaVideo
        kwargs: dict[str, Any] = {"media": content}
        if i == 0 and text:
            kwargs["caption"] = text
            kwargs["parse_mode"] = "HTML"
        media_list.append(cls(**kwargs))
    return await bot.send_media_group(telegram_id, media=media_list)


async def run_broadcast(
    bot: Bot,
    broadcast_id: int,
    user_ids: list[int],
    text: str,
    button_text: str | None,
    button_url: str | None,
    media_items: list[tuple[str, Path]] | None = None,
    upload_dir: Path | None = None,
) -> None:
    media_items = media_items or []
    is_group = len(media_items) >= 2
    markup = _build_markup(button_text, button_url) if not is_group else None

    await db.update_broadcast_progress(broadcast_id, 0, 0, status="running")

    try:
        if not user_ids:
            await db.update_broadcast_progress(broadcast_id, 0, 0, status="done")
            return

        sent = 0
        failed = 0
        counters_lock = asyncio.Lock()
        refs_lock = asyncio.Lock()
        semaphore = asyncio.Semaphore(_CONCURRENCY)

        # Пока file_id не "прогрелся" первой успешной отправкой, тут лежат
        # пути к файлам на диске; дальше — уже строки file_id для переиспользования.
        refs: list[str | Path] = [path for _, path in media_items]

        async def _send(telegram_id: int) -> None:
            nonlocal sent, failed
            ok = False
            async with semaphore:
                for _attempt in range(_MAX_RETRIES):
                    try:
                        async with refs_lock:
                            current_refs = list(refs)

                        if not media_items:
                            await bot.send_message(telegram_id, text, parse_mode="HTML", reply_markup=markup)
                        elif is_group:
                            items = [(kind, current_refs[i]) for i, (kind, _) in enumerate(media_items)]
                            result = await _send_group(bot, telegram_id, items, text)
                            async with refs_lock:
                                for i, msg in enumerate(result):
                                    ref = _extract_ref(media_items[i][0], msg)
                                    if ref:
                                        refs[i] = ref
                        else:
                            kind = media_items[0][0]
                            result = await _send_single(bot, telegram_id, kind, current_refs[0], text, markup)
                            ref = _extract_ref(kind, result)
                            if ref:
                                async with refs_lock:
                                    refs[0] = ref

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
    finally:
        if upload_dir is not None:
            shutil.rmtree(upload_dir, ignore_errors=True)
