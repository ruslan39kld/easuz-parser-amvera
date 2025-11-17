from telegram.ext import Application, CommandHandler, MessageHandler, filters
from .handlers import (
    start,
    handle_search_query,
    handle_analyze_command,
    help_command,
)

from .admin_handlers import admin_stats, admin_popular, admin_export, admin_update

def create_bot(token: str):
    app = Application.builder().token(token).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("analyze", handle_analyze_command))

    # Админ-команды
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("popular", admin_popular))
    app.add_handler(CommandHandler("export", admin_export))
    app.add_handler(CommandHandler("update", admin_update))

    # ❌ УДАЛЯЕМ ОБРАБОТЧИК КНОПКИ "МЕНЮ" — ОН СОЗДАЁТ КЛАВИАТУРУ
    # app.add_handler(MessageHandler(filters.TEXT & filters.Regex("Меню"), handle_menu_button))

    # Поиск (последний)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query))

    return app