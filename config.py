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

# ID администраторов в Telegram, через запятую: ADMIN_IDS=123456789,987654321
ADMIN_IDS: list[int] = env.list("ADMIN_IDS", subcast=int, default=[])

# HTTPS-адрес задеплоенной админ-панели (mini app), например на Vercel.
# Используется и для кнопки WebApp в /admin, и для проверки CORS у API.
ADMIN_WEBAPP_URL = env("ADMIN_WEBAPP_URL", "")
CORS_ALLOWED_ORIGIN = env("CORS_ALLOWED_ORIGIN", "") or ADMIN_WEBAPP_URL or "*"

# HTTP API для админ-панели (слушает сам бот-процесс)
WEBAPP_API_HOST = env("WEBAPP_API_HOST", "0.0.0.0")
WEBAPP_API_PORT = env.int("WEBAPP_API_PORT", 8080)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "bot.db"
