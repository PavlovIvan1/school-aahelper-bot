from pathlib import Path

from environs import Env

env = Env()
env.read_env()

BOT_TOKEN = env("BOT_TOKEN")
SUPPORT_CALL_FORM_URL = env(
    "SUPPORT_CALL_FORM_URL",
    "https://forms.amocrm.ru/rzlwvrl",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
