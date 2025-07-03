import sqlite3
from werkzeug.security import generate_password_hash

# --- KONFIGURASI ADMIN DEFAULT ---
# Anda bisa mengubah username dan password ini sesuai keinginan
DEFAULT_USERNAME = 'admin'
DEFAULT_PASSWORD = 'password123'
# ---------------------------------

# Membuat koneksi ke database
connection = sqlite3.connect('instance/store.db')
cursor = connection.cursor()

# 1. Membuat tabel 'users' jika belum ada
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
)
''')
print("Tabel 'users' berhasil diperiksa/dibuat.")

# 2. Membuat hash dari password default
password_hash = generate_password_hash(DEFAULT_PASSWORD)

# 3. Memasukkan admin default ke dalam tabel
try:
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (DEFAULT_USERNAME, password_hash)
    )
    print(f"Admin default berhasil dibuat:")
    print(f"  -> Username: {DEFAULT_USERNAME}")
    print(f"  -> Password: {DEFAULT_PASSWORD}")
except sqlite3.IntegrityError:
    # Jika username 'admin' sudah ada, tidak melakukan apa-apa
    print(f"Username '{DEFAULT_USERNAME}' sudah ada di database. Tidak ada pengguna baru yang dibuat.")

# Simpan perubahan dan tutup koneksi
connection.commit()
connection.close()
