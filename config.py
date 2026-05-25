from pathlib import Path

from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env("BOT_TOKEN")

# Telegram proxy (как в school-aabot; можно переопределить в .env)
TELEGRAM_PROXY_URL = env(
    "TELEGRAM_PROXY_URL",
    "http://hXZsbn:1wHmj3@45.130.131.214:8000",
)
HTTP_PROXY = env("HTTP_PROXY", TELEGRAM_PROXY_URL)
HTTPS_PROXY = env("HTTPS_PROXY", TELEGRAM_PROXY_URL)
ALL_PROXY = env("ALL_PROXY", TELEGRAM_PROXY_URL)

SUPPORT_CALL_FORM_URL = env(
    "SUPPORT_CALL_FORM_URL",
    "https://forms.amocrm.ru/rzlwvrl",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
