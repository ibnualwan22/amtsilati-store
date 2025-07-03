import sqlite3

conn = sqlite3.connect('instance/store.db')
cursor = conn.cursor()

try:
    # Menambahkan kolom tanggal transfer ke tabel online_sales
    cursor.execute('ALTER TABLE online_sales ADD COLUMN transfer_date TEXT')
    print("Kolom 'transfer_date' berhasil ditambahkan ke tabel online_sales.")
except Exception as e:
    print("Gagal menambahkan kolom 'transfer_date':", e)

conn.commit()
conn.close()