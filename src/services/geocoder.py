# src/services/geocoder.py
# Сервис для геокодирования адресов через Яндекс.Карты API

import requests
import logging
from typing import Optional, Tuple
from config.settings import settings

logger = logging.getLogger(__name__)


class YandexGeocoder:
    """Геокодирование адресов через Яндекс.Карты API"""
    
    BASE_URL = "https://geocode-maps.yandex.ru/1.x/"
    
    def __init__(self):
        self.api_key = settings.YANDEX_GEOCODER_API_KEY
        if not self.api_key:
            logger.warning("⚠️ YANDEX_GEOCODER_API_KEY не установлен")
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Преобразование адреса в координаты
        
        Args:
            address: Адрес для геокодирования (например: "Красногорск, ул. Строителей 1")
        
        Returns:
            Кортеж (latitude, longitude) или None при ошибке
        """
        if not self.api_key:
            logger.error("❌ API ключ Яндекс.Карт не настроен")
            return None
        
        logger.info(f"🔍 Геокодирование адреса: '{address}'")
        
        params = {
            "apikey": self.api_key,
            "geocode": address,
            "format": "json",
            "results": 1
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Извлекаем координаты из ответа
            try:
                geo_object = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                coordinates = geo_object["Point"]["pos"]
                
                # Формат Яндекса: "longitude latitude"
                lon, lat = map(float, coordinates.split())
                
                logger.info(f"✅ Найдены координаты: {lat:.6f}, {lon:.6f}")
                return (lat, lon)
                
            except (KeyError, IndexError) as e:
                logger.error(f"❌ Адрес не найден: {address}")
                return None
        
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка при запросе к Яндекс.Карты API: {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Преобразование координат в адрес (обратное геокодирование)
        
        Args:
            latitude: Широта
            longitude: Долгота
        
        Returns:
            Адрес или None при ошибке
        """
        if not self.api_key:
            logger.error("❌ API ключ Яндекс.Карт не настроен")
            return None
        
        logger.info(f"🔍 Обратное геокодирование: {latitude}, {longitude}")
        
        params = {
            "apikey": self.api_key,
            "geocode": f"{longitude},{latitude}",  # Яндекс использует lon,lat
            "format": "json",
            "results": 1
        }
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            try:
                geo_object = data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                address = geo_object["metaDataProperty"]["GeocoderMetaData"]["text"]
                
                logger.info(f"✅ Найден адрес: {address}")
                return address
                
            except (KeyError, IndexError):
                logger.error(f"❌ Адрес не найден для координат: {latitude}, {longitude}")
                return None
        
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка при запросе к Яндекс.Карты API: {e}")
            return None