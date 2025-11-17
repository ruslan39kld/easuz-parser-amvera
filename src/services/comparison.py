# src/services/comparison.py
from typing import List, Literal, Optional, Tuple
from src.database.models import Listing
from math import radians, cos, sin, asin, sqrt

CompareType = Literal["price", "area", "price_per_sqm", "distance"]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Расчет расстояния между двумя точками на Земле (формула Haversine)
    Возвращает расстояние в километрах
    """
    # Переводим в радианы
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Разница координат
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Формула Haversine
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Радиус Земли в километрах
    km = 6371 * c
    return km


class ComparisonService:
    """Сервис для сравнения объявлений"""

    @staticmethod
    def compare(listings: List[Listing], sort_by: CompareType, reverse: bool = False, 
                user_location: Optional[Tuple[float, float]] = None) -> List[Listing]:
        """
        Сортировка списка объявлений по выбранному параметру
        
        Args:
            listings: список объявлений
            sort_by: параметр сортировки (price, area, price_per_sqm, distance)
            reverse: обратная сортировка (от больших к меньшим)
            user_location: координаты пользователя (latitude, longitude) для сортировки по расстоянию
        """
        if not listings:
            return []

        if sort_by == "price":
            return sorted(listings, key=lambda x: x.start_price, reverse=reverse)
        
        elif sort_by == "area":
            return sorted(listings, key=lambda x: x.total_square or 0, reverse=reverse)
        
        elif sort_by == "price_per_sqm":
            # Считаем цену за кв.м, исключаем нулевую площадь
            def price_per_sqm(listing):
                if listing.total_square and listing.total_square > 0:
                    return listing.start_price / listing.total_square
                return float('inf')  # В конец списка
            
            return sorted(listings, key=price_per_sqm, reverse=reverse)
        
        elif sort_by == "distance":
            if not user_location:
                return listings  # Не можем сортировать без геопозиции
            
            user_lat, user_lon = user_location
            
            # Сортировка по расстоянию
            def distance_km(listing):
                if listing.latitude and listing.longitude:
                    return haversine(user_lat, user_lon, listing.latitude, listing.longitude)
                return float('inf')  # Без координат - в конец
            
            return sorted(listings, key=distance_km, reverse=reverse)
        
        return listings

    @staticmethod
    def format_comparison_table(listings: List[Listing], sort_by: CompareType, 
                                user_location: Optional[Tuple[float, float]] = None) -> str:
        """Форматирование результатов сравнения в виде таблицы"""
        if not listings:
            return "Нет данных для сравнения"

        medals = ["🥇", "🥈", "🥉"]
        result = "📊 <b>РЕЗУЛЬТАТЫ СРАВНЕНИЯ</b>\n\n"

        for i, listing in enumerate(listings, 1):
            medal = medals[i-1] if i <= 3 else f"{i}️⃣"
            
            # Краткое название
            short_name = listing.name[:50] + "..." if len(listing.name) > 50 else listing.name
            
            # Адрес
            address = listing.full_address or listing.address_description or "Адрес не указан"
            short_address = address.split(',')[0] if ',' in address else address[:30]
            
            # Основные параметры
            price_str = f"{int(listing.start_price):,} ₽"
            area_str = f"{int(listing.total_square) if listing.total_square else 0} м²"
            
            # Цена за м²
            if listing.total_square and listing.total_square > 0:
                price_per_sqm = int(listing.start_price / listing.total_square)
                price_per_sqm_str = f"{price_per_sqm:,} ₽/м²"
            else:
                price_per_sqm_str = "—"

            # Расстояние (если есть геопозиция)
            distance_str = ""
            if sort_by == "distance" and user_location and listing.latitude and listing.longitude:
                user_lat, user_lon = user_location
                distance = haversine(user_lat, user_lon, listing.latitude, listing.longitude)
                distance_str = f"\n📍 <b>{distance:.1f} км от вас</b>"

            result += (
                f"{medal} <b>Объявление {i}</b>\n"
                f"💰 {price_str} | 📏 {area_str}\n"
                f"💵 {price_per_sqm_str}{distance_str}\n"
                f"📍 {short_address}\n"
                f"🔗 <a href='{listing.direct_url or 'https://easuz.mosreg.ru'}'>Открыть</a>\n\n"
            )

        # Подсказка
        if sort_by == "price":
            result += "💡 <i>Отсортировано по цене (дешевые → дорогие)</i>"
        elif sort_by == "area":
            result += "💡 <i>Отсортировано по площади (меньше → больше)</i>"
        elif sort_by == "price_per_sqm":
            result += "💡 <i>Отсортировано по цене за м² (дешевле → дороже)</i>"
        elif sort_by == "distance":
            result += "💡 <i>Отсортировано по расстоянию (ближе → дальше)</i>"

        return result

    @staticmethod
    def get_best_recommendations(listings: List[Listing], user_location: Optional[Tuple[float, float]] = None) -> str:
        """Умные рекомендации на основе анализа"""
        if not listings:
            return ""

        # Находим лучшие варианты
        best_price = min(listings, key=lambda x: x.start_price)
        best_area = max(listings, key=lambda x: x.total_square or 0)
        
        # Лучшая цена за м²
        valid_listings = [l for l in listings if l.total_square and l.total_square > 0]
        if valid_listings:
            best_value = min(valid_listings, key=lambda x: x.start_price / x.total_square)
        else:
            best_value = None

        # Ближайший объект
        best_distance = None
        if user_location:
            user_lat, user_lon = user_location
            listings_with_coords = [l for l in listings if l.latitude and l.longitude]
            if listings_with_coords:
                best_distance = min(listings_with_coords, 
                                  key=lambda x: haversine(user_lat, user_lon, x.latitude, x.longitude))

        result = "\n\n💡 <b>УМНЫЕ РЕКОМЕНДАЦИИ:</b>\n\n"
        
        # Лучшая цена
        best_price_idx = listings.index(best_price) + 1
        result += f"🥇 <b>Лучшая цена:</b> Объявление {best_price_idx}\n"
        result += f"   {int(best_price.start_price):,} ₽\n\n"
        
        # Самый большой
        best_area_idx = listings.index(best_area) + 1
        result += f"🥇 <b>Самая большая площадь:</b> Объявление {best_area_idx}\n"
        result += f"   {int(best_area.total_square) if best_area.total_square else 0} м²\n\n"
        
        # Лучшее соотношение
        if best_value:
            best_value_idx = listings.index(best_value) + 1
            price_per_sqm = int(best_value.start_price / best_value.total_square)
            result += f"🥇 <b>Лучшее соотношение цена/площадь:</b> Объявление {best_value_idx}\n"
            result += f"   {price_per_sqm:,} ₽/м²\n\n"

        # Ближайший
        if best_distance:
            best_distance_idx = listings.index(best_distance) + 1
            distance = haversine(user_lat, user_lon, best_distance.latitude, best_distance.longitude)
            result += f"🥇 <b>Ближе всего к вам:</b> Объявление {best_distance_idx}\n"
            result += f"   {distance:.1f} км\n"

        return result