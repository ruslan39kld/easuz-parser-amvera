"""
Миграция 001: Добавление полей для HTML-данных
Дата: 2025-01-11
Автор: System
Описание: Добавляет поля full_address, direct_url, object_type в таблицу listings
"""


def upgrade(connection):
    """Применить миграцию - добавить новые поля"""
    cursor = connection.cursor()
    
    print("▶️  Применяем миграцию 001: add_html_fields")
    
    try:
        # Проверяем, существуют ли уже эти поля
        cursor.execute("PRAGMA table_info(listings)")
        columns = {col[1] for col in cursor.fetchall()}
        
        # Добавляем поля, если их ещё нет
        if 'full_address' not in columns:
            print("   Добавляем поле full_address...")
            cursor.execute("""
                ALTER TABLE listings 
                ADD COLUMN full_address TEXT DEFAULT ''
            """)
        else:
            print("   ⏭️  Поле full_address уже существует")
        
        if 'direct_url' not in columns:
            print("   Добавляем поле direct_url...")
            cursor.execute("""
                ALTER TABLE listings 
                ADD COLUMN direct_url TEXT DEFAULT ''
            """)
        else:
            print("   ⏭️  Поле direct_url уже существует")
        
        if 'object_type' not in columns:
            print("   Добавляем поле object_type...")
            cursor.execute("""
                ALTER TABLE listings 
                ADD COLUMN object_type VARCHAR(20) DEFAULT ''
            """)
        else:
            print("   ⏭️  Поле object_type уже существует")
        
        # Создаём индекс для быстрого поиска по типу объекта
        print("   Создаём индекс idx_listings_object_type...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listings_object_type 
            ON listings(object_type)
        """)
        
        connection.commit()
        print("✅ Миграция 001 успешно применена!\n")
        
    except Exception as e:
        connection.rollback()
        print(f"❌ Ошибка применения миграции: {e}\n")
        raise


def downgrade(connection):
    """
    Откатить миграцию - удалить добавленные поля
    
    ⚠️ ВНИМАНИЕ: SQLite не поддерживает DROP COLUMN напрямую.
    Для отката нужно пересоздать таблицу без этих полей.
    """
    cursor = connection.cursor()
    
    print("⚠️  ОТКАТ миграции 001: add_html_fields")
    print("⚠️  Это приведёт к потере данных в полях full_address, direct_url, object_type!")
    
    try:
        # Для SQLite нужно пересоздавать таблицу
        print("   Создаём временную таблицу...")
        
        # 1. Получаем список всех колонок (кроме новых)
        cursor.execute("PRAGMA table_info(listings)")
        all_columns = [col[1] for col in cursor.fetchall()]
        old_columns = [col for col in all_columns 
                      if col not in ['full_address', 'direct_url', 'object_type']]
        columns_str = ', '.join(old_columns)
        
        # 2. Создаём новую таблицу без этих полей
        cursor.execute(f"""
            CREATE TABLE listings_new AS 
            SELECT {columns_str} FROM listings
        """)
        
        # 3. Удаляем старую таблицу
        print("   Удаляем старую таблицу...")
        cursor.execute("DROP TABLE listings")
        
        # 4. Переименовываем новую таблицу
        print("   Переименовываем таблицу...")
        cursor.execute("ALTER TABLE listings_new RENAME TO listings")
        
        # 5. Удаляем индекс
        print("   Удаляем индекс...")
        cursor.execute("DROP INDEX IF EXISTS idx_listings_object_type")
        
        connection.commit()
        print("✅ Откат миграции 001 выполнен\n")
        
    except Exception as e:
        connection.rollback()
        print(f"❌ Ошибка отката миграции: {e}\n")
        raise