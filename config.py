import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env file if present
load_dotenv(BASE_DIR / '.env')

class Config:
    """Base configuration."""
    APP_NAME = "Secure Live Tracker"
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-secure-tracker-3948572019')
    
    # Public Base URL for production sharing (Must be HTTPS public domain)
    PUBLIC_BASE_URL = (os.environ.get('PUBLIC_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL') or '').rstrip('/')
    
    # Database URL with fallback to local SQLite
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        db_path = BASE_DIR / 'database' / 'secure_tracker.db'
        os.makedirs(db_path.parent, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path.as_posix()}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Admin Credentials
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'AdminPass123!')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@securetracker.local')
    
    # Geolocation Provider Configuration
    GEOLOCATION_PROVIDER = os.environ.get('GEOLOCATION_PROVIDER', 'ipinfo')
    GEOLOCATION_FALLBACK_PROVIDER = os.environ.get('GEOLOCATION_FALLBACK_PROVIDER', 'ip-api')
    GEOLOCATION_API_KEY = os.environ.get('GEOLOCATION_API_KEY', '')
    MAXMIND_ACCOUNT_ID = os.environ.get('MAXMIND_ACCOUNT_ID', '')
    MAXMIND_LICENSE_KEY = os.environ.get('MAXMIND_LICENSE_KEY', '')

    # Reverse Proxy & Trusted Proxy Configuration
    BEHIND_PROXY = os.environ.get('BEHIND_PROXY', 'True').lower() in ('true', '1', 't')
    TRUSTED_PROXIES = os.environ.get('TRUSTED_PROXIES', '127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16')

    # Rate Limiting
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True

    # Security Cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 7200

    # Data Retention default in days
    DEFAULT_RETENTION_DAYS = int(os.environ.get('DEFAULT_RETENTION_DAYS', 90))

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    PUBLIC_BASE_URL = 'https://test-tracker.example.com'
    BEHIND_PROXY = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}
