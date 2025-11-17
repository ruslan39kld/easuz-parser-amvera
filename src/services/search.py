# src/services/search.py
# ИСПРАВЛЕННАЯ ВЕРСИЯ - умный поиск по назначениям

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional, Dict, Any
from src.database.models import Listing
from src.llm.prompt_engine import SearchPromptEngine
from src.llm.vsegpt_client import VseGPTClient
from config.settings import settings
import logging
import re

logger = logging.getLogger(__name__)


# ✅ МАППИНГ: Что ищет LLM → Что есть в БД
PURPOSE_MAPPING = {
    "торгов": ["Магазины", "Объекты торговли", "Рынки"],
    "бизнес": ["Производственная деятельность", "Деловое управление", "Склад"],
    "коммерч": ["Производственная деятельность", "Магазины", "Бытовое обслуживание"],
    "предприним": ["Производственная деятельность", "Деловое управление"],
    "ижс": ["Для индивидуального жилищного строительства"],
    "жилищн": ["Для индивидуального жилищного строительства"],
    "дом": ["Для индивидуального жилищного строительства"],
    "сельхоз": ["Для ведения личного подсобного хозяйства", "Растениеводство", "Скотоводство", "Сельскохозяйственное использование"],
    "лпх": ["Для ведения личного подсобного хозяйства"],
    "садовод": ["Ведение садоводства"],
    "склад": ["Склад", "Складские площадки"],
    "производ": ["Производственная деятельность", "Строительная промышленность"],
    "обслуж": ["Бытовое обслуживание", "Коммунальное обслуживание"],
    "гараж": ["Хранение автотранспорта", "Служебные гаражи"],
}


