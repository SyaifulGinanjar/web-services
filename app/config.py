import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env dari root project (tidak menimpa env var yang sudah di-set, mis. di Vercel)
load_dotenv(BASE_DIR.parent / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


def env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'

    SECRET_KEY = os.getenv('SECRET_KEY')

    # Session / cookie
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', False)
    PERMANENT_SESSION_LIFETIME = env_int('SESSION_LIFETIME_MINUTES', 480) * 60

    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = env_int('DB_PORT', 3306)
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', '')
    DB_CONNECT_TIMEOUT = env_int('DB_CONNECT_TIMEOUT', 10)

    # App
    APP_NAME = os.getenv('APP_NAME', 'Data Service')
    PER_PAGE_DEFAULT = env_int('PER_PAGE_DEFAULT', 10)
    PER_PAGE_OPTIONS = (10, 25, 50, 100)

    # Upload
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER') or str(BASE_DIR / 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = env_int('MAX_UPLOAD_MB', 5) * 1024 * 1024

    @classmethod
    def validate(cls):
        if not cls.SECRET_KEY:
            if cls.DEBUG:
                # Development: pakai key acak supaya tetap jalan (session hilang tiap restart)
                cls.SECRET_KEY = secrets.token_hex(32)
            else:
                raise RuntimeError('SECRET_KEY wajib di-set di environment untuk production.')
        if not cls.DB_NAME:
            raise RuntimeError('DB_NAME belum di-set. Lihat .env.example.')


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test'
    WTF_CSRF_ENABLED = False
    DB_NAME = 'test'
