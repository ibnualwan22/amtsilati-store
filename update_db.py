import sqlite3

conn = sqlite3.connect('instance/store.db')
cursor = conn.cursor()

try:
    # Menambahkan kolom alamat (address)
    cursor.execute('ALTER TABLE offline_buyers ADD COLUMN address TEXT')
    print("Kolom 'address' berhasil ditambahkan.")
except Exception as e:
    print("Gagal menambahkan kolom 'address':", e)

try:
    # Menambahkan kolom asrama (dormitory)
    cursor.execute('ALTER TABLE offline_buyers ADD COLUMN dormitory TEXT')
    print("Kolom 'dormitory' berhasil ditambahkan.")
except Exception as e:
    print("Gagal menambahkan kolom 'dormitory':", e)

conn.commit()
conn.close()