class SearchService:
    """Сервис для умного поиска участков и имущества"""
    
    def __init__(self, db: Session):
        self.db = db
        try:
            self.llm_client = VseGPTClient(settings.VSE_GPT_API_KEY)
            self.llm_enabled = True
        except Exception as e:
            logger.error(f"❌ Не удалось инициализировать LLM клиент: {e}")
            self.llm_client = None
            self.llm_enabled = False
    
    def search_by_natural_language(
        self,
        user_query: str,
        enable_fallback: bool = True
    ) -> List[Listing]:
        """Поиск участков по естественному языку"""
        logger.info("=" * 80)
        logger.info(f"🔍 Начат поиск по запросу: '{user_query}'")
        
        if not self.llm_enabled or self.llm_client is None:
            logger.warning("⚠️ LLM недоступен, используем прямой поиск")
            return self._smart_fallback_search(user_query)
        
        try:
            messages = SearchPromptEngine.build_llm_messages(user_query)
        except Exception as e:
            logger.error(f"❌ Ошибка при формировании промпта: {e}")
            return self._smart_fallback_search(user_query)
        
        try:
            llm_response = self.llm_client.ask(
                messages=messages,
                temperature=0.2,
                max_tokens=300
            )
        except Exception as e:
            logger.error(f"❌ Ошибка при обращении к LLM: {e}")
            return self._smart_fallback_search(user_query)
        
        if not llm_response:
            logger.error("❌ LLM не вернул ответ")
            return self._smart_fallback_search(user_query)
        
        logger.info(f"✅ Ответ LLM (первые 300 символов): {llm_response[:300]}")
        
        try:
            filters = SearchPromptEngine.parse_llm_response(
                response=llm_response,
                original_query=user_query
            )
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга ответа LLM: {e}")
            return self._smart_fallback_search(user_query)
        
        if not filters:
            logger.warning("⚠️ Не удалось распарсить ответ LLM в фильтры")
            return self._smart_fallback_search(user_query)
        
        logger.info(f"📊 Извлеченные фильтры: {filters}")
        
        # ✅ НОВОЕ: Преобразуем фильтр назначения
        if filters.get("land_allowed_use_name"):
            filters = self._convert_purpose_filter(filters)
        
        results = self._execute_search(filters)
        
        if not results and enable_fallback:
            logger.warning("⚠️ По строгим фильтрам ничего не найдено. Пробую ослабить...")
            results = self._fallback_search_relaxed(filters)
        
        if not results:
            logger.warning("⚠️ Даже ослабленный поиск не дал результатов. Пробую умный fallback...")
            results = self._smart_fallback_search(user_query)
        
        logger.info(f"✅ Найдено участков: {len(results)}")
        logger.info("=" * 80)
        
        return results
    
    def _convert_purpose_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ НОВОЕ: Преобразование фильтра назначения
        LLM возвращает длинные названия → конвертируем в короткие из БД
        """
        original_purpose = filters["land_allowed_use_name"]
        logger.info(f"🔄 Конвертация назначения: '{original_purpose}'")
        
        # Ищем по ключевым словам
        purpose_lower = original_purpose.lower()
        matched_purposes = []
        
        for keyword, db_purposes in PURPOSE_MAPPING.items():
            if keyword in purpose_lower:
                matched_purposes.extend(db_purposes)
                logger.info(f"  ✓ Найдено совпадение по '{keyword}': {db_purposes}")
        
        if matched_purposes:
            # Убираем дубликаты
            matched_purposes = list(set(matched_purposes))
            filters["land_allowed_use_name_list"] = matched_purposes
            logger.info(f"  ✅ Итого назначений для поиска: {matched_purposes}")
        else:
            logger.warning(f"  ⚠️ Не удалось сконвертировать назначение, оставляю как есть")
        
        return filters
    
    def _execute_search(self, filters: Dict[str, Any]) -> List[Listing]:
        """Выполнение SQL-запроса с применением фильтров"""
        query = self.db.query(Listing).filter(Listing.is_active == True)
        
        if filters.get("district_code"):
            district = filters["district_code"]
            query = query.filter(Listing.address_description.ilike(f"%{district}%"))
            logger.info(f"  📍 Фильтр по району: '{district}'")
        
        # ✅ НОВОЕ: Поиск по списку назначений
        if filters.get("land_allowed_use_name_list"):
            purposes = filters["land_allowed_use_name_list"]
            conditions = [Listing.land_allowed_use_name.ilike(f"%{p}%") for p in purposes]
            query = query.filter(or_(*conditions))
            logger.info(f"  🎯 Фильтр по назначениям: {purposes}")
        
        # ✅ СТАРЫЙ: Точный поиск (для совместимости)
        elif filters.get("land_allowed_use_name"):
            use_name = filters["land_allowed_use_name"]
            query = query.filter(Listing.land_allowed_use_name.ilike(f"%{use_name}%"))
            logger.info(f"  🎯 Фильтр по назначению: '{use_name}'")
        
        if filters.get("start_price_max") is not None:
            max_price = filters["start_price_max"]
            query = query.filter(Listing.start_price <= max_price)
            logger.info(f"  💰 Фильтр по цене: до {max_price:,}₽")
        
        if filters.get("total_square_min") is not None:
            min_square = filters["total_square_min"]
            query = query.filter(Listing.total_square >= min_square)
            logger.info(f"  📐 Фильтр по площади: от {min_square} кв.м")
        
        if filters.get("total_square_max") is not None:
            max_square = filters["total_square_max"]
            query = query.filter(Listing.total_square <= max_square)
            logger.info(f"  📐 Фильтр по площади: до {max_square} кв.м")
        
        if filters.get("purchase_kind_name"):
            kind = filters["purchase_kind_name"]
            query = query.filter(Listing.purchase_kind_name.ilike(f"%{kind}%"))
            logger.info(f"  📝 Фильтр по типу сделки: '{kind}'")
        
        if filters.get("stage_state_name"):
            stage = filters["stage_state_name"]
            query = query.filter(Listing.stage_state_name.ilike(f"%{stage}%"))
            logger.info(f"  ⏱️ Фильтр по статусу: '{stage}'")
        
        query = query.order_by(Listing.start_price.asc(), Listing.total_square.desc())
        
        logger.debug(f"SQL: {query.statement.compile(compile_kwargs={'literal_binds': True})}")
        
        results = query.limit(10).all()
        return results
    
    def _normalize_city(self, city: str) -> str:
        """Нормализация названия города"""
        city_map = {
            "ступин": "ступино",
            "мытищ": "мытищи",
            "люберц": "люберцы",
            "химк": "химки",
            "королёв": "королев",
            "королев": "королёв",
            "подольск": "подольск",
            "балаших": "балашиха",
            "красногорск": "красногорск",
            "одинцов": "одинцово",
            "щёлков": "щёлково",
            "щелков": "щёлково",
            "орехов": "орехово",
            "электростал": "электросталь",
            "сергиев": "сергиев посад",
            "посад": "сергиев посад",
        }
        
        city_lower = city.lower().strip()
        for key, value in city_map.items():
            if key in city_lower:
                return value
        
        return city_lower
    
    def _smart_fallback_search(self, user_query: str) -> List[Listing]:
        """Умный fallback с анализом ключевых слов"""
        logger.info("🔧 Запуск умного fallback (без LLM)...")
        
        query_lower = user_query.lower()
        query = self.db.query(Listing).filter(Listing.is_active == True)
        
        # ✅ УЛУЧШЕНО: Используем PURPOSE_MAPPING
        found_purpose = False
        for keyword, db_purposes in PURPOSE_MAPPING.items():
            if keyword in query_lower:
                conditions = [Listing.land_allowed_use_name.ilike(f"%{p}%") for p in db_purposes]
                query = query.filter(or_(*conditions))
                logger.info(f"  🎯 Фильтр по ключу '{keyword}': {db_purposes}")
                found_purpose = True
                break
        
        if not found_purpose:
            logger.info("  ℹ️ Назначение не определено, ищем по всем объектам")
        
        cities = [
            "балашиха", "подольск", "химки", "королёв", "мытищи",
            "люберцы", "электросталь", "коломна", "красногорск", "одинцово",
            "серпухов", "щёлково", "орехово", "долгопрудн", "жуковск",
            "пушкино", "реутов", "сергиев посад", "сергиев", "посад", "воскресенск", "лобня",
            "клин", "ивантеевка", "дубна", "раменск", "домодедово",
            "ступино", "чехов", "фрязино", "лыткарино", "дзержинск"
        ]
        
        found_city = False
        for city in cities:
            normalized = self._normalize_city(city)
            if normalized in query_lower or city in query_lower:
                query = query.filter(
                    or_(
                        Listing.address_description.ilike(f"%{city}%"),
                        Listing.address_description.ilike(f"%{normalized}%"),
                        Listing.name.ilike(f"%{city}%"),
                        Listing.name.ilike(f"%{normalized}%")
                    )
                )
                logger.info(f"  📍 Фильтр по городу: {city}")
                found_city = True
                break
        
        found_price = False
        numbers = re.findall(r'\d+', query_lower)
        if numbers:
            max_num = max([int(n) for n in numbers])
            
            if "млн" in query_lower or "миллион" in query_lower:
                price = max_num * 1_000_000
            elif "тыс" in query_lower or "тысяч" in query_lower:
                price = max_num * 1_000
            else:
                if max_num > 100_000:
                    price = max_num
                else:
                    price = None
            
            if price:
                query = query.filter(Listing.start_price <= price)
                logger.info(f"  💰 Фильтр по цене: до {price:,}₽")
                found_price = True
        
        # ✅ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Если ничего не определено - вернуть пустой список
        if not found_purpose and not found_city and not found_price:
            logger.warning("  ⚠️ Не удалось определить параметры поиска - возвращаю пустой результат")
            return []
        
        query = query.order_by(Listing.start_price.asc())
        
        logger.debug(f"SQL: {query.statement.compile(compile_kwargs={'literal_binds': True})}")
        
        results = query.limit(10).all()
        
        if results:
            logger.info(f"  ✅ Умный fallback нашел {len(results)} объектов")
        else:
            logger.warning("  ⚠️ Умный fallback не дал результатов")
        
        return results
    
    def _fallback_search_relaxed(self, original_filters: Dict[str, Any]) -> List[Listing]:
        """Ослабление фильтров"""
        logger.info("🔧 Запуск fallback с ослабленными фильтрами...")
        
        relaxed_filters = {}
        
        if original_filters.get("district_code"):
            relaxed_filters["district_code"] = original_filters["district_code"]
        
        # ✅ Сохраняем список назначений
        if original_filters.get("land_allowed_use_name_list"):
            relaxed_filters["land_allowed_use_name_list"] = original_filters["land_allowed_use_name_list"]
        elif original_filters.get("land_allowed_use_name"):
            relaxed_filters["land_allowed_use_name"] = original_filters["land_allowed_use_name"]
        
        if original_filters.get("start_price_max"):
            original_price = original_filters["start_price_max"]
            relaxed_filters["start_price_max"] = int(original_price * 1.5)
            logger.info(f"  💰 Цена увеличена: {original_price:,}₽ → {relaxed_filters['start_price_max']:,}₽")
        
        logger.info("  📐 Убраны фильтры по площади")
        
        results = self._execute_search(relaxed_filters)
        
        if results:
            logger.info(f"  ✅ Fallback успешен: найдено {len(results)} объектов")
        else:
            logger.warning("  ⚠️ Даже с ослабленными фильтрами ничего не найдено")
        
        return results
    
    def get_search_suggestions(self, user_query: str) -> List[str]:
        """Генерация подсказок"""
        suggestions = []
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ["соток", "га", "кв.м", "площад"]):
            suggestions.append("Попробуйте расширить диапазон площади")
        
        if any(word in query_lower for word in ["млн", "тыс", "рубл", "цен"]):
            suggestions.append("Попробуйте увеличить максимальную цену на 20-30%")
        
        suggestions.extend([
            "Укажите более широкий район",
            "Уберите часть критериев из запроса"
        ])
        
        return suggestions[:3]
    
    def test_llm_connection(self) -> bool:
        """Проверка LLM"""
        if not self.llm_enabled or self.llm_client is None:
            logger.warning("⚠️ LLM клиент не инициализирован")
            return False
        
        try:
            result = self.llm_client.test_connection()
            if result:
                logger.info("✅ LLM клиент работает корректно")
            else:
                logger.error("❌ LLM клиент не отвечает")
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке LLM: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Статистика БД"""
        total = self.db.query(Listing).filter(Listing.is_active == True).count()
        
        stats = {
            "total_listings": total,
            "with_price": self.db.query(Listing).filter(
                and_(Listing.is_active == True, Listing.start_price > 0)
            ).count(),
            "land_plots": self.db.query(Listing).filter(
                and_(Listing.is_active == True, Listing.land_allowed_use_name.isnot(None))
            ).count()
        }
        
        logger.info(f"📊 Статистика БД: {stats}")
        return stats