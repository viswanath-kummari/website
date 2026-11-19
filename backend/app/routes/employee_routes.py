from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from backend.app.services.product_service import get_all_products
from backend.app.services.pos_service import create_sale_bill, get_sales_list, get_sale_by_invoice
from backend.app.services.order_service import get_orders_list, update_order_status, get_order_details
from backend.app.services.inventory_service import get_inventory_status
from backend.app.services.employee_service import get_employee_sales_summary
from backend.app.services.settings_service import get_shop_settings
from backend.app.services.auth_service import update_user_profile, change_user_password
from backend.app.utils.decorators import get_current_user, role_required

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.before_request
@role_required('employee')
def check_employee_access():
    """Guarantees all routes in this blueprint are restricted to active employees."""
    pass

@employee_bp.route('/dashboard')
def dashboard():
    """Employee operational dashboard."""
    user = get_current_user()
    summary = get_employee_sales_summary(user['id'])
    pending_orders = get_orders_list(status_filter='Pending', limit=5)
    products = get_all_products(active_only=True)
    settings = get_shop_settings()

    return render_template(
        'employee/dashboard.html',
        user=user,
        stats=summary['stats'],
        recent_bills=summary['recent_bills'],
        pending_orders=pending_orders,
        products=products,
        settings=settings
    )

@employee_bp.route('/pos')
def pos_billing():
    """Touch-friendly POS Billing Counter for Employees."""
    user = get_current_user()
    products = get_all_products(active_only=True)
    settings = get_shop_settings()
    return render_template('employee/pos.html', user=user, products=products, settings=settings)

@employee_bp.route('/sales')
def sales_history():
    """Employee's own billing history."""
    user = get_current_user()
    search = request.args.get('search')
    sales = get_sales_list(employee_id=user['id'], search=search, limit=50)
    settings = get_shop_settings()
    return render_template('employee/sales_history.html', user=user, sales=sales, settings=settings)

@employee_bp.route('/stock')
def stock_view():
    """Read-only view of stock availability for employees."""
    user = get_current_user()
    category = request.args.get('category')
    stock_items = get_inventory_status(category=category)
    settings = get_shop_settings()
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    return render_template(
        'employee/stock_view.html',
        user=user,
        stock_items=stock_items,
        categories=categories,
        active_category=category,
        settings=settings
    )

@employee_bp.route('/orders')
def online_orders():
    """View and process incoming customer online pickup orders."""
    user = get_current_user()
    status = request.args.get('status', 'All')
    orders = get_orders_list(status_filter=status, limit=50)
    settings = get_shop_settings()
    return render_template('employee/orders.html', user=user, orders=orders, active_status=status, settings=settings)

@employee_bp.route('/orders/<order_id>/update-status', methods=['POST'])
def process_order_status(order_id):
    """Update order pickup status."""
    user = get_current_user()
    new_status = request.form.get('status')
    success, msg = update_order_status(order_id, new_status, user_id=user['id'])
    if success:
        flash(msg, "success")
    else:
        flash(msg, "danger")
    return redirect(url_for('employee.online_orders'))

@employee_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Employee profile & password change."""
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_info':
            name = request.form.get('full_name')
            phone = request.form.get('phone')
            success, msg = update_user_profile(user['id'], name, phone)
            if success:
                flash("Profile details updated successfully.", "success")
                session['user_name'] = name
            else:
                flash(msg, "danger")
        elif action == 'change_password':
            old_p = request.form.get('old_password')
            new_p = request.form.get('new_password')
            success, msg = change_user_password(user['id'], old_p, new_p)
            if success:
                flash("Password updated successfully.", "success")
            else:
                flash(msg, "danger")
        return redirect(url_for('employee.profile'))

    settings = get_shop_settings()
    return render_template('employee/profile.html', user=user, settings=settings)

