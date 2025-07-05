import sqlite3
import os
import datetime
from config import get_config

class DatabaseMigration:
    """Class untuk mengelola migrasi database"""
    
    def __init__(self):
        self.config = get_config()
        self.database_path = self.config.DATABASE_PATH
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Membuat koneksi ke database"""
        self.connection = sqlite3.connect(self.database_path)
        self.cursor = self.connection.cursor()
        print(f"Connected to database: {self.database_path}")
    
    def disconnect(self):
        """Menutup koneksi database"""
        if self.connection:
            self.connection.close()
            print("Disconnected from database")
    
    def backup_database(self):
        """Membuat backup database sebelum migrasi"""
        if not os.path.exists(self.database_path):
            print("⚠️  Database tidak ditemukan, skip backup")
            return
        
        # Buat nama file backup dengan timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.database_path}.backup_{timestamp}"
        
        # Copy database ke file backup
        import shutil
        shutil.copy2(self.database_path, backup_path)
        print(f"✅ Backup database dibuat: {backup_path}")
        return backup_path
    
    def check_table_exists(self, table_name):
        """Cek apakah tabel sudah ada"""
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return self.cursor.fetchone() is not None
    
    def check_column_exists(self, table_name, column_name):
        """Cek apakah kolom sudah ada di tabel"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in self.cursor.fetchall()]
        return column_name in columns
    
    def create_migration_table(self):
        """Membuat tabel untuk tracking migrasi"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.connection.commit()
        print("✓ Tabel migrations berhasil dibuat/diperiksa")
    
    def is_migration_applied(self, migration_name):
        """Cek apakah migrasi sudah pernah dijalankan"""
        self.cursor.execute(
            "SELECT * FROM migrations WHERE name = ?",
            (migration_name,)
        )
        return self.cursor.fetchone() is not None
    
    def mark_migration_applied(self, migration_name):
        """Tandai migrasi sudah dijalankan"""
        self.cursor.execute(
            "INSERT INTO migrations (name) VALUES (?)",
            (migration_name,)
        )
        self.connection.commit()
    
    def run_migration(self, migration_name, migration_func):
        """Jalankan migrasi jika belum pernah dijalankan"""
        if self.is_migration_applied(migration_name):
            print(f"⚠️  Skip migration '{migration_name}' (sudah dijalankan)")
            return False
        
        print(f"\n🔄 Menjalankan migration: {migration_name}")
        try:
            migration_func()
            self.mark_migration_applied(migration_name)
            print(f"✅ Migration '{migration_name}' berhasil")
            return True
        except Exception as e:
            print(f"❌ Error pada migration '{migration_name}': {str(e)}")
            self.connection.rollback()
            return False
    
    # --- DEFINISI MIGRASI ---
    
    def migration_001_add_address_dormitory(self):
        """Menambahkan kolom address dan dormitory ke offline_buyers"""
        if not self.check_column_exists('offline_buyers', 'address'):
            self.cursor.execute('ALTER TABLE offline_buyers ADD COLUMN address TEXT')
            print("  ✓ Kolom 'address' ditambahkan")
        
        if not self.check_column_exists('offline_buyers', 'dormitory'):
            self.cursor.execute('ALTER TABLE offline_buyers ADD COLUMN dormitory TEXT')
            print("  ✓ Kolom 'dormitory' ditambahkan")
        
        self.connection.commit()
    
    def migration_002_add_transfer_date(self):
        """Menambahkan kolom transfer_date ke online_sales"""
        if not self.check_column_exists('online_sales', 'transfer_date'):
            self.cursor.execute('ALTER TABLE online_sales ADD COLUMN transfer_date TEXT')
            print("  ✓ Kolom 'transfer_date' ditambahkan")
        
        self.connection.commit()
    
    def migration_003_add_image_filename(self):
        """Menambahkan kolom image_filename ke books"""
        if not self.check_column_exists('books', 'image_filename'):
            self.cursor.execute('ALTER TABLE books ADD COLUMN image_filename TEXT')
            print("  ✓ Kolom 'image_filename' ditambahkan")
        
        self.connection.commit()
    
    def migration_004_add_quantity_online_sales(self):
        """Menambahkan kolom quantity ke online_sales"""
        if not self.check_column_exists('online_sales', 'quantity'):
            self.cursor.execute('ALTER TABLE online_sales ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1')
            print("  ✓ Kolom 'quantity' ditambahkan")
        
        self.connection.commit()
    
    def migration_005_remove_dormitory_column(self):
        """Menghapus kolom dormitory dari offline_buyers"""
        print("  🔄 Menghapus kolom 'dormitory' dari tabel offline_buyers...")
        
        # Backup data dulu
        self.cursor.execute("SELECT COUNT(*) FROM offline_buyers")
        count = self.cursor.fetchone()[0]
        print(f"  📊 Total data pembeli offline: {count}")
        
        try:
            # 1. Rename tabel lama
            self.cursor.execute("ALTER TABLE offline_buyers RENAME TO offline_buyers_old")
            
            # 2. Buat tabel baru tanpa kolom dormitory
            self.cursor.execute('''
            CREATE TABLE offline_buyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                address TEXT
            )
            ''')
            
            # 3. Copy data dari tabel lama (tanpa kolom dormitory)
            self.cursor.execute('''
            INSERT INTO offline_buyers (id, name, address)
            SELECT id, name, address FROM offline_buyers_old
            ''')
            
            # 4. Hapus tabel lama
            self.cursor.execute("DROP TABLE offline_buyers_old")
            
            self.connection.commit()
            print("  ✅ Kolom 'dormitory' berhasil dihapus dari offline_buyers")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.connection.rollback()
            raise
    
    def run_all_migrations(self):
        """Jalankan semua migrasi yang belum dijalankan"""
        print("\n=== RUNNING DATABASE MIGRATIONS ===")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
        print(f"Database: {self.database_path}")
        
        # Backup database terlebih dahulu
        self.backup_database()
        
        # Connect ke database
        self.connect()
        
        # Buat tabel migrations
        self.create_migration_table()
        
        # Daftar semua migrasi
        migrations = [
            ('001_add_address_dormitory', self.migration_001_add_address_dormitory),
            ('002_add_transfer_date', self.migration_002_add_transfer_date),
            ('003_add_image_filename', self.migration_003_add_image_filename),
            ('004_add_quantity_online_sales', self.migration_004_add_quantity_online_sales),
            ('005_remove_dormitory_column', self.migration_005_remove_dormitory_column),
        ]
        
        # Jalankan migrasi
        applied_count = 0
        for name, func in migrations:
            if self.run_migration(name, func):
                applied_count += 1
        
        # Disconnect
        self.disconnect()
        
        print(f"\n✅ Migrasi selesai! {applied_count} migrasi diterapkan.")

def main():
    """Main function"""
    import sys
    
    # Set environment jika diberikan sebagai argument
    if len(sys.argv) > 1:
        os.environ['FLASK_ENV'] = sys.argv[1]
        print(f"Setting FLASK_ENV to: {sys.argv[1]}")
    
    # Konfirmasi sebelum menjalankan migrasi
    print("\n⚠️  PERHATIAN: Anda akan menjalankan migrasi database!")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    response = input("\nLanjutkan? (y/n): ")
    if response.lower() != 'y':
        print("Migrasi dibatalkan.")
        return
    
    # Jalankan migrasi
    migration = DatabaseMigration()
    migration.run_all_migrations()

if __name__ == '__main__':
    main()