import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.parser.scraper import EasuzParser
from src.database.session import get_db
from src.database.models import Listing

# Укажите registry_number того лота, который нужно обновить
REGISTRY_NUMBER_TO_UPDATE = "00300060115281"

def manual_update():
    print(f"🔧 Ручное обновление лота {REGISTRY_NUMBER_TO_UPDATE}...")
    parser = EasuzParser()
    db = next(get_db())

    try:
        # Получаем данные по registry_number (через API)
        listings, _ = parser.get_page(page=1, per_page=1, registry_number=REGISTRY_NUMBER_TO_UPDATE)

        if not listings:
            print("❌ Лот не найден в API.")
            return

        land_listing = listings[0]
        print(f"✅ Найден лот: {land_listing.name}")

        # Находим запись в БД
        db_listing = db.query(Listing).filter_by(registry_number=land_listing.registry_number).first()

        if not db_listing:
            print("❌ Запись не найдена в базе данных.")
            return

        # Обновляем все поля (кроме id!)
        db_listing.name = land_listing.name
        db_listing.registry_number = land_listing.registry_number
        db_listing.start_price = land_listing.start_price
        db_listing.total_square = land_listing.total_square
        db_listing.address_description = land_listing.address_description
        db_listing.land_allowed_use_name = land_listing.land_allowed_use_name
        db_listing.purchase_kind_name = land_listing.purchase_kind_name
        db_listing.stage_state_name = land_listing.stage_state_name
        db_listing.full_address = land_listing.full_address
        db_listing.direct_url = land_listing.direct_url
        db_listing.object_type = land_listing.object_type
        db_listing.cadastral_number = land_listing.cadastral_number
        db_listing.is_active = True

        db.merge(db_listing)
        db.commit()

        print(f"🎉 Лот {REGISTRY_NUMBER_TO_UPDATE} успешно обновлен!")
        print(f"🔗 Прямая ссылка: {db_listing.direct_url}")
        print(f"🔢 Кадастровый номер: {db_listing.cadastral_number}")
        print(f"📍 Полный адрес: {db_listing.full_address}")

    except Exception as e:
        print(f"❌ Ошибка при обновлении: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    manual_update()