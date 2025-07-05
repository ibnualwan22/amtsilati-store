# Panduan Manajemen Database

## Pemisahan Database Lokal dan Produksi

Aplikasi ini sudah dikonfigurasi untuk memisahkan database lokal dan produksi secara otomatis berdasarkan environment.

### 1. Struktur Database

- **Development**: `instance/store_dev.db`
- **Production**: `/data/store.db` (di Fly.io) atau `instance/store_prod.db`
- **Testing**: In-memory database

### 2. Setup Awal

#### A. Setup Database Development (Lokal)

```bash
# Set environment ke development (default)
export FLASK_ENV=development

# Atau gunakan file .env
echo "FLASK_ENV=development" > .env

# Setup database
python setup_database.py

# Output:
# Database akan dibuat di: instance/store_dev.db
```

#### B. Setup Database Production

```bash
# Set environment ke production
export FLASK_ENV=production

# Setup database production
python setup_database.py production

# Output:
# Database akan dibuat di: /data/store.db (Fly.io) atau instance/store_prod.db
```

### 3. Menjalankan Aplikasi

#### Development
```bash
# Pastikan FLASK_ENV=development
export FLASK_ENV=development

# Jalankan aplikasi
python app.py

# Aplikasi akan menggunakan database: instance/store_dev.db
```

#### Production
```bash
# Pastikan FLASK_ENV=production
export FLASK_ENV=production

# Jalankan aplikasi
python app.py

# Aplikasi akan menggunakan database production
```

### 4. Migrasi Database

Untuk melakukan perubahan struktur database tanpa kehilangan data:

```bash
# Migrasi database development
export FLASK_ENV=development
python migrate_database.py

# Migrasi database production (hati-hati!)
export FLASK_ENV=production
python migrate_database.py production
```

**Fitur migrasi:**
- Otomatis membuat backup sebelum migrasi
- Tracking migrasi yang sudah dijalankan
- Rollback otomatis jika terjadi error

### 5. Import/Export Data

#### Export dari Production
```bash
# Di server production
export FLASK_ENV=production
python export_production_data.py
# Akan menghasilkan file: production_data_export_TIMESTAMP.sql
```

#### Import ke Development
```bash
# Di lokal
export FLASK_ENV=development
python import_production_data.py production_data_export_TIMESTAMP.sql
```

### 6. File Environment (.env)

Buat file `.env` di root project:

```env
# Development
FLASK_ENV=development

# Production
# FLASK_ENV=production
# DATABASE_PATH=/custom/path/to/database.db
# SECRET_KEY=your-production-secret-key
```

### 7. Deploy ke Production (Fly.io)

File `fly.toml` sudah dikonfigurasi dengan mount volume:

```toml
[mounts]
  source = "amtsilati_data"
  destination = "/data"
```

Database production akan tersimpan di `/data/store.db` yang persistent.

### 8. Best Practices

1. **Jangan pernah** copy database production ke development secara langsung
2. **Selalu** backup database sebelum migrasi
3. **Gunakan** environment variables untuk konfigurasi
4. **Test** semua perubahan di development dulu
5. **Dokumentasikan** setiap perubahan struktur database

### 9. Troubleshooting

#### Cek Environment dan Database Path
```bash
# Tambahkan route debug di app.py (sudah ada)
# Akses: http://localhost:5001/debug/check-config
```

#### Reset Database Development
```bash
export FLASK_ENV=development
rm instance/store_dev.db
python setup_database.py
```

#### Restore dari Backup
```bash
# List backup files
ls instance/*.backup_*

# Restore
cp instance/store_dev.db.backup_20250105_120000 instance/store_dev.db
```

### 10. Struktur File

```
project/
├── config.py              # Konfigurasi environment
├── app.py                 # Aplikasi utama (updated)
├── setup_database.py      # Setup database baru
├── migrate_database.py    # Migrasi database
├── .env                   # Environment variables (git ignored)
├── .env.example          # Contoh environment variables
├── instance/             # Folder database
│   ├── store_dev.db      # Database development
│   └── store_prod.db     # Database production (jika tidak di Fly.io)
└── uploads/              # Folder upload files
    ├── uploads_dev/      # Upload development
    └── uploads_prod/     # Upload production
```

### 11. Git Ignore

Pastikan `.gitignore` berisi:

```
instance/
*.db
.env
uploads/
uploads_dev/
uploads_prod/
__pycache__/
*.pyc
```

---

Dengan setup ini, Anda bisa bekerja di development tanpa khawatir merusak data production!