# run.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from src.bot import create_bot

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    app = create_bot(settings.TELEGRAM_BOT_TOKEN)
    print("✅ Бот запущен. Ожидание команд...")
    app.run_polling()