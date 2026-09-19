import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration settings."""
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'tamper-proof-cert-super-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'certificates.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    CERTIFICATES_FOLDER = os.path.join(BASE_DIR, 'generated_certificates')
    QRCODE_FOLDER = os.path.join(BASE_DIR, 'static', 'qrcodes')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    DEFAULT_ADMIN_USERNAME = 'admin'
    DEFAULT_ADMIN_PASSWORD = 'admin123'
    DEFAULT_ADMIN_EMAIL = 'admin@institute.edu'
    DEFAULT_ADMIN_NAME = 'System Administrator'
