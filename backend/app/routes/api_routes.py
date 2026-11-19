from flask import Blueprint, request, jsonify
from backend.app.services.product_service import get_all_products, get_product_by_id
from backend.app.services.order_service import place_online_order, get_orders_list, get_order_details, update_order_status
from backend.app.services.pos_service import create_sale_bill, get_sale_by_invoice, get_sales_list
from backend.app.services.inventory_service import get_inventory_status
from backend.app.services.settings_service import get_shop_settings
from backend.app.utils.decorators import get_current_user, login_required, roles_allowed

api_bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """Returns the 4 strictly supported retail categories."""
    return jsonify({
        'success': True,
        'categories': ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items'],
        'units': ['KG', 'PCS']
    })

@api_bp.route('/products', methods=['GET'])
def api_products():
    """List products with optional category and search filters."""
    category = request.args.get('category')
    search = request.args.get('search')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    products = get_all_products(category=category, active_only=active_only, search=search)
    return jsonify({'success': True, 'count': len(products), 'data': products})

@api_bp.route('/products/<product_id>', methods=['GET'])
def api_product_detail(product_id):
    """Retrieve single product detail."""
    prod = get_product_by_id(product_id)
    if not prod:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    return jsonify({'success': True, 'data': prod})

@api_bp.route('/cart/validate', methods=['POST'])
def api_validate_cart():
    """
    Validates items in shopping cart, checks live stock, and recalculates line totals and grand total.
    """
    data = request.get_json() or {}
    items = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400

    validated = []
    subtotal = 0.0
    errors = []

    for item in items:
        p_id = item.get('product_id')
        qty = float(item.get('quantity', 1.0))
        prod = get_product_by_id(p_id)
        if not prod or not prod['is_active']:
            errors.append(f"Product '{item.get('product_name', p_id)}' is unavailable.")
            continue

        avail = float(prod['available_stock'])
        if avail < qty:
            errors.append(f"Only {avail} {prod['unit']} available for '{prod['name']}'.")

        rate = float(prod['selling_price'])
        line_tot = round(qty * rate, 2)
        subtotal += line_tot

        validated.append({
            'product_id': prod['id'],
            'product_name': prod['name'],
            'category': prod['category'],
            'unit': prod['unit'],
            'quantity': qty,
            'unit_price': rate,
            'line_total': line_tot,
            'available_stock': avail
        })

    return jsonify({
        'success': len(errors) == 0,
        'errors': errors,
        'items': validated,
        'subtotal': round(subtotal, 2),
        'grand_total': round(subtotal, 2)
    })

@api_bp.route('/orders', methods=['POST'])
def api_place_order():
    """Customer storefront online ordering endpoint."""
    user = get_current_user()
    data = request.get_json() or {}
    customer_id = user['id'] if user else None
    success, msg, result = place_online_order(data, customer_profile_id=customer_id)
    if not success:
        return jsonify({'success': False, 'message': msg}), 400
    return jsonify({'success': True, 'message': msg, 'data': result}), 201

@api_bp.route('/orders', methods=['GET'])
@login_required
def api_get_orders():
    """Get customer orders or staff all orders."""
    user = get_current_user()
    if user['role'] == 'customer':
        orders = get_orders_list(customer_profile_id=user['id'])
    else:
        status = request.args.get('status')
        orders = get_orders_list(status_filter=status)
    return jsonify({'success': True, 'count': len(orders), 'data': orders})

@api_bp.route('/pos/bill', methods=['POST'])
@login_required
@roles_allowed(['admin', 'employee'])
def api_pos_bill():
    """Process POS billing sale."""
    user = get_current_user()
    data = request.get_json() or {}
    success, msg, result = create_sale_bill(data, employee_id=user['id'])
    if not success:
        return jsonify({'success': False, 'message': msg}), 400
    return jsonify({'success': True, 'message': msg, 'data': result}), 201

@api_bp.route('/inventory', methods=['GET'])
@login_required
@roles_allowed(['admin', 'employee'])
def api_inventory():
    """Returns inventory status."""
    category = request.args.get('category')
    low_stock = request.args.get('low_stock') == 'true'
    stock = get_inventory_status(category=category, low_stock_only=low_stock)
    return jsonify({'success': True, 'count': len(stock), 'data': stock})

@api_bp.route('/shop-settings', methods=['GET'])
def api_shop_settings():
    """Returns public shop info."""
    settings = get_shop_settings()
    return jsonify({'success': True, 'data': settings})

