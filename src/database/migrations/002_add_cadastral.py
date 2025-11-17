"""
Миграция 002: Добавление поля кадастрового номера

Дата: 2025-11-11
Автор: Система
Описание: Добавляет поле cadastral_number в таблицу listings
"""

def upgrade(connection):
    """Применить миграцию - добавить поле cadastral_number"""
    cursor = connection.cursor()
    
    print("▶️ Применяем миграцию 002: add_cadastral_number")
    
    try:
        # Проверяем, существует ли уже поле
        cursor.execute("PRAGMA table_info(listings)")
        columns = {col[1] for col in cursor.fetchall()}
        
        if 'cadastral_number' not in columns:
            print("   Добавляем поле cadastral_number...")
            cursor.execute("""
                ALTER TABLE listings 
                ADD COLUMN cadastral_number TEXT DEFAULT ''
            """)
            print("✅ Поле добавлено")
        else:
            print("   ⏭️ Поле cadastral_number уже существует")
        
        # Создаём индекс (опционально, но рекомендуется)
        print("   Создаём индекс idx_cadastral...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cadastral 
            ON listings(cadastral_number)
        """)
        
        connection.commit()
        print("✅ Миграция 002 успешно применена!\n")
        
    except Exception as e:
        connection.rollback()
        print(f"❌ Ошибка применения миграции: {e}\n")
        raise


def downgrade(connection):
    """
    Откатить миграцию - удалить поле cadastral_number
    
    ⚠️ Внимание: SQLite не поддерживает DROP COLUMN напрямую.
    Для отката нужно пересоздать таблицу.
    """
    cursor = connection.cursor()
    
    print("⚠️  ОТКАТ миграции 002: add_cadastral_number")
    print("⚠️  Это приведёт к потере данных в поле cadastral_number!")
    
    try:
        # Получаем список всех колонок (без cadastral_number)
        cursor.execute("PRAGMA table_info(listings)")
        all_columns = [col[1] for col in cursor.fetchall()]
        old_columns = [col for col in all_columns if col != 'cadastral_number']
        columns_str = ', '.join(old_columns)
        
        # Создаём новую таблицу без поля cadastral_number
        cursor.execute(f"""
            CREATE TABLE listings_new AS 
            SELECT {columns_str} FROM listings
        """)
        
        # Удаляем старую таблицу
        print("   Удаляем старую таблицу...")
        cursor.execute("DROP TABLE listings")
        
        # Переименовываем новую таблицу
        print("   Переименовываем таблицу...")
        cursor.execute("ALTER TABLE listings_new RENAME TO listings")
        
        # Удаляем индекс
        print("   Удаляем индекс...")
        cursor.execute("DROP INDEX IF EXISTS idx_cadastral")
        
        connection.commit()
        print("✅ Откат миграции 002 выполнен\n")
        
    except Exception as e:
        connection.rollback()
        print(f"❌ Ошибка отката миграции: {e}\n")
        raise