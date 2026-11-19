from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from backend.app.services.product_service import get_all_products, get_product_by_id
from backend.app.services.order_service import place_online_order, get_orders_list, get_order_details
from backend.app.services.settings_service import get_shop_settings
from backend.app.services.auth_service import update_user_profile, change_user_password
from backend.app.utils.decorators import get_current_user, login_required, role_required

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/')
def home():
    """Customer storefront homepage with 4 categories, featured items, shop hours."""
    user = get_current_user()
    category = request.args.get('category')
    search = request.args.get('search')
    products = get_all_products(category=category, active_only=True, search=search)
    settings = get_shop_settings()
    
    # Group products by 4 strict categories
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    category_counts = {}
    for cat in categories:
        category_counts[cat] = len([p for p in products if p['category'] == cat])

    return render_template(
        'customer/home.html',
        user=user,
        products=products,
        settings=settings,
        categories=categories,
        category_counts=category_counts,
        active_category=category,
        search_query=search
    )

@customer_bp.route('/products')
def product_catalog():
    """Dedicated product browsing page."""
    user = get_current_user()
    category = request.args.get('category')
    search = request.args.get('search')
    products = get_all_products(category=category, active_only=True, search=search)
    settings = get_shop_settings()
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    return render_template(
        'customer/products.html',
        user=user,
        products=products,
        settings=settings,
        categories=categories,
        active_category=category,
        search_query=search
    )

@customer_bp.route('/cart')
def view_cart():
    """Customer shopping cart page."""
    user = get_current_user()
    settings = get_shop_settings()
    return render_template('customer/cart.html', user=user, settings=settings)

@customer_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Review items and place order for shop pickup."""
    user = get_current_user()
    settings = get_shop_settings()

    if request.method == 'POST':
        # JSON or Form submission
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        customer_id = user['id'] if user else None
        success, message, result = place_online_order(data, customer_profile_id=customer_id)
        if not success:
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 400
            flash(message, "danger")
            return redirect(url_for('customer.view_cart'))

        if request.is_json:
            return jsonify({'success': True, 'message': message, 'data': result})
        return redirect(url_for('customer.order_confirmation', order_number=result['order_number']))

    return render_template('customer/checkout.html', user=user, settings=settings)

@customer_bp.route('/order-confirmation/<order_number>')
def order_confirmation(order_number):
    """Order confirmation receipt screen with order reference number."""
    user = get_current_user()
    order = get_order_details(order_number)
    if not order:
        flash("Order not found.", "warning")
        return redirect(url_for('customer.home'))
    settings = get_shop_settings()
    return render_template('customer/order_confirmation.html', user=user, order=order, settings=settings)

@customer_bp.route('/my-orders')
@login_required
@role_required('customer')
def my_orders():
    """Customer order history."""
    user = get_current_user()
    orders = get_orders_list(customer_profile_id=user['id'])
    settings = get_shop_settings()
    return render_template('customer/order_history.html', user=user, orders=orders, settings=settings)

@customer_bp.route('/my-profile', methods=['GET', 'POST'])
@login_required
def my_profile():
    """Customer profile and password management."""
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
        return redirect(url_for('customer.my_profile'))

    settings = get_shop_settings()
    return render_template('customer/profile.html', user=user, settings=settings)
