import sqlite3

conn = sqlite3.connect('instance/store.db')
cursor = conn.cursor()

try:
    # Menambahkan kolom untuk nama file gambar
    cursor.execute('ALTER TABLE books ADD COLUMN image_filename TEXT')
    print("Kolom 'image_filename' berhasil ditambahkan ke tabel books.")
except Exception as e:
    print("Gagal menambahkan kolom 'image_filename':", e)

conn.commit()
conn.close()