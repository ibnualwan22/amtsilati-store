# config.py

import os
from pathlib import Path

# Base directory aplikasi
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Konfigurasi dasar aplikasi"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'kunci-rahasia-yang-sangat-sulit-ditebak')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16MB

    # Konfigurasi Upload Folder
    # (Disesuaikan di kelas bawahnya)
    UPLOAD_FOLDER = ''

    # Konfigurasi Database MySQL
    # (Disesuaikan di kelas bawahnya)
    MYSQL_HOST = '165.22.106.176'
    MYSQL_USER = 'alan'
    MYSQL_PASSWORD = 'alan'
    MYSQL_PORT = 3306
    MYSQL_DB = '' # Akan diisi di kelas development/production

    # API Keys
    BITESHIP_API_KEY = os.environ.get('BITESHIP_API_KEY',
        "biteship_live.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiYW10c2lsYXRpIHN0b3JlIiwidXNlcklkIjoiNjg2NWNhNGI4MzA3ZjgwMDEzNzY5NWQ5IiwiaWF0IjoxNzUxNjEwMzQ1fQ.hJAwHsYKTUWmhB6UvOeoLHGFIq0OA7y3yEAW4U5pwBA")
    BITESHIP_BASE_URL = "https://api.biteship.com"

class DevelopmentConfig(Config):
    """Konfigurasi untuk development/lokal"""
    DEBUG = True
    TESTING = False
    MYSQL_DB = 'as_store_dev' # Database untuk development
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_dev')

class ProductionConfig(Config):
    """Konfigurasi untuk production"""
    DEBUG = False
    TESTING = False
    MYSQL_DB = 'as_store_prod' # Database untuk production

    # Jika di Fly.io, gunakan path persistent volume
    if os.environ.get('FLY_APP_NAME'):
        UPLOAD_FOLDER = '/data/uploads'
    else:
        # Fallback untuk production non-Fly.io
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_prod')

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