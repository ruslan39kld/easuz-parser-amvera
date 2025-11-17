# src/llm/prompt_engine.py
import json
import re
import logging
from typing import Dict, Any, Optional

from src.bot_messages import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class SearchPromptEngine:
    
    # Официальные категории для нормализации (страховка если LLM ошибся)
    PURPOSE_MAPPING = {
        "ижс": "Для индивидуального жилищного строительства",
        "под дом": "Для индивидуального жилищного строительства",
        "для дома": "Для индивидуального жилищного строительства",
        "жилой дом": "Для индивидуального жилищного строительства",
        "индивидуальное жилищное строительство": "Для индивидуального жилищного строительства",
        
        "лпх": "Для ведения личного подсобного хозяйства",
        "личное подсобное": "Для ведения личного подсобного хозяйства",
        "личное подсобное хозяйство": "Для ведения личного подсобного хозяйства",
        
        "кфх": "Для крестьянского (фермерского) хозяйства",
        "фермерское": "Для крестьянского (фермерского) хозяйства",
        "ферма": "Для крестьянского (фермерского) хозяйства",
        "крестьянское хозяйство": "Для крестьянского (фермерского) хозяйства",
        
        "сельхоз": "Для сельскохозяйственного производства",
        "сельское хозяйство": "Для сельскохозяйственного производства",
        "сельскохозяйственное производство": "Для сельскохозяйственного производства",
        
        "бизнес": "Для размещения объектов торговли, общественного питания и бытового обслуживания",
        "коммерция": "Для размещения объектов торговли, общественного питания и бытового обслуживания",
        "магазин": "Для размещения объектов торговли, общественного питания и бытового обслуживания",
        "офис": "Для размещения объектов торговли, общественного питания и бытового обслуживания",
        "торговля": "Для размещения объектов торговли, общественного питания и бытового обслуживания",
    }
    
    @staticmethod
    def generate_search_prompt(user_query: str) -> str:
        """
        Генерирует детальный промпт для извлечения параметров поиска.
        Включает четкую схему JSON и правила нормализации.
        """
        prompt = f"""
Извлеки параметры из запроса пользователя и верни их СТРОГО в формате JSON.

**ОБЯЗАТЕЛЬНАЯ СХЕМА JSON:**
{{
  "location": "название города/района без сокращений",
  "purpose": "полное официальное название категории земли",
  "max_price": число в рублях,
  "min_area": число в кв.м,
  "max_area": число в кв.м
}}

**ПРАВИЛА НОРМАЛИЗАЦИИ:**

1. **location** - полное название БЕЗ сокращений:
   ✅ "Ступино", "Химки", "Одинцовский городской округ"
   ❌ "г. Ступино", "г.о. Химки", "м.р. Одинцово"

2. **purpose** - ПЕРЕВОДИ сокращения в официальные формулировки:
   • "ИЖС", "под дом" → "Для индивидуального жилищного строительства"
   • "ЛПХ" → "Для ведения личного подсобного хозяйства"
   • "КФХ", "фермерское" → "Для крестьянского (фермерского) хозяйства"
   • "сельхоз" → "Для сельскохозяйственного производства"
   • "бизнес", "коммерция" → "Для размещения объектов торговли, общественного питания и бытового обслуживания"

3. **Цены и площади** - только числа в базовых единицах:
   • "до 2 млн" → "max_price": 2000000
   • "от 10 соток" → "min_area": 1000 (1 сотка = 100 кв.м)
   • "5 га" → 50000 (1 га = 10000 кв.м)
   • ВСЕГДА ПЕРЕВОДИ В КВ.М!

**ВАЖНО:**
- Если параметр НЕ указан — НЕ ВКЛЮЧАЙ его в JSON
- НЕ ПРИДУМЫВАЙ данные
- Ответ должен содержать ТОЛЬКО валидный JSON, без текста до/после
- Никаких объяснений, никаких ```json блоков

**Запрос пользователя:**
"{user_query}"

**Твой ответ (только JSON):**
"""
        return prompt.strip()
    
    @staticmethod
    def build_llm_messages(user_query: str) -> list[dict[str, str]]:
        """Формирует список сообщений для LLM с системным промптом."""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": SearchPromptEngine.generate_search_prompt(user_query)}
        ]
    
    @staticmethod
    def _normalize_purpose(raw_purpose: str) -> str:
        """
        Нормализует назначение земли через словарь.
        Используется как страховка если LLM вернул сокращение.
        """
        normalized = raw_purpose.strip().lower()
        return SearchPromptEngine.PURPOSE_MAPPING.get(normalized, raw_purpose)
    
    @staticmethod
    def _clean_location(location: str) -> str:
        """
        Агрессивно очищает название локации от всех возможных сокращений.
        Обрабатывает: "г. Ступино", "Ступино г.", "город Химки", "пос. Томилино".
        """
        # Убираем сокращения в любом месте строки
        location = re.sub(
            r'\s*(г\.|г\.о\.|м\.р\.|пос\.|д\.|с\.|город|район|поселок|деревня|село)\s*',
            ' ',
            location,
            flags=re.IGNORECASE
        )
        # Убираем лишние пробелы
        location = re.sub(r'\s+', ' ', location).strip()
        return location
    
    @staticmethod
    def _parse_numeric_value(value: Any, field_name: str, original_query: str = "") -> Optional[float]:
        """
        Парсит числовое значение с обработкой:
        - Строк типа "2000000 руб"
        - Единиц измерения: сотки → *100, га → *10000
        
        Args:
            value: значение для парсинга
            field_name: имя поля (для логов)
            original_query: оригинальный запрос пользователя (для определения единиц)
        """
        if value is None:
            return None
        
        # Если уже число
        if isinstance(value, (int, float)):
            numeric_value = float(value)
        elif isinstance(value, str):
            # Убираем все кроме цифр, точки и минуса
            cleaned = re.sub(r'[^\d.-]', '', value)
            if not cleaned:
                logger.warning(f"Не удалось извлечь число из {field_name}: '{value}'")
                return None
            try:
                numeric_value = float(cleaned)
            except ValueError:
                logger.warning(f"Не удалось извлечь число из {field_name}: '{value}'")
                return None
        else:
            logger.warning(f"Неожиданный тип данных для {field_name}: {type(value)}")
            return None
        
        # Обработка единиц измерения для площадей
        if field_name in ["min_area", "max_area"]:
            original_lower = original_query.lower()
            
            # Проверяем наличие "соток" в исходном запросе
            if "соток" in original_lower or "сотка" in original_lower or "сотки" in original_lower:
                # Если число маленькое (< 1000) — вероятно в сотках
                if numeric_value < 1000:
                    logger.info(f"Обнаружены сотки в запросе. Умножаю {numeric_value} на 100")
                    numeric_value *= 100
            
            # Проверяем наличие "га" в исходном запросе
            elif "га" in original_lower or "гектар" in original_lower:
                # Если число маленькое (< 100) — вероятно в гектарах
                if numeric_value < 100:
                    logger.info(f"Обнаружены гектары в запросе. Умножаю {numeric_value} на 10000")
                    numeric_value *= 10000
        
        return numeric_value
    
    @staticmethod
    def parse_llm_response(response: str, original_query: str = "") -> Optional[Dict[str, Any]]:
        """
        Парсит JSON из ответа LLM с агрессивной очисткой и валидацией.
        
        Args:
            response: ответ от LLM
            original_query: оригинальный запрос пользователя (для контекста)
        
        Обрабатывает:
        - Markdown блоки ```json
        - Текст до/после JSON
        - Переносы строк
        - Нормализует назначения через PURPOSE_MAPPING
        - Обрабатывает единицы измерения (сотки, га)
        - Очищает location от сокращений
        - Округляет площади
        - Валидирует извлеченные данные
        """
        if not response:
            logger.warning("LLM вернул пустой ответ")
            return None
        
        original_response = response
        
        # Шаг 1: Удаляем markdown блоки
        response = re.sub(r"```(?:json)?\s*", "", response)
        response = re.sub(r"```\s*", "", response)
        
        # Шаг 2: Ищем JSON объект в тексте (между { и })
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
        if json_match:
            response = json_match.group(0)
        
        response = response.strip()
        
        # Логируем для отладки
        logger.info(f"Очищенный ответ LLM (первые 200 символов): {response[:200]}")
        
        try:
            data = json.loads(response)
            filters = {}
            
            # Извлекаем и валидируем location
            if "location" in data and data["location"]:
                location = str(data["location"]).strip()
                # Агрессивная очистка от ВСЕХ сокращений
                location = SearchPromptEngine._clean_location(location)
                filters["district_code"] = location
                logger.info(f"✓ Извлечен location: '{location}'")
            
            # Извлекаем и нормализуем purpose
            if "purpose" in data and data["purpose"]:
                raw_purpose = str(data["purpose"]).strip()
                # Применяем нормализацию через словарь (страховка)
                purpose = SearchPromptEngine._normalize_purpose(raw_purpose)
                filters["land_allowed_use_name"] = purpose
                
                if purpose != raw_purpose:
                    logger.info(f"✓ Purpose нормализован: '{raw_purpose}' → '{purpose}'")
                else:
                    logger.info(f"✓ Извлечен purpose: '{purpose}'")
            
            # Извлекаем max_price
            if "max_price" in data:
                max_price = SearchPromptEngine._parse_numeric_value(
                    data["max_price"], 
                    "max_price",
                    original_query
                )
                if max_price is not None and max_price > 0:
                    filters["start_price_max"] = int(max_price)
                    logger.info(f"✓ Извлечен max_price: {int(max_price)} руб")
                elif max_price is not None:
                    logger.warning(f"⚠ max_price <= 0: {max_price}")
            
            # Извлекаем min_area с обработкой единиц и округлением
            if "min_area" in data:
                min_area = SearchPromptEngine._parse_numeric_value(
                    data["min_area"], 
                    "min_area",
                    original_query
                )
                if min_area is not None and min_area > 0:
                    # Округляем до целого
                    filters["total_square_min"] = int(round(min_area))
                    logger.info(f"✓ Извлечен min_area: {int(round(min_area))} кв.м")
                elif min_area is not None:
                    logger.warning(f"⚠ min_area <= 0: {min_area}")
            
            # Извлекаем max_area с обработкой единиц и округлением
            if "max_area" in data:
                max_area = SearchPromptEngine._parse_numeric_value(
                    data["max_area"], 
                    "max_area",
                    original_query
                )
                if max_area is not None and max_area > 0:
                    filters["total_square_max"] = int(round(max_area))
                    logger.info(f"✓ Извлечен max_area: {int(round(max_area))} кв.м")
                elif max_area is not None:
                    logger.warning(f"⚠ max_area <= 0: {max_area}")
            
            # Валидация: min_area <= max_area
            if ("total_square_min" in filters and 
                "total_square_max" in filters and 
                filters["total_square_min"] > filters["total_square_max"]):
                logger.warning(
                    f"⚠ min_area > max_area ({filters['total_square_min']} > {filters['total_square_max']}). Меняю местами."
                )
                filters["total_square_min"], filters["total_square_max"] = \
                    filters["total_square_max"], filters["total_square_min"]
            
            if filters:
                logger.info(f"✅ Итоговые фильтры: {filters}")
                return filters
            else:
                logger.warning("⚠ Не удалось извлечь ни одного параметра из ответа LLM")
                return None
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка парсинга JSON: {e}")
            logger.error(f"Оригинальный ответ LLM: {original_response[:500]}")
            logger.error(f"После очистки: {response[:500]}")
            return None
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"❌ Ошибка обработки данных: {e}")
            logger.error(f"Ответ LLM: {original_response[:500]}")
            return None