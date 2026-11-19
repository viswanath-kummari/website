import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from backend.app.config import Config
from backend.app.db import query_one, execute, execute_returning

def hash_password(password: str) -> str:
    """Hashes a password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """Checks a password against its bcrypt/pgcrypto hash."""
    if not hashed_password or not password:
        return False
    try:
        # Check standard bcrypt hash
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        # Fallback query via pgcrypto crypt() in PostgreSQL if needed
        res = query_one(
            "SELECT (crypt(%s, %s) = %s) AS match;",
            (password, hashed_password, hashed_password)
        )
        return bool(res and res.get('match'))

def generate_jwt_token(user: dict) -> str:
    """Generates a secure JWT token for mobile or REST API clients."""
    payload = {
        'sub': str(user['id']),
        'email': user['email'],
        'role': user['role'],
        'name': user['full_name'],
        'iat': datetime.now(timezone.utc),
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def authenticate(email: str, password: str, intended_role: str = None) -> tuple[bool, str, dict]:
    """
    Authenticates user by email & password.
    Enforces that the user's verified role matches the intended portal role if provided.
    Returns (success, message, user_data_with_token).
    """
    if not email or not password:
        return False, "Email and password are required.", {}

    user = query_one(
        "SELECT id, email, password_hash, full_name, phone, role, is_active FROM public.profiles WHERE LOWER(email) = LOWER(%s);",
        (email.strip(),)
    )

    if not user:
        return False, "Invalid email or password.", {}

    if not user.get('is_active'):
        return False, "Account has been deactivated. Please contact the administrator.", {}

    if not check_password(password, user.get('password_hash')):
        return False, "Invalid email or password.", {}

    # Strict role verification: If the user attempted to log in via Owner portal, ensure role is admin
    actual_role = user.get('role')
    if intended_role:
        if intended_role == 'admin' and actual_role != 'admin':
            return False, "Access denied: Unauthorized login attempt for Administrator portal.", {}
        elif intended_role == 'employee' and actual_role != 'employee':
            return False, "Access denied: This portal is reserved for shop employees only.", {}
        elif intended_role == 'customer' and actual_role != 'customer':
            return False, "Storefront customer login is for customers only. Staff and owners, please use your dedicated portal.", {}

    token = generate_jwt_token(user)

    user_info = {
        'id': str(user['id']),
        'email': user['email'],
        'full_name': user['full_name'],
        'phone': user['phone'],
        'role': actual_role,
        'token': token
    }

    return True, "Authentication successful.", user_info

def register_customer(name: str, phone: str, email: str, password: str) -> tuple[bool, str, dict]:
    """
    Registers a new customer. Customers can register independently.
    Creates both profile and customers table record.
    """
    name = (name or '').strip()
    phone = (phone or '').strip()
    email = (email or '').strip().lower()

    if not name or not phone or not email or not password:
        return False, "All fields (name, phone, email, password) are required.", {}

    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", {}

    # Check existing email
    existing_profile = query_one(
        "SELECT id FROM public.profiles WHERE LOWER(email) = LOWER(%s);",
        (email,)
    )
    if existing_profile:
        return False, "An account with this email address already exists.", {}

    pwd_hash = hash_password(password)

    # Insert profile with role 'customer'
    profile = execute_returning(
        """
        INSERT INTO public.profiles (email, password_hash, full_name, phone, role, is_active)
        VALUES (%s, %s, %s, %s, 'customer', TRUE)
        RETURNING id, email, full_name, phone, role, is_active;
        """,
        (email, pwd_hash, name, phone)
    )

    if not profile:
        return False, "Failed to create user profile. Please try again.", {}

    # Insert customer record
    execute(
        """
        INSERT INTO public.customers (profile_id, name, phone, email, address, outstanding_balance)
        VALUES (%s, %s, %s, %s, '', 0.00);
        """,
        (profile['id'], name, phone, email)
    )

    token = generate_jwt_token(profile)
    user_info = {
        'id': str(profile['id']),
        'email': profile['email'],
        'full_name': profile['full_name'],
        'phone': profile['phone'],
        'role': 'customer',
        'token': token
    }

    return True, "Registration successful.", user_info

def change_user_password(user_id: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Changes password for an authenticated user."""
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters."

    user = query_one(
        "SELECT password_hash FROM public.profiles WHERE id = %s;",
        (user_id,)
    )
    if not user or not check_password(old_password, user.get('password_hash')):
        return False, "Current password is incorrect."

    new_hash = hash_password(new_password)
    execute(
        "UPDATE public.profiles SET password_hash = %s, updated_at = NOW() WHERE id = %s;",
        (new_hash, user_id)
    )
    return True, "Password changed successfully."

def update_user_profile(user_id: str, full_name: str, phone: str) -> tuple[bool, str]:
    """Updates full name and phone."""
    execute(
        "UPDATE public.profiles SET full_name = %s, phone = %s, updated_at = NOW() WHERE id = %s;",
        (full_name.strip(), phone.strip(), user_id)
    )
    # Also update customer record if applicable
    execute(
        "UPDATE public.customers SET name = %s, phone = %s, updated_at = NOW() WHERE profile_id = %s;",
        (full_name.strip(), phone.strip(), user_id)
    )
    return True, "Profile updated successfully."
