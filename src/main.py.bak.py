# src/main.py

import sys
import os
import asyncio

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.settings import settings
from src.bot import create_bot


async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в .env")
        print("📁 Убедитесь, что файл .env находится в корне проекта:")
        print(f"   Z:\\__УЦТ\\Руслан\\easuz-parser 1\\.env")
        return

    print("🚀 Запуск бота...")
    app = create_bot(settings.TELEGRAM_BOT_TOKEN)
    print("✅ Бот запущен. Ожидание команд...")
    await app.run_polling()


if __name__ == "__main__":
    # 🔑 Решение для Windows: всегда используем новый event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Бот остановлен вручную.")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")