import sqlite3

connection = sqlite3.connect('instance/store.db')
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

# Tabel untuk pembeli offline dengan kolom tambahan
cursor.execute('''
CREATE TABLE IF NOT EXISTS offline_buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    address TEXT,
    dormitory TEXT
)
''')

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

# Tabel untuk admin users
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
)
''')

# Contoh data kitab awal dengan kolom baru
try:
    cursor.execute("""
        INSERT INTO books (name, price, availability, link_shopee) VALUES (?, ?, ?, ?)
        """, ('Kitab Amtsilati 1', 25000, 'Tersedia', 'http://shopee.co.id/link1'))
    cursor.execute("""
        INSERT INTO books (name, price, availability, link_shopee) VALUES (?, ?, ?, ?)
        """, ('Kitab Jurumiyyah', 30000, 'Tersedia', 'http://shopee.co.id/link2'))
    cursor.execute("""
        INSERT INTO books (name, price, availability, link_shopee) VALUES (?, ?, ?, ?)
        """, ('Kitab Imrithi', 35000, 'Tidak Tersedia', 'http://shopee.co.id/link3'))
except sqlite3.IntegrityError:
    print("Contoh data kitab sudah ada.")

connection.commit()
connection.close()

print("Database dan tabel berhasil dibuat di instance/store.db")