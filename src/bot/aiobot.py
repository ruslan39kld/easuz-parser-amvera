# src/bot/aiobot.py
# ПОЛНАЯ ВЕРСИЯ: ИЗБРАННОЕ + СРАВНЕНИЕ + ГЕОЛОКАЦИЯ (с ручным вводом координат)

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from src.services.search import SearchService
from src.services.favorites import FavoritesService
from src.services.comparison import ComparisonService
from src.services.geocoder import YandexGeocoder
from src.database.session import get_db
import asyncio
import logging
import re

logger = logging.getLogger(__name__)

BOT_TOKEN = "8515654664:AAFnBg8Qk_NL6IQvOS49bK-hnk2Pcqf_I_g"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранение геопозиций пользователей (в памяти)
user_locations = {}

# Флаг ожидания координат
waiting_for_coords = set()

# === Категории ===
CATEGORY_FILTERS = {
    "1": "аренда покупка имущество",
    "2": "ИЖС дом жильё",
    "3": "бизнес коммерция",
    "4": "сельское хозяйство сельхоз",
}


def _get_purpose_fallback(listing):
    """Умное определение назначения"""
    if listing.land_allowed_use_name and listing.land_allowed_use_name.strip():
        return listing.land_allowed_use_name

    name_lower = listing.name.lower()

    if any(word in name_lower for word in ["ижс", "индивидуаль", "жилищн", "жил", "дом"]):
        return "Для индивидуального жилищного строительства (ИЖС)"
    elif any(word in name_lower for word in ["бизнес", "коммерч", "предприним", "предпринимател"]):
        return "Для осуществления предпринимательской деятельности"
    elif any(word in name_lower for word in ["сельхоз", "сельск", "лпх", "кфх", "садовод", "огородн"]):
        return "Для сельскохозяйственного использования"
    elif any(word in name_lower for word in ["аренда", "арендова"]):
        return "Аренда земельного участка"
    elif any(word in name_lower for word in ["здани", "помещен", "нежил"]):
        return "Продажа помещения/здания"
    else:
        return "Не указано"


def _build_easuz_link(listing) -> str:
    """Построение правильной ссылки на ЕАСУЗ"""
    if listing.direct_url and listing.direct_url.strip():
        return listing.direct_url
    if listing.registry_number and listing.registry_number.strip():
        return f"https://easuz.mosreg.ru/torgi/purchase/{listing.registry_number}"
    logger.warning(f"⚠️ У объявления {listing.id} нет registry_number!")
    return "https://easuz.mosreg.ru/torgi"


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome = (
        "👋 Здравствуйте!\n\n"
        "Я интеллектуальный помощник по поиску земельных участков и имущества "
        "для участия в торгах системы <b>ЕАСУЗ Московской области</b>.\n\n"
        "✅ <b>Мои возможности:</b>\n"
        "• Быстрый поиск по вашим критериям\n"
        "• Анализ и сравнение объектов\n"
        "• Сохранение в избранное\n"
        "• Расчет расстояний\n\n"
        "💬 <b>Как начать?</b>\n"
        "Просто опишите что ищете. Например:\n"
        "• <i>участок в Мытищах до 2 млн</i>\n"
        "• <i>аренда земли под ИЖС в Химках</i>\n"
        "• <i>земля под бизнес до 5000000</i>\n\n"
        "Что будем искать?"
    )

    # Получаем количество избранных
    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        fav_count = fav_service.count(message.from_user.id)

    # 7 КНОПОК (новый порядок: консультация перед избранным)
    fav_text = f"⭐ Мое избранное ({fav_count})" if fav_count > 0 else "⭐ Мое избранное"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ Что я могу?", callback_data="show_capabilities")],
            [InlineKeyboardButton(text="🏢 Аренда и покупка имущества", callback_data="category_1")],
            [InlineKeyboardButton(text="🏡 Участок под дом", callback_data="category_2")],
            [InlineKeyboardButton(text="💼 Земля для бизнеса", callback_data="category_3")],
            [InlineKeyboardButton(text="🌾 Земля под сельское хозяйство", callback_data="category_4")],
            [InlineKeyboardButton(text="💬 Консультация по ЕАСУЗ", url="https://t.me/easuz_ai_bot")],
            [InlineKeyboardButton(text=fav_text, callback_data="show_favorites")],
        ]
    )

    await message.answer(welcome, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "show_capabilities")
