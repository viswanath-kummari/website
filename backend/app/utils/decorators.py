from functools import wraps
from flask import session, request, jsonify, redirect, url_for, g
import jwt
from backend.app.config import Config
from backend.app.db import query_one

def get_current_user():
    """
    Extracts the current authenticated user from session or JWT bearer token.
    Attaches user record to Flask's g.user.
    """
    if hasattr(g, 'user') and g.user is not None:
        return g.user

    user = None
    user_id = None

    # 1. Check Authorization Bearer header (for mobile / API clients)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            user_id = payload.get('sub')
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    # 2. Check Flask session (for web browser clients)
    elif 'user_id' in session:
        user_id = session.get('user_id')

    if user_id:
        user = query_one(
            "SELECT id, email, full_name, phone, role, is_active FROM public.profiles WHERE id = %s;",
            (str(user_id),)
        )
        if user and user.get('is_active'):
            g.user = user
            return user

    g.user = None
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            # Check if this is an API request or browser request
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
            return redirect(url_for('auth.login_landing', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
                return redirect(url_for('auth.login_landing', next=request.url))
            
            if user.get('role') != required_role:
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'Forbidden', 'message': f'Access restricted to {required_role}'}), 403
                # Redirect to appropriate home page for user's actual role
                if user.get('role') == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user.get('role') == 'employee':
                    return redirect(url_for('employee.dashboard'))
                else:
                    return redirect(url_for('customer.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def roles_allowed(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
                return redirect(url_for('auth.login_landing', next=request.url))
            
            if user.get('role') not in allowed_roles:
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'error': 'Forbidden', 'message': 'Access restricted for your role'}), 403
                if user.get('role') == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user.get('role') == 'employee':
                    return redirect(url_for('employee.dashboard'))
                else:
                    return redirect(url_for('customer.home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

