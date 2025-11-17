# scripts/init_db.py
# Скрипт для создания/обновления таблиц в базе данных

import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.models import Base
from src.database.session import engine

def init_database():
    """Создание всех таблиц в базе данных"""
    print("=" * 60)
    print("🔧 Инициализация базы данных...")
    print("=" * 60)
    
    try:
        # Создаем все таблицы, определенные в моделях
        Base.metadata.create_all(bind=engine)
        
        print("✅ Таблицы успешно созданы!")
        print("\n📋 Созданные таблицы:")
        for table_name in Base.metadata.tables.keys():
            print(f"  • {table_name}")
        
        print("\n" + "=" * 60)
        print("✅ Инициализация завершена успешно!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False
    
    return True

if __name__ == "__main__":
    init_database()