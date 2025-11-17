# scripts/view_db.py
# Скрипт для просмотра содержимого базы данных

import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.session import get_db
from src.database.models import Listing
from sqlalchemy import func

def view_database():
    """Просмотр статистики базы данных"""
    print("=" * 80)
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("=" * 80)
    
    with next(get_db()) as db:
        # Общее количество объявлений
        total = db.query(Listing).count()
        print(f"\n📋 Всего объявлений: {total}")
        
        # Активные объявления
        active = db.query(Listing).filter(Listing.is_active == True).count()
        print(f"✅ Активных: {active}")
        
        # Неактивные
        inactive = total - active
        print(f"❌ Неактивных: {inactive}")
        
        if total == 0:
            print("\n⚠️  База данных ПУСТАЯ!")
            print("\n💡 Запустите парсер для заполнения базы:")
            print("   py -3.11 scripts/parse_all.py")
            return
        
        # Статистика по назначению
        print("\n" + "=" * 80)
        print("🏷️  ПО НАЗНАЧЕНИЯМ:")
        print("=" * 80)
        
        purposes = db.query(
            Listing.land_allowed_use_name,
            func.count(Listing.id).label('count')
        ).filter(
            Listing.is_active == True
        ).group_by(
            Listing.land_allowed_use_name
        ).order_by(
            func.count(Listing.id).desc()
        ).limit(10).all()
        
        for purpose, count in purposes:
            purpose_name = purpose if purpose else "Не указано"
            print(f"  • {purpose_name[:60]}: {count}")
        
        # Примеры объявлений
        print("\n" + "=" * 80)
        print("📌 ПРИМЕРЫ ОБЪЯВЛЕНИЙ:")
        print("=" * 80)
        
        examples = db.query(Listing).filter(
            Listing.is_active == True
        ).limit(5).all()
        
        for i, listing in enumerate(examples, 1):
            print(f"\n{i}. {listing.name[:70]}")
            print(f"   💰 Цена: {int(listing.start_price):,} ₽")
            print(f"   📏 Площадь: {int(listing.total_square) if listing.total_square else 0} кв.м")
            address = listing.address_description or "Не указан"
            print(f"   📍 Адрес: {address[:60]}")
            
            # Кадастровый номер
            cadastral = listing.cadastral_number or "Не указан"
            print(f"   🆔 Кадастр: {cadastral}")
            
            # Назначение
            purpose = listing.land_allowed_use_name or "Не указано"
            print(f"   🏷️  Назначение: {purpose[:60]}")
            
            # Ссылка на ЕАСУЗ
            if listing.direct_url and listing.direct_url.strip():
                easuz_link = listing.direct_url
            elif listing.registry_number and listing.registry_number.strip():
                easuz_link = f"https://easuz.mosreg.ru/torgi/purchase/{listing.registry_number}"
            else:
                easuz_link = "Не указана"
            print(f"   🔗 ЕАСУЗ: {easuz_link[:70]}")
    
    print("\n" + "=" * 80)
    print("✅ Просмотр завершен")
    print("=" * 80)

if __name__ == "__main__":
    view_database()