async def handle_show_capabilities(callback: types.CallbackQuery):
    """Показ развернутой информации о возможностях бота"""
    capabilities = (
        "🤖 <b>Мои возможности и преимущества:</b>\n\n"
        
        "🔍 <b>УМНЫЙ ПОИСК</b>\n"
        "• Понимаю естественный язык — пишите как удобно вам\n"
        "• Автоматически определяю район, цену, площадь, назначение\n"
        "• Ищу по 2500+ актуальным объявлениям ЕАСУЗ\n"
        "• Мгновенные результаты без сложных форм\n\n"
        
        "📊 <b>АНАЛИЗ И СРАВНЕНИЕ</b>\n"
        "• Детальная информация по каждому лоту\n"
        "• Сравнение до 10 объектов по ключевым параметрам\n"
        "• Расчет цены за м² для объективной оценки\n"
        "• Определение расстояния от вашего местоположения\n"
        "• Наглядные таблицы с рекомендациями\n\n"
        
        "⭐ <b>ПЕРСОНАЛЬНОЕ ИЗБРАННОЕ</b>\n"
        "• Сохраните до 10 интересных объектов\n"
        "• Быстрый доступ к сохраненным лотам\n"
        "• Возможность сравнить избранные варианты\n"
        "• Не теряйте найденные предложения\n\n"
        
        "🎯 <b>КАТЕГОРИИ ПОИСКА</b>\n"
        "• 🏢 Аренда и покупка имущества\n"
        "• 🏡 Участки под дом/ИЖС\n"
        "• 💼 Земля для бизнеса\n"
        "• 🌾 Земля для сельского хозяйства\n\n"
        
        "💡 <b>ЗАЧЕМ ЭТО НУЖНО?</b>\n"
        "✓ Экономия времени: не нужно вручную листать тысячи объявлений\n"
        "✓ Точность поиска: находите именно то, что соответствует критериям\n"
        "✓ Прозрачность: видите все параметры объекта сразу\n"
        "✓ Удобство: работает 24/7, отвечает мгновенно\n"
        "✓ Помощь в выборе: сравнивайте и принимайте взвешенные решения\n\n"
        
        "🚀 <b>ПЕРСПЕКТИВЫ</b>\n"
        "В разработке:\n"
        "• Уведомления о новых подходящих лотах\n"
        "• История изменения цен\n"
        "• Аналитика рынка по районам\n"
        "• Калькулятор потенциальной выгоды\n\n"
        
        "📌 <b>КАК Я ПОМОГУ ВАМ?</b>\n"
        "• Инвесторам — найти выгодные объекты под застройку\n"
        "• Предпринимателям — подобрать землю для бизнеса\n"
        "• Частным лицам — выбрать участок под дом мечты\n"
        "• Агентам — быстро подбирать варианты для клиентов\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Готов приступить к поиску!\n"
        "Просто напишите что вам нужно 😊"
    )
    
    await callback.message.answer(capabilities, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("category_"))
