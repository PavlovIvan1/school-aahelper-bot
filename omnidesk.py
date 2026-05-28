import json
import logging
from typing import Any

import aiohttp
from aiogram.types import Message

import config

logger = logging.getLogger(__name__)


def message_to_telegram_update(message: Message) -> dict[str, Any]:
    return {
        "update_id": message.message_id,
        "message": message.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
        ),
    }


async def forward_to_omnidesk(update: dict[str, Any]) -> bool:
    """
    Отправляет update в Omnidesk (аналог widget_telegram.php).

    Возвращает True, если Omnidesk принял обращение и бот не должен
    обрабатывать сообщение дальше.
    """
    text = (update.get("message") or {}).get("text") or ""
    if text == "/start":
        return False

    connector = aiohttp.TCPConnector(ssl=False)
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                config.OMNIDESK_WEBHOOK_URL,
                json=update,
                proxy=config.HTTPS_PROXY,
            ) as response:
                raw = await response.text()
    except Exception as exc:
        logger.exception("Omnidesk webhook request failed: %s", exc)
        return False

    result: dict[str, Any] | None = None
    if raw:
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Omnidesk returned non-JSON: %s", raw[:500])
            return False

    if not result:
        return False
    if result.get("success") == "2":
        return False
    if result.get("success"):
        return True
    return False
