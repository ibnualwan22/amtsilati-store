#!/usr/bin/env python
"""
Management script untuk Amtsilati Store
Mempermudah berbagai operasi database dan aplikasi
"""

import os
import sys
import subprocess
from pathlib import Path

# Tambahkan current directory ke Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """Print header yang menarik"""
    print("\n" + "="*50)
    print(f" {title} ")
    print("="*50 + "\n")

def print_menu():
    """Print menu utama"""
    print_header("AMTSILATI STORE MANAGEMENT")
    print("Environment:", os.environ.get('FLASK_ENV', 'development'))
    print("\nPilih operasi:")
    print("1. Setup database baru")
    print("2. Migrasi database")
    print("3. Export data")
    print("4. Import data")
    print("5. Sync production ke development")
    print("6. Jalankan server development")
    print("7. Buat admin user")
    print("8. Backup database")
    print("9. Set environment")
    print("0. Keluar")

def set_environment():
    """Set Flask environment"""
    print("\nPilih environment:")
    print("1. Development")
    print("2. Production")
    print("3. Testing")
    
    choice = input("\nPilihan: ")
    
    env_map = {
        '1': 'development',
        '2': 'production',
        '3': 'testing'
    }
    
    if choice in env_map:
        os.environ['FLASK_ENV'] = env_map[choice]
        print(f"✅ Environment set to: {env_map[choice]}")
    else:
        print("❌ Pilihan tidak valid")

def run_command(command):
    """Jalankan command dan tampilkan output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def setup_database():
    """Setup database baru"""
    print_header("SETUP DATABASE")
    
    # Konfirmasi
    current_env = os.environ.get('FLASK_ENV', 'development')
    print(f"⚠️  Akan membuat database untuk environment: {current_env}")
    
    response = input("\nLanjutkan? (y/n): ")
    if response.lower() != 'y':
        print("Setup dibatalkan.")
        return
    
    # Jalankan setup
    run_command(f"{sys.executable} setup_database.py")

def migrate_database():
    """Migrasi database"""
    print_header("MIGRASI DATABASE")
    run_command(f"{sys.executable} migrate_database.py")

def export_data():
    """Export data"""
    print_header("EXPORT DATA")
    run_command(f"{sys.executable} export_import_data.py export")

def import_data():
    """Import data"""
    print_header("IMPORT DATA")
    
    # List available export files
    export_files = list(Path('.').glob('*_data_export_*.json'))
    
    if not export_files:
        print("❌ Tidak ada file export yang ditemukan")
        return
    
    print("File export yang tersedia:")
    for i, file in enumerate(export_files, 1):
        print(f"{i}. {file.name}")
    
    choice = input("\nPilih file (nomor): ")
    
    try:
        file_index = int(choice) - 1
        if 0 <= file_index < len(export_files):
            filename = str(export_files[file_index])
            
            # Pilih mode
            print("\nMode import:")
            print("1. Merge (default) - Skip data yang sudah ada")
            print("2. Replace - Hapus data lama, ganti dengan yang baru")
            
            mode_choice = input("Pilihan (1/2): ") or '1'
            mode = 'merge' if mode_choice == '1' else 'replace'
            
            run_command(f"{sys.executable} export_import_data.py import {filename} {mode}")
        else:
            print("❌ Pilihan tidak valid")
    except ValueError:
        print("❌ Input tidak valid")

def sync_prod_to_dev():
    """Sync production ke development"""
    print_header("SYNC PRODUCTION TO DEVELOPMENT")
    run_command(f"{sys.executable} export_import_data.py sync-prod-to-dev")

def run_server():
    """Jalankan server development"""
    print_header("RUN DEVELOPMENT SERVER")
    print("Starting Flask development server...")
    print("Press Ctrl+C to stop\n")
    
    try:
        subprocess.run([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\nServer stopped.")

def create_admin():
    """Buat admin user"""
    print_header("CREATE ADMIN USER")
    
    from werkzeug.security import generate_password_hash
    from config import get_config
    import sqlite3
    
    username = input("Username (default: admin): ") or 'admin'
    password = input("Password (default: password123): ") or 'password123'
    
    config = get_config()
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        conn.commit()
        print(f"\n✅ Admin user '{username}' berhasil dibuat!")
    except sqlite3.IntegrityError:
        print(f"\n⚠️  Username '{username}' sudah ada")
    finally:
        conn.close()

def backup_database():
    """Backup database"""
    print_header("BACKUP DATABASE")
    
    from config import get_config
    import shutil
    from datetime import datetime
    
    config = get_config()
    if not os.path.exists(config.DATABASE_PATH):
        print("❌ Database tidak ditemukan")
        return
    
    # Buat nama backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{os.environ.get('FLASK_ENV', 'development')}_{timestamp}.db"
    backup_path = os.path.join('backups', backup_name)
    
    # Buat folder backups jika belum ada
    os.makedirs('backups', exist_ok=True)
    
    # Copy database
    shutil.copy2(config.DATABASE_PATH, backup_path)
    print(f"✅ Backup berhasil: {backup_path}")

def main():
    """Main function"""
    # Load .env jika ada
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
    
    while True:
        print_menu()
        choice = input("\nPilihan: ")
        
        if choice == '0':
            print("\nTerima kasih! 👋")
            break
        elif choice == '1':
            setup_database()
        elif choice == '2':
            migrate_database()
        elif choice == '3':
            export_data()
        elif choice == '4':
            import_data()
        elif choice == '5':
            sync_prod_to_dev()
        elif choice == '6':
            run_server()
        elif choice == '7':
            create_admin()
        elif choice == '8':
            backup_database()
        elif choice == '9':
            set_environment()
        else:
            print("❌ Pilihan tidak valid")
        
        input("\nTekan Enter untuk melanjutkan...")

if __name__ == '__main__':
    main()