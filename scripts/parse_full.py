"""Спарсить ВСЕ объявления с сайта"""
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from parser import EasuzParser
from database import Database

def main():
    print("="*60)
    print("ПОЛНЫЙ ПАРСИНГ ВСЕХ ОБЪЯВЛЕНИЙ С ЕАСУЗ")
    print("="*60)
    
    parser = EasuzParser()
    db = Database()
    db.create_tables()
    
    # Получаем общее количество
    print("\n🔍 Получение информации о количестве объявлений...")
    _, pagination = parser.get_page(page=1, per_page=50)
    
    total_count = pagination.get('countTotal', 0)
    total_pages = pagination.get('pageCount', 0)
    
    print(f"\n📊 На сайте:")
    print(f"   Всего объявлений: {total_count}")
    print(f"   Всего страниц: {total_pages}")
    
    # Спрашиваем подтверждение
    print(f"\n⏱️  Примерное время: ~{total_pages // 2} секунд (~{total_pages // 60 + 1} минут)")
    response = input("\nНачать полный парсинг? (да/нет): ")
    
    if response.lower() not in ['да', 'yes', 'y', 'д']:
        print("Отменено")
        return
    
    print("\n" + "="*60)
    print("ПАРСИНГ...")
    print("="*60 + "\n")
    
    all_listings = []
    page = 1
    errors = 0
    
    while page <= total_pages:
        print(f"[{page}/{total_pages}] ", end='', flush=True)
        
        try:
            listings, _ = parser.get_page(page=page, per_page=50)
            
            if not listings:
                print("✗ нет данных")
                errors += 1
                if errors > 5:
                    print("\n❌ Слишком много ошибок, останавливаемся")
                    break
                page += 1
                continue
            
            all_listings.extend(listings)
            print(f"✓ {len(listings)} объявлений (всего: {len(all_listings)})")
            errors = 0  # Сбрасываем счетчик ошибок
            
            # Сохраняем каждые 100 объявлений
            if len(all_listings) >= 100:
                print(f"   💾 Сохранение...", end=' ', flush=True)
                saved = db.save_many(all_listings)
                print(f"✓ {saved}")
                all_listings = []
            
            page += 1
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Прервано пользователем")
            break
        except Exception as e:
            print(f"✗ ошибка: {e}")
            errors += 1
            page += 1
    
    # Сохраняем остаток
    if all_listings:
        print(f"\n💾 Сохранение последних {len(all_listings)}...", end=' ', flush=True)
        saved = db.save_many(all_listings)
        print(f"✓ {saved}")
    
    print("\n" + "="*60)
    print("✅ ПАРСИНГ ЗАВЕРШЕН!")
    print("="*60)
    
    stats = db.get_stats()
    print(f"\n📈 Статистика БД:")
    print(f"   Всего: {stats['total']}")
    print(f"   Активных: {stats['active']}")

if __name__ == "__main__":
    main()