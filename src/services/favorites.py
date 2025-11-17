# src/services/favorites.py
from sqlalchemy.orm import Session
from src.database.models import Favorite, Listing
from typing import List, Optional

MAX_FAVORITES = 10


class FavoritesService:
    """Сервис для управления избранным пользователя"""

    def __init__(self, db: Session):
        self.db = db

    def add(self, telegram_id: int, listing_id: int) -> bool:
        """Добавить объявление в избранное. Возвращает True если добавлено."""
        # Проверка лимита
        count = self.db.query(Favorite).filter(
            Favorite.telegram_id == telegram_id
        ).count()
        
        if count >= MAX_FAVORITES:
            return False

        # Проверка существования
        exists = self.db.query(Favorite).filter(
            Favorite.telegram_id == telegram_id,
            Favorite.listing_id == listing_id
        ).first()
        
        if exists:
            return False

        # Добавление
        fav = Favorite(telegram_id=telegram_id, listing_id=listing_id)
        self.db.add(fav)
        self.db.commit()
        return True

    def remove(self, telegram_id: int, listing_id: int) -> bool:
        """Удалить объявление из избранного."""
        fav = self.db.query(Favorite).filter(
            Favorite.telegram_id == telegram_id,
            Favorite.listing_id == listing_id
        ).first()
        
        if fav:
            self.db.delete(fav)
            self.db.commit()
            return True
        return False

    def clear(self, telegram_id: int) -> int:
        """Очистить всё избранное. Возвращает количество удалённых."""
        count = self.db.query(Favorite).filter(
            Favorite.telegram_id == telegram_id
        ).delete()
        self.db.commit()
        return count

    def get_all(self, telegram_id: int) -> List[Listing]:
        """Получить все избранные объявления."""
        favorites = self.db.query(Listing).join(
            Favorite, Favorite.listing_id == Listing.id
        ).filter(
            Favorite.telegram_id == telegram_id
        ).order_by(
            Favorite.added_at.desc()
        ).all()
        
        return favorites

    def count(self, telegram_id: int) -> int:
        """Количество избранных объявлений."""
        return self.db.query(Favorite).filter(
            Favorite.telegram_id == telegram_id
        ).count()

    def is_favorite(self, telegram_id: int, listing_id: int) -> bool:
        """Проверка, находится ли объявление в избранном."""
        return self.db.query(Favorite).filter(
            Favorite.telegram_id == telegram_id,
            Favorite.listing_id == listing_id
        ).first() is not None