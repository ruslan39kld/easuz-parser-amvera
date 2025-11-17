import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.database.models import Base
from src.database.session import engine

print("🔧 Создание таблиц БД...")

Base.metadata.create_all(engine)

print("✅ База данных создана успешно!")
print(f"📍 Файл: {engine.url}")