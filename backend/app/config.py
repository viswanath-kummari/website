import os
from pathlib import Path
from dotenv import load_dotenv

# Load root project .env.local
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env.local")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        if os.getenv('VERCEL'):
            raise RuntimeError('SECRET_KEY environment variable is required')
        SECRET_KEY = 'freshcut-local-development-secret-key'
    
    # Database
    DB_HOST = os.getenv('DB_HOST')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Supabase API (Optional)
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://fkcvsjxdbkghtghpdmwo.supabase.co')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    
    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = bool(os.getenv('VERCEL'))
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    
    # Shop Business Rules
    ALLOWED_CATEGORIES = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    ALLOWED_UNITS = ['KG', 'PCS']
    ALLOWED_PAYMENT_METHODS = ['Cash', 'UPI', 'Card', 'Mixed', 'Credit']
    ALLOWED_ORDER_STATUSES = ['Pending', 'Accepted', 'Ready for Collection', 'Completed', 'Cancelled']