async def handle_category_button(callback: types.CallbackQuery):
    category_id = callback.data.split("_")[1]
    keywords = CATEGORY_FILTERS.get(category_id, "")

    logger.info(f"🔍 Поиск по категории {category_id}: '{keywords}'")

    with next(get_db()) as db:
        service = SearchService(db)
        results = service.search_by_natural_language(keywords)

    category_names = {
        "1": "Аренда и покупка имущества",
        "2": "Участок под дом",
        "3": "Земля для бизнеса",
        "4": "Земля под сельское хозяйство"
    }
    cat_name = category_names.get(category_id, "Выбранная категория")

    await callback.message.answer(
        f"🔍 Показаны объявления по категории:\n<b>«{cat_name}»</b>",
        parse_mode="HTML"
    )

    if not results:
        logger.warning(f"❌ Категория {category_id}: ничего не найдено в БД")
        await callback.message.answer(
            "🔍 К сожалению, по данной категории ничего не найдено\n\n"
            "💡 <b>Попробуйте:</b>\n"
            "• Выбрать другую категорию\n"
            "• Написать запрос текстом (например: <i>участок в Балашихе</i>)\n"
            "• Изменить параметры поиска",
            parse_mode="HTML"
        )
    else:
        logger.info(f"✅ Найдено {len(results)} объектов")
        await _send_listings(callback.message, results[:7], callback.from_user.id)

    await callback.answer()


@dp.message(F.text)
async def handle_text_message(message: types.Message):
    """Обработка текстовых сообщений (поиск, координаты или адрес)"""
    user_text = message.text.strip()
    user_id = message.from_user.id
    
    # Проверяем, ожидаем ли мы координаты/адрес от этого пользователя
    if user_id in waiting_for_coords:
        # Сначала пробуем распарсить как координаты
        # Форматы: "55.7558, 37.6173" или "55.7558 37.6173"
        coord_pattern = r'(-?\d+\.?\d*)[,\s]+(-?\d+\.?\d*)'
        match = re.search(coord_pattern, user_text)
        
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                
                # Проверка валидности координат
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    user_locations[user_id] = (lat, lon)
                    waiting_for_coords.discard(user_id)
                    
                    await message.answer(
                        f"✅ <b>Координаты сохранены!</b>\n\n"
                        f"📍 {lat:.4f}, {lon:.4f}\n\n"
                        f"Теперь можете сравнивать объявления по расстоянию от этой точки.",
                        parse_mode="HTML"
                    )
                    
                    # АВТОМАТИЧЕСКИ показываем меню сравнения
                    with next(get_db()) as db:
                        fav_service = FavoritesService(db)
                        fav_count = fav_service.count(user_id)
                        
                        if fav_count >= 2:
                            await show_comparison_menu(message, user_id)
                        else:
                            await message.answer(
                                f"💡 У вас сохранено {fav_count} объявлений.\n"
                                f"Добавьте минимум 2 объявления в избранное для сравнения.",
                                parse_mode="HTML"
                            )
                    
                    return
                else:
                    await message.answer(
                        "❌ Неверные координаты. Широта должна быть от -90 до 90, долгота от -180 до 180.\n\n"
                        "Попробуйте еще раз или напишите /start для отмены."
                    )
                    return
            except ValueError:
                pass
        
        # Если не координаты - пробуем как адрес
        geocoder = YandexGeocoder()
        coords = geocoder.geocode_address(user_text)
        
        if coords:
            lat, lon = coords
            user_locations[user_id] = (lat, lon)
            waiting_for_coords.discard(user_id)
            
            await message.answer(
                f"✅ <b>Адрес найден!</b>\n\n"
                f"📍 {user_text}\n"
                f"🗺 Координаты: {lat:.4f}, {lon:.4f}\n\n"
                f"Теперь можете сравнивать объявления по расстоянию от этой точки.",
                parse_mode="HTML"
            )
            
            # АВТОМАТИЧЕСКИ показываем меню сравнения
            with next(get_db()) as db:
                fav_service = FavoritesService(db)
                fav_count = fav_service.count(user_id)
                
                if fav_count >= 2:
                    await show_comparison_menu(message, user_id)
                else:
                    await message.answer(
                        f"💡 У вас сохранено {fav_count} объявлений.\n"
                        f"Добавьте минимум 2 объявления в избранное для сравнения.",
                        parse_mode="HTML"
                    )
            
            return
        else:
            # Не удалось распознать ни как координаты, ни как адрес
            await message.answer(
                "❌ Не удалось определить местоположение.\n\n"
                "💡 <b>Попробуйте:</b>\n"
                "• Уточнить адрес (например: <i>Красногорск, ул. Строителей 1</i>)\n"
                "• Отправить координаты: <code>55.9649, 37.4201</code>\n"
                "• Или напишите /start для отмены",
                parse_mode="HTML"
            )
            return
    
    # Обычный поиск
    logger.info(f"🔍 Поиск по запросу: '{user_text}'")

    with next(get_db()) as db:
        service = SearchService(db)
        results = service.search_by_natural_language(user_text)

        if not results:
            logger.warning(f"❌ По запросу '{user_text}' ничего не найдено")
            await message.answer(
                "🔍 К сожалению, по вашему запросу ничего не найдено\n\n"
                "💡 <b>Попробуйте:</b>\n"
                "• Изменить название района (например: <i>Балашиха вместо Балашихинский</i>)\n"
                "• Увеличить максимальную цену\n"
                "• Убрать часть критериев из запроса\n"
                "• Использовать другие ключевые слова",
                parse_mode="HTML"
            )
        else:
            logger.info(f"✅ Найдено {len(results)} объектов")
            await _send_listings(message, results[:7], message.from_user.id)


