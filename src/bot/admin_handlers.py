# src/bot/admin_handlers.py

from telegram import Update
from telegram.ext import ContextTypes
from src.database.session import get_db
from src.services.admin import AdminService
from config.settings import settings
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def admin_only(func):
    """Декоратор: доступ только для администратора."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        admin_id = settings.TELEGRAM_ADMIN_ID

        if str(user_id) != admin_id:
            await update.message.reply_text(
                "🔒 Эта команда доступна только администратору.\n"
                f"Ваш ID: {user_id}\n"
                f"Админ ID: {admin_id}"
            )
            logger.warning(f"Попытка доступа к админ-команде от {user_id}")
            return

        logger.info(f"Админ {user_id} вызвал команду: {func.__name__}")

        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Ошибка в команде {func.__name__}: {e}")
            await update.message.reply_text("❌ Произошла ошибка при выполнении команды.")

    return wrapper


@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats — показывает статистику."""
    with next(get_db()) as db:
        service = AdminService(db)
        stats = service.get_usage_stats()

    msg = (
        "📊 <b>Статистика использования</b>\n\n"
        f"👥 Всего пользователей: <code>{stats['total_users']}</code>\n"
        f"🟢 Активно за 7 дней: <code>{stats['active_users_7d']}</code>\n\n"
        f"🏘️ Всего участков: <code>{stats['total_listings']}</code>\n"
        f"✅ Активных объявлений: <code>{stats['active_listings']}</code>"
    )
    await update.message.reply_html(msg)


@admin_only
async def admin_popular(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /popular — популярные запросы."""
    with next(get_db()) as db:
        service = AdminService(db)
        queries = service.get_popular_queries()

    msg = "🔥 <b>Популярные запросы пользователей</b>\n\n" + "\n".join(f"• <code>{q}</code>" for q in queries)
    await update.message.reply_html(msg)


@admin_only
async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /export — экспорт в Excel."""
    with next(get_db()) as db:
        service = AdminService(db)
        try:
            excel_file = service.export_listings_to_excel()
        except Exception as e:
            logger.error(f"Ошибка экспорта Excel: {e}")
            await update.message.reply_text("❌ Не удалось создать файл Excel.")
            return

    await update.message.reply_document(
        document=excel_file,
        filename="easuz_listings_export.xlsx",
        caption="📄 Выгрузка всех активных объявлений из ЕАСУЗ\n"
                "Дата выгрузки: " + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )


@admin_only
async def admin_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /update — запуск обновления базы."""
    with next(get_db()) as db:
        service = AdminService(db)
        result = service.trigger_db_update()

    await update.message.reply_text(result)