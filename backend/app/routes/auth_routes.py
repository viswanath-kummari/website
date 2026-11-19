from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from backend.app.services.auth_service import authenticate, register_customer, change_user_password, update_user_profile
from backend.app.utils.decorators import login_required, get_current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/landing')
def login_landing():
    """Attractive 3-choice authentication landing page."""
    user = get_current_user()
    if user:
        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user['role'] == 'employee':
            return redirect(url_for('employee.dashboard'))
        else:
            return redirect(url_for('customer.home'))
    return render_template('auth/login_landing.html')

@auth_bp.route('/login/owner', methods=['GET', 'POST'])
def owner_login():
    """Owner / Admin login page and handler."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        success, message, user = authenticate(email, password, intended_role='admin')
        if success:
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = user['full_name']
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('admin.dashboard'))
        flash(message, "danger")
    return render_template('auth/owner_login.html')

@auth_bp.route('/login/employee', methods=['GET', 'POST'])
def employee_login():
    """Employee login page and handler."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        success, message, user = authenticate(email, password, intended_role='employee')
        if success:
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = user['full_name']
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('employee.dashboard'))
        flash(message, "danger")
    return render_template('auth/employee_login.html')

@auth_bp.route('/login/customer', methods=['GET', 'POST'])
def customer_login():
    """Customer storefront login page and handler."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        next_url = request.form.get('next') or request.args.get('next')
        success, message, user = authenticate(email, password, intended_role='customer')
        if success:
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = user['full_name']
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(next_url or url_for('customer.home'))
        flash(message, "danger")
    return render_template('auth/customer_login.html')

@auth_bp.route('/register/customer', methods=['GET', 'POST'])
def customer_register():
    """Customer self-registration page and handler."""
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return render_template('auth/customer_register.html')

        success, message, user = register_customer(name, phone, email, password)
        if success:
            session['user_id'] = user['id']
            session['user_role'] = user['role']
            session['user_name'] = user['full_name']
            flash("Your account has been created successfully! Welcome to Fresh Cut.", "success")
            return redirect(url_for('customer.home'))
        flash(message, "danger")
    return render_template('auth/customer_register.html')

@auth_bp.route('/switch/<role>')
def quick_switch_role(role):
    """
    All-in-One Instant Role Switcher.
    Allows 1-click switching between Owner, Employee, and Customer experiences from a single URL.
    """
    session.clear()
    role = role.lower()
    
    if role in ['admin', 'owner']:
        success, msg, user = authenticate('owner@freshcut.com', 'Owner@123', intended_role='admin')
        if success and user:
            session['user_id'] = user['id']
            session['user_role'] = 'admin'
            session['user_name'] = user['full_name']
            flash(f"Switched to Owner Mode (Logged in as {user['full_name']})", "success")
            return redirect(url_for('admin.dashboard'))
        else:
            flash(f"Could not switch to Owner: {msg}", "danger")
            return redirect(url_for('auth.login_landing'))
        
    elif role in ['employee', 'staff']:
        success, msg, user = authenticate('employee@freshcut.com', 'Employee@123', intended_role='employee')
        if success and user:
            session['user_id'] = user['id']
            session['user_role'] = 'employee'
            session['user_name'] = user['full_name']
            flash(f"Switched to Employee Counter POS (Logged in as {user['full_name']})", "info")
            return redirect(url_for('employee.pos_billing'))
        else:
            flash(f"Could not switch to Employee: {msg}", "danger")
            return redirect(url_for('auth.login_landing'))
        
    else:  # customer
        success, msg, user = authenticate('customer@freshcut.com', 'Customer@123', intended_role='customer')
        if success and user:
            session['user_id'] = user['id']
            session['user_role'] = 'customer'
            session['user_name'] = user['full_name']
            flash(f"Switched to Customer Storefront (Logged in as {user['full_name']})", "success")
            return redirect(url_for('customer.home'))
        else:
            flash(f"Could not switch to Customer: {msg}", "danger")
            return redirect(url_for('customer.home'))

@auth_bp.route('/logout')
def logout():
    """Clears session and redirects to authentication landing."""
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('auth.login_landing'))

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """REST API Login endpoint returning JWT for mobile / external clients."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    success, message, user = authenticate(email, password, intended_role=role)
    if not success:
        return jsonify({'success': False, 'message': message}), 401
    return jsonify({'success': True, 'message': message, 'data': user})

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """REST API Customer Registration endpoint."""
    data = request.get_json() or {}
    success, message, user = register_customer(
        data.get('name'), data.get('phone'), data.get('email'), data.get('password')
    )
    if not success:
        return jsonify({'success': False, 'message': message}), 400
    return jsonify({'success': True, 'message': message, 'data': user})

