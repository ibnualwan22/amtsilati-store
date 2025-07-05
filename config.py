import os
from pathlib import Path

# Base directory aplikasi
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Konfigurasi dasar aplikasi"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'kunci-rahasia-yang-sangat-sulit-ditebak')
    
    # Upload folder configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max 16MB file size
    
    # API Keys
    BITESHIP_API_KEY = os.environ.get('BITESHIP_API_KEY', 
        "biteship_live.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiYW10c2lsYXRpIHN0b3JlIiwidXNlcklkIjoiNjg2NWNhNGI4MzA3ZjgwMDEzNzY5NWQ5IiwiaWF0IjoxNzUxNjEwMzQ1fQ.hJAwHsYKTUWmhB6UvOeoLHGFIq0OA7y3yEAW4U5pwBA")
    BITESHIP_BASE_URL = "https://api.biteship.com"

class DevelopmentConfig(Config):
    """Konfigurasi untuk development/lokal"""
    DEBUG = True
    TESTING = False
    
    # Database lokal di folder instance
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'store_dev.db')
    
    # Upload folder untuk development
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_dev')

class ProductionConfig(Config):
    """Konfigurasi untuk production"""
    DEBUG = False
    TESTING = False
    
    # Database production di persistent volume
    # Jika di Fly.io, gunakan /data yang sudah di-mount
    if os.environ.get('FLY_APP_NAME'):
        DATABASE_PATH = '/data/store.db'
        UPLOAD_FOLDER = '/data/uploads'
    else:
        # Fallback untuk production non-Fly.io
        DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'store_prod.db')
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_prod')
    
    # Override dengan environment variable jika ada
    DATABASE_PATH = os.environ.get('DATABASE_PATH', DATABASE_PATH)

class TestingConfig(Config):
    """Konfigurasi untuk testing"""
    DEBUG = False
    TESTING = True
    
    # Database testing di memory
    DATABASE_PATH = ':memory:'
    
    # Upload folder untuk testing
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_test')

# Dictionary untuk memilih config berdasarkan environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Mengambil konfigurasi berdasarkan environment variable"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])