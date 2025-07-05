import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash
from config import get_config

def create_database():
    """Membuat database dan tabel-tabel yang diperlukan"""
    # Dapatkan konfigurasi sesuai environment
    config = get_config()
    database_path = config.DATABASE_PATH
    
    # Buat direktori jika belum ada
    database_dir = os.path.dirname(database_path)
    if database_dir and not os.path.exists(database_dir):
        os.makedirs(database_dir)
        print(f"Created directory: {database_dir}")
    
    print(f"Creating database at: {database_path}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # Koneksi ke database
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    
    # Membuat tabel untuk data kitab dengan kolom lengkap
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        price REAL NOT NULL,
        availability TEXT NOT NULL DEFAULT 'Tersedia',
        link_ig TEXT,
        link_wa TEXT,
        link_shopee TEXT,
        link_tiktok TEXT,
        image_filename TEXT
    )
    ''')
    print("✓ Tabel 'books' berhasil dibuat/diperiksa")
    
    # Tabel untuk pembeli offline dengan kolom tambahan
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS offline_buyers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        address TEXT,
        dormitory TEXT
    )
    ''')
    print("✓ Tabel 'offline_buyers' berhasil dibuat/diperiksa")
    
    # Tabel untuk penjualan offline
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS offline_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER,
        book_id INTEGER,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES offline_buyers (id),
        FOREIGN KEY (book_id) REFERENCES books (id)
    )
    ''')
    print("✓ Tabel 'offline_sales' berhasil dibuat/diperiksa")
    
    # Tabel untuk penjualan online dengan kolom tambahan
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS online_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_name TEXT NOT NULL,
        buyer_address TEXT NOT NULL,
        book_id INTEGER,
        quantity INTEGER NOT NULL DEFAULT 1,
        shipping_cost REAL NOT NULL,
        total_price REAL NOT NULL,
        transfer_date DATE,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books (id)
    )
    ''')
    print("✓ Tabel 'online_sales' berhasil dibuat/diperiksa")
    
    # Tabel untuk admin users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
    ''')
    print("✓ Tabel 'users' berhasil dibuat/diperiksa")
    
    connection.commit()
    connection.close()
    print(f"\n✅ Database berhasil dibuat di: {database_path}")

def create_admin_user(username='admin', password='password123'):
    """Membuat user admin default"""
    config = get_config()
    database_path = config.DATABASE_PATH
    
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    
    # Generate password hash
    password_hash = generate_password_hash(password)
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        print(f"\n✅ Admin user berhasil dibuat:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
    except sqlite3.IntegrityError:
        print(f"\n⚠️  Username '{username}' sudah ada di database.")
    
    connection.commit()
    connection.close()

def add_sample_data():
    """Menambahkan data sample untuk development"""
    config = get_config()
    
    # Hanya tambahkan sample data jika di development
    if os.environ.get('FLASK_ENV') != 'development':
        print("\n⚠️  Sample data hanya ditambahkan di environment development")
        return
    
    database_path = config.DATABASE_PATH
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()
    
    # Sample data kitab
    sample_books = [
        ('Kitab Amtsilati 1', 25000, 'Tersedia', 'http://shopee.co.id/link1'),
        ('Kitab Jurumiyyah', 30000, 'Tersedia', 'http://shopee.co.id/link2'),
        ('Kitab Imrithi', 35000, 'Tidak Tersedia', 'http://shopee.co.id/link3'),
        ('Kitab Alfiyah', 40000, 'Tersedia', 'http://shopee.co.id/link4'),
        ('Kitab Nahwu Wadhih', 28000, 'Tersedia', 'http://shopee.co.id/link5')
    ]
    
    for book in sample_books:
        try:
            cursor.execute(
                "INSERT INTO books (name, price, availability, link_shopee) VALUES (?, ?, ?, ?)",
                book
            )
            print(f"✓ Added: {book[0]}")
        except sqlite3.IntegrityError:
            print(f"⚠️  Skip: {book[0]} (sudah ada)")
    
    connection.commit()
    connection.close()
    print("\n✅ Sample data berhasil ditambahkan")

def main():
    """Main function untuk setup database"""
    print("=== SETUP DATABASE ===")
    
    # Cek apakah ada argumen environment
    if len(sys.argv) > 1:
        os.environ['FLASK_ENV'] = sys.argv[1]
        print(f"Setting FLASK_ENV to: {sys.argv[1]}")
    
    # Create database dan tabel
    create_database()
    
    # Create admin user
    create_admin_user()
    
    # Tanya apakah ingin menambahkan sample data
    if os.environ.get('FLASK_ENV', 'development') == 'development':
        response = input("\nApakah ingin menambahkan sample data? (y/n): ")
        if response.lower() == 'y':
            add_sample_data()
    
    print("\n✅ Setup database selesai!")

if __name__ == '__main__':
    main()