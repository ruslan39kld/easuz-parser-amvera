from typing import List, Optional

class LandListing:
    """Модель объявления о продаже земли/недвижимости с ЕАСУЗ"""
    
    def __init__(self,
                 id: int,
                 name: str,
                 registry_number: str = "",
                 start_price: float = 0,
                 deposit_amount: float = 0,
                 start_step_amount: float = 0,
                 total_square: float = 0,
                 address_description: str = "",
                 # ===== НОВЫЕ ПОЛЯ =====
                 full_address: str = "",              # Полный адрес из HTML
                 direct_url: str = "",                # Прямая ссылка на лот
                 object_type: str = "",               # "land" или "buildings"
                 cadastral_number: str = "",          # ← КАДАСТРОВЫЙ НОМЕР (НОВОЕ)
                 # ======================
                 latitude: Optional[float] = None,
                 longitude: Optional[float] = None,
                 district_code: Optional[str] = None,
                 right_term_use_year: Optional[int] = None,
                 right_term_use_month: Optional[int] = None,
                 purchase_kind_name: str = "",
                 purchase_form_name: str = "",
                 stage_state_name: str = "",
                 land_allowed_use_name: str = "",
                 accept_plan_end_date: Optional[str] = None,
                 review_plan_end_date: Optional[str] = None,
                 count_views: int = 0,
                 photos: List[str] = None):
        
        self.id = id
        self.name = name
        self.registry_number = registry_number
        self.start_price = start_price
        self.deposit_amount = deposit_amount
        self.start_step_amount = start_step_amount
        self.total_square = total_square
        self.address_description = address_description
        
        # Новые поля
        self.full_address = full_address
        self.direct_url = direct_url
        self.object_type = object_type
        self.cadastral_number = cadastral_number  # ← ДОБАВЛЕНО
        
        self.latitude = latitude
        self.longitude = longitude
        self.district_code = district_code
        self.right_term_use_year = right_term_use_year
        self.right_term_use_month = right_term_use_month
        self.purchase_kind_name = purchase_kind_name
        self.purchase_form_name = purchase_form_name
        self.stage_state_name = stage_state_name
        self.land_allowed_use_name = land_allowed_use_name
        self.accept_plan_end_date = accept_plan_end_date
        self.review_plan_end_date = review_plan_end_date
        self.count_views = count_views
        self.photos = photos or []
    
    def get_display_address(self) -> str:
        """Получить лучший доступный адрес для отображения"""
        return self.full_address or self.address_description or "Адрес не указан"
    
    def get_link(self) -> str:
        """Получить лучшую доступную ссылку"""
        # 🔧 ИСПРАВЛЕНО: убраны пробелы
        return self.direct_url or f"https://easuz.mosreg.ru/torgi/purchase/{self.id}"
    
    def has_complete_data(self) -> bool:
        """Проверить, загружены ли HTML-данные"""
        return bool(self.direct_url and self.full_address)
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сохранения в БД"""
        return {
            'id': self.id,
            'name': self.name,
            'registry_number': self.registry_number,
            'start_price': self.start_price,
            'deposit_amount': self.deposit_amount,
            'start_step_amount': self.start_step_amount,
            'total_square': self.total_square,
            'address_description': self.address_description,
            'full_address': self.full_address,
            'direct_url': self.direct_url,
            'object_type': self.object_type,
            'cadastral_number': self.cadastral_number,  # ← ДОБАВЛЕНО
            'latitude': self.latitude,
            'longitude': self.longitude,
            'district_code': self.district_code,
            'right_term_use_year': self.right_term_use_year,
            'right_term_use_month': self.right_term_use_month,
            'purchase_kind_name': self.purchase_kind_name,
            'purchase_form_name': self.purchase_form_name,
            'stage_state_name': self.stage_state_name,
            'land_allowed_use_name': self.land_allowed_use_name,
            'accept_plan_end_date': self.accept_plan_end_date,
            'review_plan_end_date': self.review_plan_end_date,
            'count_views': self.count_views,
            'photos': ','.join(self.photos) if self.photos else ''
        }
    
    def __repr__(self):
        return f"<LandListing id={self.id} name='{self.name[:30]}...'>"