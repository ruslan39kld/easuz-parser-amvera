"""
Полный перепарсинг всех данных с ЕАСУЗ с извлечением кадастровых номеров
"""
import sys
import time
import json
from datetime import datetime
from src.parser.scraper import EasuzParser
from src.database.session import get_db
from src.database.models import Listing

def parse_datetime(date_str):
    """Конвертирует ISO строку в datetime объект"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None

def main():
    print("🚀 Запуск полного перепарсинга данных с ЕАСУЗ...")
    print()
    
    parser = EasuzParser()
    db = next(get_db())
    
    total_saved = 0
    page = 1
    max_pages = 320  # Примерно 3200 записей / 10 = 320 страниц
    
    try:
        while page <= max_pages:
            print(f"📄 Загрузка страницы {page}/{max_pages} из ЕАСУЗ...")
            
            # Получаем данные с HTML-парсингом
            listings, pagination = parser.get_page(page=page, per_page=10, fetch_html=True)
            
            if not listings:
                print("✅ Больше нет данных для загрузки")
                break
            
            print(f"  → Получено {len(listings)} записей")
            
            # Сохраняем каждую запись
            for listing in listings:
                try:
                    # Проверяем существование записи
                    existing = db.query(Listing).filter(
                        Listing.registry_number == listing.registry_number
                    ).first()
                    
                    if existing:
                        # UPDATE существующей записи
                        existing.name = listing.name
                        existing.start_price = listing.start_price
                        existing.deposit_amount = listing.deposit_amount
                        existing.start_step_amount = listing.start_step_amount
                        existing.total_square = listing.total_square
                        existing.address_description = listing.address_description
                        existing.latitude = listing.latitude
                        existing.longitude = listing.longitude
                        existing.district_code = listing.district_code
                        existing.right_term_use_year = listing.right_term_use_year
                        existing.right_term_use_month = listing.right_term_use_month
                        existing.purchase_kind_name = listing.purchase_kind_name
                        existing.purchase_form_name = listing.purchase_form_name
                        existing.stage_state_name = listing.stage_state_name
                        existing.land_allowed_use_name = listing.land_allowed_use_name
                        existing.accept_plan_end_date = parse_datetime(listing.accept_plan_end_date)
                        existing.review_plan_end_date = parse_datetime(listing.review_plan_end_date)
                        existing.count_views = listing.count_views
                        existing.photos_json = json.dumps(listing.photos) if listing.photos else None
                        existing.full_address = listing.full_address
                        existing.direct_url = listing.direct_url
                        existing.object_type = listing.object_type
                        existing.cadastral_number = listing.cadastral_number
                    else:
                        # INSERT новой записи
                        db.add(listing)
                    
                    db.commit()
                    total_saved += 1
                    
                except Exception as e:
                    print(f"  ⚠️ Ошибка: {str(e)[:100]}")
                    db.rollback()
                    continue
            
            print(f"  ✅ Сохранено {len(listings)} записей (всего: {total_saved})")
            
            page += 1
            print("⏳ Пауза 2 сек...")
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print(f"\n📊 Итого обработано записей: {total_saved}")
        print("✅ Готово!")

if __name__ == "__main__":
    main()