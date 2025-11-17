from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index, UniqueConstraint, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()


class Listing(Base):
    __tablename__ = 'listings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(500), nullable=False)
    registry_number = Column(String(100), unique=True, nullable=False, index=True)
    start_price = Column(Float, nullable=False, index=True)
    deposit_amount = Column(Float, default=0)
    start_step_amount = Column(Float, default=0)
    total_square = Column(Float, default=0, index=True)
    address_description = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    district_code = Column(String(100), index=True)
    right_term_use_year = Column(Integer)
    right_term_use_month = Column(Integer)
    purchase_kind_name = Column(String(200))
    purchase_form_name = Column(String(200))
    stage_state_name = Column(String(200), index=True)
    land_allowed_use_name = Column(String(500), index=True)
    accept_plan_end_date = Column(DateTime)
    review_plan_end_date = Column(DateTime)
    count_views = Column(Integer, default=0)
    photos_json = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # === НОВЫЕ ПОЛЯ ДЛЯ HTML-СКРАПИНГА ===
    full_address = Column(String(1000), default="")
    direct_url = Column(String(1000), default="")
    object_type = Column(String(50), default="")
    cadastral_number = Column(String(100), default="", index=True)
    # =====================================

    __table_args__ = (
        Index("idx_price_area", "start_price", "total_square"),
        Index("idx_district_purpose", "district_code", "land_allowed_use_name"),
        Index("idx_stage_state", "stage_state_name"),
        Index("idx_coordinates", "latitude", "longitude"),
        Index("idx_cadastral", "cadastral_number"),
        UniqueConstraint("registry_number", name="uq_registry_number"),
    )

    def __repr__(self):
        return f"<Listing {self.id}: {self.name[:50]}>"

    @property
    def photos(self) -> list:
        """Возвращает список URL фотографий или пустой список."""
        if not self.photos_json:
            return []
        try:
            data = json.loads(self.photos_json)
            return data if isinstance(data, list) else []
        except (TypeError, ValueError):
            return []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "registry_number": self.registry_number,
            "start_price": self.start_price,
            "total_square": self.total_square,
            "address_description": self.address_description,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "district_code": self.district_code,
            "purchase_kind_name": self.purchase_kind_name,
            "land_allowed_use_name": self.land_allowed_use_name,
            "accept_plan_end_date": self.accept_plan_end_date.isoformat() if self.accept_plan_end_date else None,
            "review_plan_end_date": self.review_plan_end_date.isoformat() if self.review_plan_end_date else None,
            "photos_json": self.photos_json,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "full_address": self.full_address,
            "direct_url": self.direct_url,
            "object_type": self.object_type,
            "cadastral_number": self.cadastral_number,
        }


class ListingHistory(Base):
    __tablename__ = 'listing_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String(100))
    old_value = Column(Text)
    new_value = Column(Text)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<History {self.listing_id}: {self.field_name}>"


class TelegramUser(Base):
    __tablename__ = 'telegram_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    notify_new_listings = Column(Boolean, default=False)
    notify_price_changes = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.telegram_id}: {self.username}>"


# ===== НОВАЯ МОДЕЛЬ: ИЗБРАННОЕ =====
class Favorite(Base):
    __tablename__ = 'favorites'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_user_favorites", "telegram_id", "added_at"),
        UniqueConstraint("telegram_id", "listing_id", name="uq_user_listing"),
    )

    def __repr__(self):
        return f"<Favorite user={self.telegram_id} listing={self.listing_id}>"