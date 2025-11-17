#!/usr/bin/env python3
"""
Скрипт для проверки БД - запускайте это ДО запуска бота
Использование: python check_db_amvera.py
"""

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def check_db():
    """Проверка БД"""
    try:
        logger.info("=" * 80)
        logger.info("🔍 ПРОВЕРКА БАЗЫ ДАННЫХ")
        logger.info("=" * 80)
        
        # Проверяем файл БД
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'easuz.db')
        logger.info(f"📂 Путь к БД: {db_path}")
        logger.info(f"✅ Файл существует: {os.path.exists(db_path)}")
        
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            size_mb = size_bytes / 1024 / 1024
            logger.info(f"📊 Размер файла: {size_mb:.2f} MB ({size_bytes:,} байт)")
        else:
            logger.error("❌ КРИТИЧНО: Файл БД не найден!")
            logger.info("\n📁 Содержимое папки data:")
            data_dir = os.path.join(os.path.dirname(__file__), 'data')
            if os.path.exists(data_dir):
                for item in os.listdir(data_dir):
                    item_path = os.path.join(data_dir, item)
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path)
                        logger.info(f"   - {item} ({size:,} байт)")
                    else:
                        logger.info(f"   - {item}/ (папка)")
            else:
                logger.error("   Папка data/ не существует!")
            return False
        
        # Подключаемся к БД
        from src.database.database import SessionLocal
        from src.database.models import Listing
        
        db = SessionLocal()
        
        # Проверяем записи
        total = db.query(Listing).count()
        logger.info(f"📊 Всего записей: {total}")
        
        active = db.query(Listing).filter(Listing.is_active == True).count()
        logger.info(f"✅ Активных записей: {active}")
        
        if active > 0:
            sample = db.query(Listing).filter(Listing.is_active == True).first()
            logger.info("\n📌 Пример записи:")
            logger.info(f"   ID: {sample.id}")
            logger.info(f"   Название: {sample.name[:80]}")
            if sample.address_description:
                logger.info(f"   Адрес: {sample.address_description[:80]}")
            logger.info(f"   Назначение: {sample.land_allowed_use_name}")
            logger.info(f"   Цена: {sample.start_price:,}₽")
        
        db.close()
        
        logger.info("=" * 80)
        logger.info("✅ ПРОВЕРКА ЗАВЕРШЕНА УСПЕШНО")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"\n❌ ОШИБКА: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = check_db()
    sys.exit(0 if success else 1)