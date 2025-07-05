#!/bin/bash

# Quickstart script untuk Amtsilati Store
# Untuk memulai development dengan cepat

echo "🚀 AMTSILATI STORE - QUICKSTART"
echo "================================"

# Cek Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 tidak ditemukan. Silakan install Python 3 terlebih dahulu."
    exit 1
fi

echo "✓ Python 3 ditemukan"

# Buat virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Membuat virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment dibuat"
else
    echo "✓ Virtual environment sudah ada"
fi

# Activate virtual environment
echo "🔄 Mengaktifkan virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Buat file .env dari template
if [ ! -f ".env" ]; then
    echo "📝 Membuat file .env..."
    cp .env.example .env
    echo "✓ File .env dibuat. Silakan edit sesuai kebutuhan."
else
    echo "✓ File .env sudah ada"
fi

# Setup database development
echo "🗄️ Setup database development..."
export FLASK_ENV=development
python setup_database.py

# Jalankan migrasi
echo "🔄 Menjalankan migrasi database..."
python migrate_database.py

echo ""
echo "✅ SETUP SELESAI!"
echo ""
echo "Untuk menjalankan aplikasi:"
echo "1. Aktifkan virtual environment: source venv/bin/activate"
echo "2. Jalankan server: python app.py"
echo ""
echo "Atau gunakan management script:"
echo "python manage.py"
echo ""
echo "Login admin default:"
echo "Username: admin"
echo "Password: password123"
echo ""
echo "Akses aplikasi di: http://localhost:5001"