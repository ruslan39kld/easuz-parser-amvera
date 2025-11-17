# src/parser/update_html_data.py
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.parser.scraper import EasuzParser
from src.database.session import get_db
from src.database.models import Listing

def update_existing_listings(batch_size=10):
    parser = EasuzParser()
    db = next(get_db())
    
    try:
        # Получаем все записи без direct_url или cadastral_number
        listings = db.query(Listing).filter(
            (Listing.direct_url == "") | (Listing.cadastral_number == "")
        ).limit(batch_size).all()
        
        print(f"Найдено {len(listings)} записей для обновления")
        
        for listing in listings:
            print(f"Обновляю ID {listing.id} (registry: {listing.registry_number})")
            # Создаём временный объект LandListing для парсера
            from src.parser.models import LandListing
            temp_obj = {
                'id': listing.id,
                'registryNumber': listing.registry_number,
                'name': listing.name,
                'startPrice': listing.start_price,
                'totalSquare': listing.total_square,
                'addressDescription': listing.address_description,
                'objectPurchases': [{'totalSquare': listing.total_square}],
                'photos': []
            }
            land_listing = parser._parse_listing(temp_obj, fetch_html=True)
            
            # Обновляем поля в БД
            listing.direct_url = land_listing.direct_url
            listing.full_address = land_listing.full_address
            listing.object_type = land_listing.object_type
            listing.cadastral_number = land_listing.cadastral_number
            
            print(f"  → URL: {listing.direct_url[:50]}...")
            print(f"  → Кадастр: {listing.cadastral_number}")
        
        db.commit()
        print("✅ Обновление завершено")
    finally:
        db.close()

if __name__ == "__main__":
    update_existing_listings(batch_size=20)  # Обновить 20 записей за раз