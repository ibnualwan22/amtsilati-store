import sqlite3
import os
from werkzeug.security import generate_password_hash

# --- KONFIGURASI ---
# Pastikan path ini sama dengan yang ada di config.py Anda untuk production
DB_PATH = '/data/store_prod.db' 

def create_tables(conn):
    """Fungsi untuk membuat semua tabel yang dibutuhkan."""
    cursor = conn.cursor()
    
    print("Mengeksekusi perintah CREATE TABLE...")

    # 1. Tabel Pengguna (Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );
    """)
    print("- Tabel 'users' siap.")

    # 2. Tabel Buku/Kitab
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        price REAL NOT NULL,
        availability TEXT,
        link_ig TEXT,
        link_wa TEXT,
        link_shopee TEXT,
        link_tiktok TEXT,
        image_filename TEXT
    );
    """)
    print("- Tabel 'books' siap.")

    # 3. Tabel Pembeli Offline
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_buyers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        address TEXT,
        dormitory TEXT
    );
    """)
    print("- Tabel 'offline_buyers' siap.")

    # 4. Tabel Penjualan Offline
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES offline_buyers (id),
        FOREIGN KEY (book_id) REFERENCES books (id)
    );
    """)
    print("- Tabel 'offline_sales' siap.")

    # 5. Tabel Penjualan Online
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS online_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_name TEXT NOT NULL,
        buyer_address TEXT NOT NULL,
        book_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        shipping_cost REAL,
        total_price REAL NOT NULL,
        transfer_date DATE,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books (id)
    );
    """)
    print("- Tabel 'online_sales' siap.")

    conn.commit()
    print("\nSemua tabel berhasil disiapkan.")

    # 5. Tabel Penjualan Online
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS online_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_name TEXT NOT NULL,
        buyer_address TEXT NOT NULL,
        book_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        shipping_cost REAL,
        total_price REAL NOT NULL,
        transfer_date DATE,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books (id)
    );
    """)
    print("- Tabel 'online_sales' siap.")

    # 6. Tabel Rekap Kas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cash_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL CHECK(type IN ('debit', 'kredit')),
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        record_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("- Tabel 'cash_records' siap.")

    conn.commit()
    print("\nSemua tabel berhasil disiapkan.")

def create_default_admin(conn):
    """Fungsi untuk membuat pengguna admin default jika belum ada."""
    cursor = conn.cursor()
    
    # Cek apakah admin sudah ada
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if cursor.fetchone() is None:
        print("\nMembuat pengguna admin default...")
        # Hashing password
        password = 'admin' # Ganti password ini jika perlu
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ('admin', hashed_password)
        )
        conn.commit()
        print(f"""
        Pengguna admin berhasil dibuat.
        ===============================
        Username: admin
        Password: {password}
        ===============================
        Harap segera ganti password setelah login!
        """)
    else:
        print("\nPengguna 'admin' sudah ada.")

def main():
    """Fungsi utama untuk menjalankan inisialisasi."""
    # Gunakan config untuk mendapatkan path yang benar
    config = get_config()
    DB_PATH = config.DATABASE_PATH
    
    # Buat direktori jika belum ada
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created directory: {db_dir}")
    
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Berhasil terhubung ke database di {DB_PATH}")
        
        create_tables(conn)
        create_default_admin(conn)

    except Exception as e:
        print(f"Terjadi error: {e}")
    finally:
        if conn:
            conn.close()
            print("\nKoneksi database ditutup. Inisialisasi selesai.")

if __name__ == '__main__':
    main()
