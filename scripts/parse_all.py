"""Спарсить все объявления и сохранить в БД"""
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from parser import EasuzParser
from database import Database

def main():
    print("=== ПАРСИНГ И СОХРАНЕНИЕ В БД ===\n")
    
    parser = EasuzParser()
    db = Database()
    
    # Создаем таблицы если их нет
    db.create_tables()
    
    # Парсим первые 5 страниц для теста (250 объявлений)
    print("Парсинг первых 5 страниц (тест)...\n")
    
    all_listings = []
    for page in range(1, 6):
        print(f"Страница {page}...", end=' ', flush=True)
        
        listings, pagination = parser.get_page(page=page, per_page=50)
        
        if listings:
            all_listings.extend(listings)
            print(f"✓ получено {len(listings)} объявлений")
        else:
            print("✗ ошибка")
            break
        
        time.sleep(1)  # Задержка между запросами
    
    print(f"\n📊 Всего спарсено: {len(all_listings)} объявлений")
    print("\n💾 Сохранение в БД...", flush=True)
    
    saved = db.save_many(all_listings)
    
    print(f"\n✅ Сохранено: {saved} объявлений")
    
    # Статистика
    stats = db.get_stats()
    print(f"\n📈 Статистика БД:")
    print(f"  Всего записей: {stats['total']}")
    print(f"  Активных: {stats['active']}")
    print(f"  Неактивных: {stats['inactive']}")

if __name__ == "__main__":
    main()