async def _send_listings(message, listings, user_id):
    """Отправка списка объявлений с кнопками избранного"""
    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        
        for i, listing in enumerate(listings, 1):
            easuz_link = _build_easuz_link(listing)
            full_address = listing.full_address or listing.address_description or "Адрес не указан"
            display_address = (full_address[:100] + "...") if len(full_address) > 100 else full_address
            purpose = _get_purpose_fallback(listing)
            cadastral = listing.cadastral_number or "Не указан"

            caption = (
                f"📌 <b>Объявление {i}</b>\n"
                f"{listing.name}\n\n"
                f"💰 <b>Цена:</b> {int(listing.start_price):,} ₽\n"
                f"📏 <b>Площадь:</b> {int(listing.total_square) if listing.total_square else 0} кв.м\n"
                f"📍 <b>Адрес:</b> {display_address}\n"
                f"🏷 <b>Назначение:</b> {purpose}\n"
                f"🆔 <b>Кадастр:</b> <code>{cadastral}</code>\n"
                f"🔗 <a href='{easuz_link}'>Открыть на ЕАСУЗ</a>"
            )

            # Кнопка избранного
            is_fav = fav_service.is_favorite(user_id, listing.id)
            fav_button_text = "⭐ Убрать из избранного" if is_fav else "⭐ В избранное"
            fav_callback = f"rem_fav_{listing.id}" if is_fav else f"add_fav_{listing.id}"
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text=fav_button_text, callback_data=fav_callback)
                ]]
            )

            # Отправка с фото
            photo_sent = False
            if listing.photos and len(listing.photos) > 0:
                photo_url = listing.photos[0]
                if photo_url and (photo_url.startswith('http://') or photo_url.startswith('https://')):
                    try:
                        await message.answer_photo(
                            photo=photo_url,
                            caption=caption,
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                        photo_sent = True
                    except Exception:
                        pass

            if not photo_sent:
                await message.answer(caption, parse_mode="HTML", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("add_fav_"))
async def handle_add_favorite(callback: types.CallbackQuery):
    """Добавление в избранное"""
    listing_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        
        if fav_service.add(user_id, listing_id):
            count = fav_service.count(user_id)
            await callback.answer(f"✅ Добавлено в избранное ({count}/10)", show_alert=True)
        else:
            count = fav_service.count(user_id)
            if count >= 10:
                await callback.answer("❌ Достигнут лимит (10 объявлений)", show_alert=True)
            else:
                await callback.answer("❌ Уже в избранном", show_alert=True)


@dp.callback_query(lambda c: c.data.startswith("rem_fav_"))
async def handle_remove_favorite(callback: types.CallbackQuery):
    """Удаление из избранного"""
    listing_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id

    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        
        if fav_service.remove(user_id, listing_id):
            count = fav_service.count(user_id)
            await callback.answer(f"✅ Удалено из избранного ({count})", show_alert=True)
        else:
            await callback.answer("❌ Не найдено в избранном", show_alert=True)


@dp.callback_query(lambda c: c.data == "show_favorites")
async def handle_show_favorites(callback: types.CallbackQuery):
    """Показ избранного"""
    user_id = callback.from_user.id

    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        favorites = fav_service.get_all(user_id)

        if not favorites:
            await callback.message.answer(
                "⭐ <b>Ваше избранное пусто</b>\n\n"
                "Добавьте объявления, нажав кнопку <b>⭐ В избранное</b> под интересующими предложениями.",
                parse_mode="HTML"
            )
        else:
            count = len(favorites)
            await callback.message.answer(
                f"⭐ <b>Ваше избранное ({count}/10)</b>\n\n"
                f"Всего сохранено: {count} объявлений",
                parse_mode="HTML"
            )
            await _send_listings(callback.message, favorites, user_id)

            # Кнопки управления избранным
            if count >= 2:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="📊 Сравнить", callback_data="show_compare_menu")],
                        [InlineKeyboardButton(text="🗑 Очистить избранное", callback_data="clear_favorites")]
                    ]
                )
            else:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🗑 Очистить избранное", callback_data="clear_favorites")]
                    ]
                )
            
            await callback.message.answer(
                "Управление избранным:",
                reply_markup=keyboard
            )

    await callback.answer()


