import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'freshcut-retail-secret-key-prod-2026-secure-jwt')
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'aws-0-ap-south-1.pooler.supabase.com')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'postgres')
    DB_USER = os.getenv('DB_USER', 'postgres.fkcvsjxdbkghtghpdmwo')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'Viswanath@321')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Supabase API (Optional)
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://fkcvsjxdbkghtghpdmwo.supabase.co')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    
    # Session & Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in HTTPS production
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days
    
    # Shop Business Rules
    ALLOWED_CATEGORIES = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    ALLOWED_UNITS = ['KG', 'PCS']
    ALLOWED_PAYMENT_METHODS = ['Cash', 'UPI', 'Card', 'Mixed', 'Credit']
    ALLOWED_ORDER_STATUSES = ['Pending', 'Accepted', 'Ready for Collection', 'Completed', 'Cancelled']
