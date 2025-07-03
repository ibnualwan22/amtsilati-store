import sqlite3

conn = sqlite3.connect('instance/store.db')
cursor = conn.cursor()

try:
    # Menambahkan kolom jumlah dengan nilai default 1
    cursor.execute('ALTER TABLE online_sales ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1')
    print("Kolom 'quantity' berhasil ditambahkan ke tabel online_sales.")
except Exception as e:
    print("Gagal menambahkan kolom 'quantity':", e)

conn.commit()
conn.close()