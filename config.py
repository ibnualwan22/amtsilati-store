# config.py

import os
from pathlib import Path

# Base directory aplikasi
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Konfigurasi dasar aplikasi"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'kunci-rahasia-yang-sangat-sulit-ditebak')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API Keys (tetap sama)
    BITESHIP_API_KEY = os.environ.get('BITESHIP_API_KEY', "biteship_live...")
    BITESHIP_BASE_URL = "https://api.biteship.com"

class DevelopmentConfig(Config):
    """Konfigurasi untuk development/lokal"""
    DEBUG = True
    TESTING = False
    
    # --- BAGIAN PERBAIKAN DIMULAI DI SINI ---
    
    # 1. Tetap sediakan variabel individual untuk dibaca oleh get_db_connection()
    MYSQL_HOST = os.environ.get('DB_HOST')
    MYSQL_USER = os.environ.get('DB_USER')
    MYSQL_PASSWORD = os.environ.get('DB_PASS')
    MYSQL_PORT = int(os.environ.get('DB_PORT', 3306))
    #MYSQL_DB = 'as_store_dev'
    MYSQL_DB = os.environ.get('DB_NAME', 'as_store_dev')  # Pastikan ini adalah string


    # 2. Tetap sediakan URI lengkap untuk dibaca oleh Flask-Migrate
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    
    # --- SELESAI PERBAIKAN ---

    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_dev')

class ProductionConfig(Config):
    """Konfigurasi untuk production"""
    DEBUG = False
    TESTING = False
    
    # --- TERAPKAN PERBAIKAN YANG SAMA DI SINI ---
    
    # 1. Variabel individual
    MYSQL_HOST = os.environ.get('DB_HOST')
    MYSQL_USER = os.environ.get('DB_USER')
    MYSQL_PASSWORD = os.environ.get('DB_PASS')
    MYSQL_PORT = int(os.environ.get('DB_PORT', 3306))
    #MYSQL_DB = 'as_store_prod'
    MYSQL_DB = os.environ.get('DB_NAME', 'as_store_prod')  # Pastikan ini adalah string

    # 2. URI Lengkap
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

    # --- PERBAIKAN DI SINI ---
    # Tentukan UPLOAD_FOLDER berdasarkan environment FLY_APP_NAME
    if os.environ.get('FLY_APP_NAME'):
        UPLOAD_FOLDER = '/data/uploads'
    else:
        # Fallback untuk production non-Fly.io
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_prod')

    # --- SELESAI PERBAIKAN ---

class TestingConfig(Config):
    """Konfigurasi untuk testing - menggunakan SQLite in-memory"""
    TESTING = True
    # Untuk testing, kita tetap bisa pakai SQLite in-memory agar cepat
    DATABASE_PATH = ':memory:'
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_test')


# Dictionary untuk memilih config berdasarkan environment
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Mengambil konfigurasi berdasarkan environment variable"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, config_by_name['default'])