@dp.callback_query(lambda c: c.data == "clear_favorites")
async def handle_clear_favorites(callback: types.CallbackQuery):
    """Очистка избранного"""
    user_id = callback.from_user.id

    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        count = fav_service.clear(user_id)
        
        await callback.answer(f"✅ Удалено {count} объявлений", show_alert=True)
        await callback.message.answer(
            "🗑 <b>Избранное очищено</b>",
            parse_mode="HTML"
        )


@dp.callback_query(lambda c: c.data == "show_compare_menu")
async def handle_show_compare_menu(callback: types.CallbackQuery):
    """Показ меню выбора параметра сравнения"""
    await show_comparison_menu(callback.message, callback.from_user.id)
    await callback.answer()


async def show_comparison_menu(message: types.Message, user_id: int):
    """Вспомогательная функция для показа меню сравнения"""
    # Проверяем наличие геопозиции
    has_location = user_id in user_locations
    
    buttons = [
        [InlineKeyboardButton(text="💰 По цене", callback_data="compare_price")],
        [InlineKeyboardButton(text="📏 По площади", callback_data="compare_area")],
        [InlineKeyboardButton(text="💵 По цене за м²", callback_data="compare_price_per_sqm")],
    ]
    
    # Добавляем кнопку "По расстоянию" только если есть геопозиция
    if has_location:
        buttons.append([InlineKeyboardButton(text="📍 По расстоянию от меня", callback_data="compare_distance")])
    else:
        buttons.append([InlineKeyboardButton(text="📍 Указать местоположение", callback_data="request_location")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        "📊 <b>Выберите параметр сравнения:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data == "request_location")
async def handle_request_location(callback: types.CallbackQuery):
    """Запрос геопозиции пользователя"""
    user_id = callback.from_user.id
    waiting_for_coords.add(user_id)
    
    await callback.message.answer(
        "📍 <b>Укажите ваше местоположение</b>\n\n"
        
        "📱 <b>С ТЕЛЕФОНА:</b>\n"
        "1️⃣ Нажмите кнопку 📎 (скрепка) внизу\n"
        "2️⃣ Выберите <b>Геопозиция</b>\n"
        "3️⃣ Подтвердите отправку\n\n"
        
        "💻 <b>С КОМПЬЮТЕРА - 3 способа:</b>\n\n"
        
        "<b>Способ 1</b> - Введите адрес:\n"
        "Просто напишите адрес, например:\n"
        "• <code>Красногорск, ул. Строителей 1</code>\n"
        "• <code>Балашиха, Советская 12</code>\n"
        "Бот автоматически определит координаты ✅\n\n"
        
        "<b>Способ 2</b> - Координаты из Яндекс.Карт:\n"
        "1️⃣ Откройте <a href='https://yandex.ru/maps'>Яндекс.Карты</a>\n"
        "2️⃣ Найдите нужное место\n"
        "3️⃣ Нажмите правой кнопкой → <b>Что здесь?</b>\n"
        "4️⃣ Скопируйте координаты\n"
        "5️⃣ Отправьте сюда в формате: <code>55.9649, 37.4201</code>\n\n"
        
        "<b>Способ 3</b> - Координаты из Google Maps:\n"
        "1️⃣ Откройте Google Maps\n"
        "2️⃣ Кликните на нужное место\n"
        "3️⃣ Координаты появятся внизу\n"
        "4️⃣ Скопируйте и отправьте\n\n"
        
        "Жду ваш адрес или координаты! 😊",
        parse_mode="HTML",
        disable_web_page_preview=True
    )
    await callback.answer()


@dp.message(F.location)
async def handle_location(message: types.Message):
    """Обработка полученной геопозиции"""
    user_id = message.from_user.id
    latitude = message.location.latitude
    longitude = message.location.longitude
    
    # Сохраняем геопозицию
    user_locations[user_id] = (latitude, longitude)
    waiting_for_coords.discard(user_id)
    
    await message.answer(
        f"✅ <b>Местоположение сохранено!</b>\n\n"
        f"📍 Координаты: {latitude:.4f}, {longitude:.4f}\n\n"
        f"Теперь вы можете сравнивать объявления по расстоянию от вас.",
        parse_mode="HTML"
    )
    
    # АВТОМАТИЧЕСКИ показываем меню сравнения
    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        fav_count = fav_service.count(user_id)
        
        if fav_count >= 2:
            await show_comparison_menu(message, user_id)
        else:
            await message.answer(
                f"💡 У вас сохранено {fav_count} объявлений.\n"
                f"Добавьте минимум 2 объявления в избранное для сравнения.",
                parse_mode="HTML"
            )


@dp.callback_query(lambda c: c.data.startswith("compare_"))
async def handle_compare(callback: types.CallbackQuery):
    """Обработка сравнения"""
    user_id = callback.from_user.id
    compare_type = callback.data.split("_")[1]
    
    with next(get_db()) as db:
        fav_service = FavoritesService(db)
        favorites = fav_service.get_all(user_id)

        if len(favorites) < 2:
            await callback.answer("❌ Добавьте минимум 2 объявления для сравнения", show_alert=True)
            return

        # Получаем геопозицию пользователя (если есть)
        user_location = user_locations.get(user_id)
        
        # Если выбрано сравнение по расстоянию, но геопозиции нет
        if compare_type == "distance" and not user_location:
            await callback.answer("❌ Сначала укажите свое местоположение", show_alert=True)
            return

        # Сортировка
        comp_service = ComparisonService()
        if compare_type == "price":
            sorted_listings = comp_service.compare(favorites, "price")
            sort_type = "price"
        elif compare_type == "area":
            sorted_listings = comp_service.compare(favorites, "area")
            sort_type = "area"
        elif compare_type in ["price", "per", "sqm"]:  # compare_price_per_sqm
            sorted_listings = comp_service.compare(favorites, "price_per_sqm")
            sort_type = "price_per_sqm"
        elif compare_type == "distance":
            sorted_listings = comp_service.compare(favorites, "distance", user_location=user_location)
            sort_type = "distance"
        else:
            sorted_listings = favorites
            sort_type = "price"

        # Форматирование таблицы
        table = comp_service.format_comparison_table(sorted_listings, sort_type, user_location=user_location)
        
        # Умные рекомендации
        recommendations = comp_service.get_best_recommendations(sorted_listings, user_location=user_location)
        
        result = table + recommendations
        
        await callback.message.answer(result, parse_mode="HTML", disable_web_page_preview=True)
    
    await callback.answer()


async def main():
    logger.info("🤖 Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())