import requests
import time
from typing import List, Dict, Optional
from parser.models import LandListing

class EasuzParser:
    """Парсер для сайта ЕАСУЗ"""
    
    BASE_URL = "https://easuz.mosreg.ru"
    API_URL = f"{BASE_URL}/api/v1-web/Purchase/GetPurchasePage"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{self.BASE_URL}/torgi/land'
        })
    
    def _make_request(self, payload: Dict) -> Optional[Dict]:
        """Выполнить запрос к API"""
        try:
            response = self.session.post(
                self.API_URL, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка запроса: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Ошибка: {e}")
            return None
    
    def _parse_listing(self, obj: Dict) -> LandListing:
        """Парсинг одного объявления"""
        
        # Получаем данные об участке
        obj_purchase = obj.get('objectPurchases', [{}])[0]
        obj_char = obj_purchase.get('objectCharacteristics', [{}])[0]
        
        # Фотографии
        photos = [photo['url'] for photo in obj.get('photos', [])]
        
        return LandListing(
            id=obj['id'],
            name=obj['name'],
            registry_number=obj.get('registryNumber', ''),
            start_price=obj.get('startPrice', 0),
            deposit_amount=obj.get('depositAmount', 0),
            start_step_amount=obj.get('startStepAmount', 0),
            total_square=obj_purchase.get('totalSquare', 0),
            address_description=obj.get('addressDescription', ''),
            latitude=obj.get('latitude'),
            longitude=obj.get('longitude'),
            district_code=obj.get('districtCode'),
            right_term_use_year=obj.get('rightTermUseYear'),
            right_term_use_month=obj.get('rightTermUseMonth'),
            purchase_kind_name=obj.get('purchaseKind', {}).get('name', ''),
            purchase_form_name=obj.get('purchaseForm', {}).get('name', ''),
            stage_state_name=obj.get('stageState', {}).get('name', ''),
            land_allowed_use_name=obj_char.get('landAllowedUseName', ''),
            accept_plan_end_date=obj.get('acceptPlanEndDate'),
            review_plan_end_date=obj.get('reviewPlanEndDate'),
            count_views=obj.get('countViews', 0),
            photos=photos
        )
    
    def get_page(self, page: int = 1, per_page: int = 10) -> tuple[List[LandListing], Dict]:
        """
        Получить одну страницу объявлений
        
        Returns:
            (listings, pagination_info)
        """
        payload = {
            "filter": {
                "purchaseStageState": [1000004]  # Торги объявлены
            },
            "page": page,
            "take": per_page,
            "orderByColumn": "Id",
            "orderByDescending": True
        }
        
        data = self._make_request(payload)
        
        if not data:
            return [], {}
        
        # Парсим объявления
        listings = []
        for obj in data.get('objects', []):
            try:
                listing = self._parse_listing(obj)
                listings.append(listing)
            except Exception as e:
                print(f"Ошибка парсинга объявления {obj.get('id')}: {e}")
        
        # Информация о пагинации
        pagination = data.get('pagination', {})
        
        return listings, pagination
    
    def get_all(self, max_pages: Optional[int] = None, delay: float = 1.0) -> List[LandListing]:
        """
        Получить все объявления со всех страниц
        
        Args:
            max_pages: Максимальное количество страниц (None = все)
            delay: Задержка между запросами в секундах
        """
        all_listings = []
        page = 1
        
        print(f"Начинаем парсинг...")
        
        while True:
            print(f"Страница {page}...", end=' ')
            
            listings, pagination = self.get_page(page=page, per_page=50)
            
            if not listings:
                print("Нет данных")
                break
            
            all_listings.extend(listings)
            
            total_pages = pagination.get('pageCount', 0)
            total_count = pagination.get('countTotal', 0)
            
            print(f"Получено {len(listings)} объявлений. Всего: {len(all_listings)}/{total_count}")
            
            # Проверяем условия выхода
            if page >= total_pages:
                break
            
            if max_pages and page >= max_pages:
                print(f"Достигнут лимит страниц: {max_pages}")
                break
            
            page += 1
            time.sleep(delay)  # Задержка между запросами
        
        print(f"\nПарсинг завершен! Всего объявлений: {len(all_listings)}")
        return all_listings
    
    def search(self, 
               query: Optional[str] = None,
               price_from: Optional[float] = None,
               price_to: Optional[float] = None,
               area_from: Optional[float] = None,
               area_to: Optional[float] = None) -> List[LandListing]:
        """
        Поиск объявлений с фильтрами
        
        Args:
            query: Текстовый поиск (адрес, район)
            price_from: Цена от
            price_to: Цена до
            area_from: Площадь от
            area_to: Площадь до
        """
        payload = {
            "filter": {
                "purchaseStageState": [1000004]
            },
            "page": 1,
            "take": 50,
            "query": query,
            "orderByColumn": "Id",
            "orderByDescending": True
        }
        
        data = self._make_request(payload)
        
        if not data:
            return []
        
        # Парсим объявления
        listings = []
        for obj in data.get('objects', []):
            try:
                listing = self._parse_listing(obj)
                
                # Фильтрация по цене
                if price_from and listing.start_price < price_from:
                    continue
                if price_to and listing.start_price > price_to:
                    continue
                
                # Фильтрация по площади
                if area_from and listing.total_square < area_from:
                    continue
                if area_to and listing.total_square > area_to:
                    continue
                
                listings.append(listing)
                
            except Exception as e:
                print(f"Ошибка парсинга: {e}")
        
        return listings