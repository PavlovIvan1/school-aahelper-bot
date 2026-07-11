from pathlib import Path

from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env("BOT_TOKEN")

# Прокси для Telegram. Задаётся в .env через TELEGRAM_PROXY_URL.
# Поддерживаются http:// и socks5:// (для socks нужен пакет aiohttp-socks).
# Если не задан — бот и запросы идут напрямую, без прокси.
TELEGRAM_PROXY_URL = env("TELEGRAM_PROXY_URL", "") or None
HTTP_PROXY = env("HTTP_PROXY", "") or TELEGRAM_PROXY_URL
HTTPS_PROXY = env("HTTPS_PROXY", "") or TELEGRAM_PROXY_URL
ALL_PROXY = env("ALL_PROXY", "") or TELEGRAM_PROXY_URL

SUPPORT_CALL_FORM_URL = env(
    "SUPPORT_CALL_FORM_URL",
    "https://forms.amocrm.ru/rzlwvrl",
)

OMNIDESK_WEBHOOK_URL = env(
    "OMNIDESK_WEBHOOK_URL",
    "https://telegramwh.omnidesk.ru/webhooks/telegram/13619/2ad59c852bbdcf83",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
