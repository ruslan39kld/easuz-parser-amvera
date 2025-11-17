# config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
    VSE_GPT_API_KEY = os.getenv("VSE_GPT_API_KEY")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/easuz")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    YANDEX_GEOCODER_API_KEY = os.getenv("YANDEX_GEOCODER_API_KEY")


settings = Settings()