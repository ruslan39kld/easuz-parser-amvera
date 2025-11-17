import requests
import time
import json
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime
import re

def parse_datetime(date_str):
    """Конвертирует ISO строку в datetime объект"""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except:
        return None

class EasuzParser:
    """Парсер ЕАСУЗ с правильной структурой URL и парсингом HTML"""

    BASE_URL = "https://easuz.mosreg.ru"
    API_URL = f"{BASE_URL}/api/v1-web/Purchase/GetPurchasePage"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self._html_cache = {}

    def _make_request(self, payload: Dict) -> Optional[Dict]:
        try:
            response = self.session.post(self.API_URL, json=payload, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"❌ API ошибка: {e}")
            return None

    def _fetch_html_details(self, lot_id: int, category_code: str, district_code: str) -> Tuple[str, str, str]:
        """
        Парсит HTML-страницу лота
        URL: /torgi/{category}/{district_code}/{lot_id}/info
        Возвращает: (direct_url, full_address, cadastral_number)
        """
        cache_key = f"{lot_id}_{category_code}_{district_code}"
        if cache_key in self._html_cache:
            return self._html_cache[cache_key]

        try:
            category = "land" if category_code == "land" else "buildings"
            view_url = f"{self.BASE_URL}/torgi/{category}/{district_code}/{lot_id}/info"
            
            response = self.session.get(view_url, timeout=30, allow_redirects=True)

            if response.status_code != 200:
                result = ("", "", "")
                self._html_cache[cache_key] = result
                return result

            soup = BeautifulSoup(response.text, 'html.parser')
            direct_url = response.url
            full_address = ""
            cadastral_number = ""

            # Парсим список <li class="leftCol-list-li">
            for li in soup.find_all('li', class_='leftCol-list-li'):
                gray_span = li.find('span', class_='grayColor')
                black_span = li.find('span', class_='blackColor')
                
                if gray_span and black_span:
                    label = gray_span.get_text(strip=True)
                    value = black_span.get_text(strip=True)
                    
                    if 'Адрес' in label:
                        full_address = value
                    elif 'Кадастровый номер' in label:
                        cadastral_number = value

            result = (direct_url, full_address, cadastral_number)
            self._html_cache[cache_key] = result
            return result

        except Exception as e:
            print(f"  ❌ Ошибка HTML: {e}")
            result = ("", "", "")
            self._html_cache[cache_key] = result
            return result

    def _parse_listing(self, obj: Dict, fetch_html: bool = True) -> 'LandListing':
        obj_purchase = obj.get('objectPurchases', [{}])[0]
        obj_char = obj_purchase.get('objectCharacteristics', [{}])[0]
        photos = [photo['url'] for photo in obj.get('photos', [])]

        listing_data = {
            'id': obj['id'],
            'name': obj['name'],
            'registry_number': obj.get('registryNumber', ''),
            'start_price': obj.get('startPrice', 0),
            'deposit_amount': obj.get('depositAmount', 0),
            'start_step_amount': obj.get('startStepAmount', 0),
            'total_square': obj_purchase.get('totalSquare', 0),
            'address_description': obj.get('addressDescription', ''),
            'latitude': obj.get('latitude'),
            'longitude': obj.get('longitude'),
            'district_code': obj.get('districtCode'),
            'right_term_use_year': obj.get('rightTermUseYear'),
            'right_term_use_month': obj.get('rightTermUseMonth'),
            'purchase_kind_name': obj.get('purchaseKind', {}).get('name', ''),
            'purchase_form_name': obj.get('purchaseForm', {}).get('name', ''),
            'stage_state_name': obj.get('stageState', {}).get('name', ''),
            'land_allowed_use_name': obj_char.get('landAllowedUseName', ''),
            'accept_plan_end_date': parse_datetime(obj.get('acceptPlanEndDate')),
            'review_plan_end_date': parse_datetime(obj.get('reviewPlanEndDate')),
            'count_views': obj.get('countViews', 0),
            'photos_json': json.dumps(photos) if photos else None,
            'full_address': '',
            'direct_url': '',
            'object_type': '',
            'cadastral_number': '',
        }

        if fetch_html:
            lot_id = obj.get('id')
            category_code = obj.get('categoryCode', 'land')
            district_code = obj.get('districtCode', '')
            
            if lot_id and district_code:
                direct_url, full_address, cadastral = self._fetch_html_details(
                    lot_id, category_code, district_code
                )
                listing_data['direct_url'] = direct_url
                listing_data['full_address'] = full_address or obj.get('addressDescription', '')
                listing_data['object_type'] = category_code
                listing_data['cadastral_number'] = cadastral
            time.sleep(0.5)
        else:
            category = "land" if obj.get('categoryCode') == "land" else "buildings"
            district = obj.get('districtCode', '')
            listing_data['direct_url'] = f"{self.BASE_URL}/torgi/{category}/{district}/{obj['id']}/info"
            listing_data['full_address'] = obj.get('addressDescription', '')
            listing_data['object_type'] = obj.get('categoryCode', '')

        from src.database.models import Listing
        return Listing(**listing_data)

    def get_page(self, page: int = 1, per_page: int = 10, fetch_html: bool = False) -> Tuple[List['LandListing'], Dict]:
        payload = {
            "filter": {"purchaseStageState": [1000004]},
            "page": page,
            "take": per_page,
            "orderByColumn": "Id",
            "orderByDescending": True
        }
        data = self._make_request(payload)
        if not data:
            return [], {}

        listings = []
        for obj in data.get('objects', []):
            try:
                listings.append(self._parse_listing(obj, fetch_html))
            except Exception as e:
                print(f"❌ Ошибка парсинга лота {obj.get('id')}: {e}")
        return listings, data.get('pagination', {})

    def search(self, query: Optional[str] = None,
               price_from: Optional[float] = None,
               price_to: Optional[float] = None,
               fetch_html: bool = False) -> List['LandListing']:
        payload = {
            "filter": {"purchaseStageState": [1000004]},
            "page": 1,
            "take": 50,
            "query": query,
            "orderByColumn": "Id",
            "orderByDescending": True
        }
        data = self._make_request(payload)
        if not data:
            return []

        listings = []
        for obj in data.get('objects', []):
            try:
                listing = self._parse_listing(obj, fetch_html)
                if price_from and listing.start_price < price_from:
                    continue
                if price_to and listing.start_price > price_to:
                    continue
                listings.append(listing)
            except Exception as e:
                print(f"❌ Ошибка поиска: {e}")
        return listings