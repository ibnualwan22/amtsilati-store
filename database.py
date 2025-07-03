import sqlite3

connection = sqlite3.connect('instance/store.db')
cursor = connection.cursor()

# --- MODIFIKASI DI SINI ---
# Membuat tabel untuk data kitab dengan kolom baru
cursor.execute('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    price REAL NOT NULL,
    availability TEXT NOT NULL DEFAULT 'Tersedia',
    link_ig TEXT,
    link_wa TEXT,
    link_shopee TEXT,
    link_tiktok TEXT
)
''')
# -------------------------

# Tabel lainnya tetap sama
cursor.execute('''
CREATE TABLE IF NOT EXISTS offline_buyers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
''')
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
cursor.execute('''
CREATE TABLE IF NOT EXISTS online_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_name TEXT NOT NULL,
    buyer_address TEXT NOT NULL,
    book_id INTEGER,
    shipping_cost REAL NOT NULL,
    total_price REAL NOT NULL,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books (id)
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

print("Database dan tabel berhasil dibuat ulang di instance/store.db")