import sqlite3
import json
import os
import datetime
import sys
from config import get_config

class DataExporter:
    """Class untuk export data dari database"""
    
    def __init__(self):
        self.config = get_config()
        self.database_path = self.config.DATABASE_PATH
    
    def export_to_json(self, output_file=None):
        """Export semua data ke file JSON"""
        if not output_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            env = os.environ.get('FLASK_ENV', 'development')
            output_file = f"{env}_data_export_{timestamp}.json"
        
        print(f"Exporting from: {self.database_path}")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
        
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Dictionary untuk menyimpan semua data
        data = {
            'metadata': {
                'exported_at': datetime.datetime.now().isoformat(),
                'environment': os.environ.get('FLASK_ENV', 'development'),
                'database_path': self.database_path
            },
            'tables': {}
        }
        
        # Daftar tabel yang akan di-export (kecuali migrations)
        tables = ['books', 'offline_buyers', 'offline_sales', 'online_sales', 'users']
        
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                data['tables'][table] = [dict(row) for row in rows]
                print(f"✓ Exported {len(rows)} rows from {table}")
            except sqlite3.OperationalError as e:
                print(f"⚠️  Skip table {table}: {str(e)}")
        
        conn.close()
        
        # Simpan ke file JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ Data exported to: {output_file}")
        return output_file


class DataImporter:
    """Class untuk import data ke database"""
    
    def __init__(self):
        self.config = get_config()
        self.database_path = self.config.DATABASE_PATH
    
    def import_from_json(self, input_file, mode='merge'):
        """
        Import data dari file JSON
        mode: 'merge' (default) atau 'replace'
        """
        print(f"Importing to: {self.database_path}")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
        print(f"Mode: {mode}")
        
        # Baca file JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\nSource environment: {data['metadata']['environment']}")
        print(f"Exported at: {data['metadata']['exported_at']}")
        
        # Konfirmasi
        response = input(f"\nImport data ke database {os.environ.get('FLASK_ENV', 'development')}? (y/n): ")
        if response.lower() != 'y':
            print("Import dibatalkan.")
            return
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Backup database sebelum import
        self._backup_database()
        
        try:
            if mode == 'replace':
                # Mode replace: hapus data lama dulu
                for table in data['tables'].keys():
                    if table != 'users':  # Jangan hapus users
                        cursor.execute(f"DELETE FROM {table}")
                        print(f"✓ Cleared table {table}")
            
            # Import data
            for table, rows in data['tables'].items():
                if table == 'users' and mode == 'merge':
                    # Skip users table in merge mode untuk keamanan
                    print(f"⚠️  Skip table 'users' in merge mode (untuk keamanan)")
                    continue
                
                imported = 0
                skipped = 0
                
                for row in rows:
                    # Buat placeholders untuk query
                    columns = list(row.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    column_names = ','.join(columns)
                    
                    if mode == 'merge':
                        # Coba insert, skip jika ada konflik
                        try:
                            query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
                            cursor.execute(query, list(row.values()))
                            imported += 1
                        except sqlite3.IntegrityError:
                            skipped += 1
                    else:
                        # Mode replace: langsung insert
                        query = f"INSERT INTO {table} ({column_names}) VALUES ({placeholders})"
                        cursor.execute(query, list(row.values()))
                        imported += 1
                
                print(f"✓ Table {table}: imported {imported}, skipped {skipped}")
            
            conn.commit()
            print("\n✅ Import completed successfully!")
            
        except Exception as e:
            conn.rollback()
            print(f"\n❌ Error during import: {str(e)}")
            print("Database rolled back to previous state.")
            raise
        finally:
            conn.close()
    
    def _backup_database(self):
        """Backup database sebelum import"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.database_path}.backup_before_import_{timestamp}"
        
        import shutil
        shutil.copy2(self.database_path, backup_path)
        print(f"✅ Backup created: {backup_path}")


def export_data():
    """Export data dari database"""
    exporter = DataExporter()
    exporter.export_to_json()


def import_data(filename, mode='merge'):
    """Import data ke database"""
    if not os.path.exists(filename):
        print(f"❌ File tidak ditemukan: {filename}")
        return
    
    importer = DataImporter()
    importer.import_from_json(filename, mode)


def sync_production_to_development():
    """
    Helper function untuk sync data dari production ke development
    Hanya sync data transaksi, bukan user/admin
    """
    # Backup current environment
    current_env = os.environ.get('FLASK_ENV', 'development')
    
    try:
        # Export dari production
        print("=== STEP 1: Export dari Production ===")
        os.environ['FLASK_ENV'] = 'production'
        exporter = DataExporter()
        export_file = exporter.export_to_json()
        
        # Import ke development
        print("\n=== STEP 2: Import ke Development ===")
        os.environ['FLASK_ENV'] = 'development'
        importer = DataImporter()
        importer.import_from_json(export_file, mode='merge')
        
        print("\n✅ Sync completed!")
        
    finally:
        # Restore environment
        os.environ['FLASK_ENV'] = current_env


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python export_import_data.py export")
        print("  python export_import_data.py import <filename> [merge|replace]")
        print("  python export_import_data.py sync-prod-to-dev")
        return
    
    command = sys.argv[1]
    
    if command == 'export':
        export_data()
    
    elif command == 'import':
        if len(sys.argv) < 3:
            print("❌ Please provide filename to import")
            return
        
        filename = sys.argv[2]
        mode = sys.argv[3] if len(sys.argv) > 3 else 'merge'
        
        if mode not in ['merge', 'replace']:
            print("❌ Mode must be 'merge' or 'replace'")
            return
        
        import_data(filename, mode)
    
    elif command == 'sync-prod-to-dev':
        response = input("⚠️  This will sync production data to development. Continue? (y/n): ")
        if response.lower() == 'y':
            sync_production_to_development()
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == '__main__':
    main()