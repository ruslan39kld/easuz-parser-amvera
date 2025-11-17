from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class LandListing:
    """Модель объявления о земельном участке"""
    
    # Основная информация
    id: int
    name: str
    registry_number: str
    
    # Цена и условия
    start_price: float
    deposit_amount: float
    start_step_amount: float
    
    # Площадь
    total_square: float
    
    # Адрес и местоположение
    address_description: str
    latitude: Optional[float]
    longitude: Optional[float]
    district_code: Optional[str]
    
    # Срок аренды/продажи
    right_term_use_year: Optional[int]
    right_term_use_month: Optional[int]
    
    # Тип и статус
    purchase_kind_name: str  # Аренда/Продажа
    purchase_form_name: str  # Аукцион
    stage_state_name: str    # Торги объявлены
    land_allowed_use_name: str  # Назначение земли
    
    # Даты
    accept_plan_end_date: Optional[str]
    review_plan_end_date: Optional[str]
    
    # Дополнительно
    count_views: int
    photos: List[str]
    
    # URL на ЕАСУЗ
    @property
    def url(self) -> str:
        return f"https://easuz.mosreg.ru/purchase/{self.id}"
    
    def __str__(self):
        return f"{self.name} - {self.start_price:,.0f} руб. ({self.total_square} кв.м)"
    
    def to_dict(self):
        """Конвертация в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'registry_number': self.registry_number,
            'price': self.start_price,
            'deposit': self.deposit_amount,
            'area': self.total_square,
            'address': self.address_description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'district_code': self.district_code,
            'term_years': self.right_term_use_year,
            'term_months': self.right_term_use_month,
            'purchase_type': self.purchase_kind_name,
            'purchase_form': self.purchase_form_name,
            'status': self.stage_state_name,
            'land_use': self.land_allowed_use_name,
            'deadline': self.accept_plan_end_date,
            'views': self.count_views,
            'photos': self.photos,
            'url': self.url
        }