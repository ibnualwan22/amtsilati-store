#!/bin/bash

# Script untuk melakukan migrasi database di Fly.io (FIXED VERSION)
# Usage: ./fly_migrate_fixed.sh

echo "🚀 FLY.IO DATABASE MIGRATION"
echo "============================"

# Cek apakah fly CLI terinstall
if ! command -v fly &> /dev/null; then
    echo "❌ Fly CLI tidak ditemukan. Install dulu: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Cek apakah sudah login
if ! fly auth whoami &> /dev/null; then
    echo "❌ Belum login ke Fly. Jalankan: fly auth login"
    exit 1
fi

# Tampilkan app yang akan di-migrate
APP_NAME=$(fly status --json | grep -o '"Name":"[^"]*' | grep -o '[^"]*$' | head -1)
echo "📱 App: $APP_NAME"

# Konfirmasi
echo ""
echo "⚠️  PERHATIAN:"
echo "- Pastikan sudah deploy code terbaru"
echo "- Database akan di-backup otomatis"
echo "- Downtime minimal selama proses"
echo ""
read -p "Lanjutkan migrasi? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migrasi dibatalkan"
    exit 1
fi

echo ""
echo "📦 Step 1: Backup database..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
fly ssh console -C "sh -c 'cp /data/store.db /data/store.db.backup_fly_${TIMESTAMP} && echo \"✅ Backup created: store.db.backup_fly_${TIMESTAMP}\"'"

echo ""
echo "🔄 Step 2: Menjalankan migrasi..."
fly ssh console -C "sh -c 'cd /app && export FLASK_ENV=production && echo y | python migrate_database.py'"

echo ""
echo "✅ Step 3: Verifikasi..."
fly ssh console -C "sh -c 'cd /app && export FLASK_ENV=production && python migrate_database.py verify'"

echo ""
echo "📋 Step 4: Cek backup files..."
fly ssh console -C "sh -c 'ls -la /data/*.backup* | tail -n 5'"

echo ""
echo "✅ MIGRASI SELESAI!"
echo ""
echo "Jika ada masalah, restore dengan:"
echo "fly ssh console"
echo "cp /data/store.db.backup_fly_${TIMESTAMP} /data/store.db"