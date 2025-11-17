"""
Скрипт для применения миграций базы данных

ИСПОЛЬЗОВАНИЕ:
    python src/database/migrate.py              # Применить все непримененные миграции
    python src/database/migrate.py --rollback   # Откатить последнюю миграцию
    python src/database/migrate.py --status     # Показать статус миграций
"""

import sqlite3
import sys
from pathlib import Path
import importlib.util
import shutil


class MigrationManager:
    """Менеджер миграций базы данных"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / 'migrations'

        if not self.db_path.exists():
            print(f"❌ База данных не найдена: {self.db_path}")
            sys.exit(1)

    def get_connection(self):
        """Получить соединение с БД"""
        return sqlite3.connect(str(self.db_path))

    def init_migrations_table(self, conn):
        """Создать таблицу для отслеживания миграций"""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def get_applied_migrations(self, conn):
        """Получить список примененных миграций"""
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY migration_name")
        return {row[0] for row in cursor.fetchall()}

    def get_available_migrations(self):
        """Получить список доступных файлов миграций"""
        if not self.migrations_dir.exists():
            print(f"⚠️ Папка миграций не найдена: {self.migrations_dir}")
            return []

        migrations = []
        for file in sorted(self.migrations_dir.glob('*.py')):
            if file.name.startswith('__'):
                continue
            migration_name = file.stem
            migrations.append((migration_name, file))

        return migrations

    def load_migration_module(self, migration_file):
        """Загрузить модуль миграции"""
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def apply_migration(self, conn, migration_name, migration_file):
        """Применить одну миграцию"""
        print(f"\n{'=' * 60}")
        print(f"📦 Применяем миграцию: {migration_name}")
        print(f"{'=' * 60}\n")

        try:
            module = self.load_migration_module(migration_file)
            module.upgrade(conn)

            cursor = conn.cursor()
            cursor.execute("INSERT INTO schema_migrations (migration_name) VALUES (?)", (migration_name,))
            conn.commit()

            print(f"✅ Миграция {migration_name} успешно применена")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка применения миграции {migration_name}: {e}")
            return False

    def rollback_migration(self, conn, migration_name, migration_file):
        """Откатить миграцию"""
        print(f"\n{'=' * 60}")
        print(f"⏪ Откатываем миграцию: {migration_name}")
        print(f"{'=' * 60}\n")

        try:
            module = self.load_migration_module(migration_file)
            module.downgrade(conn)

            cursor = conn.cursor()
            cursor.execute("DELETE FROM schema_migrations WHERE migration_name = ?", (migration_name,))
            conn.commit()

            print(f"✅ Миграция {migration_name} успешно откачена")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ Ошибка отката миграции {migration_name}: {e}")
            return False

    def migrate(self):
        """Применить все непримененные миграции"""
        conn = self.get_connection()
        try:
            self.init_migrations_table(conn)
            applied = self.get_applied_migrations(conn)
            available = self.get_available_migrations()

            if not available:
                print("📭 Нет доступных миграций")
                return

            pending = [(name, file) for name, file in available if name not in applied]
            if not pending:
                print("✅ Все миграции уже применены")
                return

            print(f"\n🚀 Найдено {len(pending)} непримененных миграций\n")
            for migration_name, migration_file in pending:
                if not self.apply_migration(conn, migration_name, migration_file):
                    print(f"\n❌ Остановка на миграции {migration_name}")
                    break

            print("\n" + "=" * 60)
            print("🎉 Миграция завершена!")
            print("=" * 60)

        finally:
            conn.close()

    def rollback(self):
        """Откатить последнюю примененную миграцию"""
        conn = self.get_connection()
        try:
            self.init_migrations_table(conn)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT migration_name 
                FROM schema_migrations 
                ORDER BY applied_at DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                print("📭 Нет примененных миграций для отката")
                return

            migration_name = row[0]
            migration_file = self.migrations_dir / f"{migration_name}.py"
            if not migration_file.exists():
                print(f"❌ Файл миграции не найден: {migration_file}")
                return

            print(f"\n⚠️  ВНИМАНИЕ: Откат миграции {migration_name}")
            print("⚠️  Это может привести к потере данных!")
            if input("\nПродолжить? (yes/no): ").lower() != 'yes':
                print("❌ Откат отменён")
                return

            self.rollback_migration(conn, migration_name, migration_file)

        finally:
            conn.close()

    def status(self):
        """Показать статус миграций"""
        conn = self.get_connection()
        try:
            self.init_migrations_table(conn)
            applied = self.get_applied_migrations(conn)
            available = self.get_available_migrations()

            print("\n" + "=" * 60)
            print("📊 СТАТУС МИГРАЦИЙ")
            print("=" * 60 + "\n")

            if not available:
                print("📭 Нет доступных миграций")
                return

            for migration_name, _ in available:
                status = "✅ Применена" if migration_name in applied else "⏳ Ожидает"
                print(f"{status}  {migration_name}")

            print(f"\nВсего миграций: {len(available)}")
            print(f"Применено: {len(applied)}")
            print(f"Ожидает: {len(available) - len(applied)}")
            print("=" * 60)

        finally:
            conn.close()


def find_database():
    """Найти easuz.db в типичных местах, включая папку data/"""
    current = Path.cwd()
    candidates = [
        current / 'easuz.db',
        current / 'data' / 'easuz.db',
        current / 'src' / 'database' / 'easuz.db',
        current / 'src' / 'easuz.db',
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def main():
    print("\n" + "=" * 60)
    print("🗄️  МЕНЕДЖЕР МИГРАЦИЙ БД EASUZ")
    print("=" * 60 + "\n")

    db_path = find_database()
    if not db_path:
        print("❌ easuz.db не найден в корне, src/, src/database/ или data/")
        print("Убедитесь, что файл easuz.db существует.")
        sys.exit(1)

    print(f"📁 Использую БД: {db_path}\n")

    backup_path = db_path.with_suffix('.db.backup')
    print(f"💾 Создаём резервную копию: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("✅ Резервная копия создана\n")

    manager = MigrationManager(db_path)

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == '--rollback':
            manager.rollback()
        elif cmd == '--status':
            manager.status()
        elif cmd == '--help':
            print(__doc__)
        else:
            print(f"❌ Неизвестная команда: {cmd}")
            sys.exit(1)
    else:
        manager.migrate()


if __name__ == "__main__":
    main()