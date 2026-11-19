from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_file
import io
from backend.app.services.product_service import (
    get_all_products, get_product_by_id, create_product, update_product, update_product_price, toggle_product_status
)
from backend.app.services.pos_service import create_sale_bill, get_sales_list, get_sale_by_invoice
from backend.app.services.inventory_service import get_inventory_status, record_stock_adjustment, get_stock_movements
from backend.app.services.order_service import get_orders_list, update_order_status, get_order_details
from backend.app.services.customer_service import get_customers_list, get_customer_details
from backend.app.services.employee_service import get_employees_list, create_employee, toggle_employee_status, get_employee_sales_summary
from backend.app.services.supplier_service import get_suppliers_list, create_supplier, update_supplier, record_incoming_purchase, get_purchases_list
from backend.app.services.expense_service import get_expenses_list, record_expense, get_payments_list
from backend.app.services.report_service import get_dashboard_metrics, get_dashboard_charts, get_report_data
from backend.app.services.settings_service import get_shop_settings, update_shop_settings, get_audit_logs
from backend.app.services.auth_service import update_user_profile, change_user_password
from backend.app.utils.export_helpers import export_to_csv, export_to_excel, generate_invoice_pdf
from backend.app.utils.decorators import get_current_user, role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@role_required('admin')
def check_admin_access():
    """Restricts all admin endpoints to verified Administrator accounts."""
    pass

# 1. DASHBOARD
@admin_bp.route('/dashboard')
def dashboard():
    user = get_current_user()
    metrics = get_dashboard_metrics()
    charts = get_dashboard_charts()
    settings = get_shop_settings()
    recent_sales = get_sales_list(limit=5)
    pending_orders = get_orders_list(status_filter='Pending', limit=5)

    return render_template(
        'admin/dashboard.html',
        user=user,
        metrics=metrics,
        charts=charts,
        recent_sales=recent_sales,
        pending_orders=pending_orders,
        settings=settings
    )

# 2. PRODUCTS MANAGEMENT
@admin_bp.route('/products', methods=['GET', 'POST'])
def products():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            success, msg, prod = create_product(request.form.to_dict(), user_id=user['id'])
            flash(msg, "success" if success else "danger")
        elif action == 'edit':
            p_id = request.form.get('product_id')
            success, msg, prod = update_product(p_id, request.form.to_dict(), user_id=user['id'])
            flash(msg, "success" if success else "danger")
        elif action == 'toggle_status':
            p_id = request.form.get('product_id')
            new_status = request.form.get('is_active') == 'true'
            success, msg = toggle_product_status(p_id, new_status)
            flash(msg, "info" if success else "danger")
        return redirect(url_for('admin.products'))

    category = request.args.get('category')
    search = request.args.get('search')
    products_list = get_all_products(category=category, active_only=False, search=search)
    settings = get_shop_settings()
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    return render_template(
        'admin/products.html',
        user=user,
        products=products_list,
        categories=categories,
        active_category=category,
        search_query=search,
        settings=settings
    )

# 3. PRICE MANAGEMENT
@admin_bp.route('/prices', methods=['GET', 'POST'])
def prices():
    user = get_current_user()
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        selling_price = request.form.get('selling_price')
        cost_price = request.form.get('cost_price')
        success, msg = update_product_price(product_id, selling_price, cost_price, user_id=user['id'])
        flash(msg, "success" if success else "danger")
        return redirect(url_for('admin.prices'))

    category = request.args.get('category')
    search = request.args.get('search')
    products_list = get_all_products(category=category, active_only=False, search=search)
    settings = get_shop_settings()
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    return render_template(
        'admin/prices.html',
        user=user,
        products=products_list,
        categories=categories,
        active_category=category,
        settings=settings
    )

# 4. POS / BILLING
@admin_bp.route('/pos')
def pos():
    user = get_current_user()
    products_list = get_all_products(active_only=True)
    customers = get_customers_list()
    settings = get_shop_settings()
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    return render_template(
        'admin/pos.html',
        user=user,
        products=products_list,
        customers=customers,
        categories=categories,
        settings=settings
    )

# 5. INVENTORY MANAGEMENT
@admin_bp.route('/inventory', methods=['GET', 'POST'])
def inventory():
    user = get_current_user()
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        qty = request.form.get('quantity_change')
        mov_type = request.form.get('movement_type')
        reason = request.form.get('reason')
        success, msg, res = record_stock_adjustment(product_id, qty, mov_type, reason, user_id=user['id'])
        flash(msg, "success" if success else "danger")
        return redirect(url_for('admin.inventory'))

    category = request.args.get('category')
    low_stock = request.args.get('low_stock') == '1'
    stock_items = get_inventory_status(category=category, low_stock_only=low_stock)
    movements = get_stock_movements(limit=30)
    settings = get_shop_settings()
    categories = ['Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items']
    return render_template(
        'admin/inventory.html',
        user=user,
        stock_items=stock_items,
        movements=movements,
        categories=categories,
        active_category=category,
        low_stock_filter=low_stock,
        settings=settings
    )

# 6. ONLINE ORDERS
@admin_bp.route('/orders')
def online_orders():
    user = get_current_user()
    status = request.args.get('status', 'All')
    orders = get_orders_list(status_filter=status, limit=50)
    settings = get_shop_settings()
    return render_template('admin/orders.html', user=user, orders=orders, active_status=status, settings=settings)

@admin_bp.route('/orders/<order_id>/update-status', methods=['POST'])
def update_order(order_id):
    user = get_current_user()
    new_status = request.form.get('status')
    success, msg = update_order_status(order_id, new_status, user_id=user['id'])
    flash(msg, "success" if success else "danger")
    return redirect(url_for('admin.online_orders'))

# 7. CUSTOMER MANAGEMENT
@admin_bp.route('/customers')
def customers():
    user = get_current_user()
    search = request.args.get('search')
    customers_list = get_customers_list(search=search)
    settings = get_shop_settings()
    return render_template('admin/customers.html', user=user, customers=customers_list, settings=settings)

@admin_bp.route('/customers/<customer_id>')
def customer_detail(customer_id):
    user = get_current_user()
    cust = get_customer_details(customer_id)
    if not cust:
        flash("Customer not found.", "warning")
        return redirect(url_for('admin.customers'))
    settings = get_shop_settings()
    return render_template('admin/customer_details.html', user=user, customer=cust, settings=settings)

# 8. EMPLOYEE MANAGEMENT
@admin_bp.route('/employees', methods=['GET', 'POST'])
def employees():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            success, msg, emp = create_employee(request.form.to_dict(), admin_id=user['id'])
            flash(msg, "success" if success else "danger")
        elif action == 'toggle_status':
            p_id = request.form.get('profile_id')
            new_status = request.form.get('is_active') == 'true'
            success, msg = toggle_employee_status(p_id, new_status, admin_id=user['id'])
            flash(msg, "info" if success else "danger")
        return redirect(url_for('admin.employees'))

    employees_list = get_employees_list()
    settings = get_shop_settings()
    return render_template('admin/employees.html', user=user, employees=employees_list, settings=settings)

# 9. SUPPLIER MANAGEMENT
@admin_bp.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    user = get_current_user()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            success, msg, sup = create_supplier(request.form.to_dict())
            flash(msg, "success" if success else "danger")
        elif action == 'edit':
            s_id = request.form.get('supplier_id')
            success, msg, sup = update_supplier(s_id, request.form.to_dict())
            flash(msg, "success" if success else "danger")
        return redirect(url_for('admin.suppliers'))

    suppliers_list = get_suppliers_list()
    settings = get_shop_settings()
    return render_template('admin/suppliers.html', user=user, suppliers=suppliers_list, settings=settings)

# 10. PURCHASE MANAGEMENT
@admin_bp.route('/purchases', methods=['GET', 'POST'])
def purchases():
    user = get_current_user()
    if request.method == 'POST':
        # Parse JSON or form data
        if request.is_json:
            data = request.get_json()
        else:
            # Multi-item purchase form parsing
            data = request.form.to_dict()
            product_id = request.form.get('product_id')
            qty = request.form.get('quantity')
            unit_cost = request.form.get('unit_cost')
            data['items'] = [{'product_id': product_id, 'quantity': qty, 'unit_cost': unit_cost}]

        success, msg, res = record_incoming_purchase(data, admin_id=user['id'])
        if request.is_json:
            return jsonify({'success': success, 'message': msg, 'data': res})
        flash(msg, "success" if success else "danger")
        return redirect(url_for('admin.purchases'))

    purchases_list = get_purchases_list()
    suppliers_list = get_suppliers_list()
    products_list = get_all_products(active_only=True)
    settings = get_shop_settings()
    return render_template(
        'admin/purchases.html',
        user=user,
        purchases=purchases_list,
        suppliers=suppliers_list,
        products=products_list,
        settings=settings
    )

# 11. EXPENSES MANAGEMENT
@admin_bp.route('/expenses', methods=['GET', 'POST'])
def expenses():
    user = get_current_user()
    if request.method == 'POST':
        success, msg, exp = record_expense(request.form.to_dict(), admin_id=user['id'])
        flash(msg, "success" if success else "danger")
        return redirect(url_for('admin.expenses'))

    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    expenses_list = get_expenses_list(category=category, start_date=start_date, end_date=end_date)
    settings = get_shop_settings()
    allowed_categories = [
        'Shop rent', 'Electricity', 'Employee salaries',
        'Transportation', 'Packaging', 'Maintenance', 'Other business expenses'
    ]
    return render_template(
        'admin/expenses.html',
        user=user,
        expenses=expenses_list,
        categories=allowed_categories,
        active_category=category,
        settings=settings
    )

# 12. PAYMENTS
@admin_bp.route('/payments')
def payments():
    user = get_current_user()
    pay_type = request.args.get('type')
    payments_list = get_payments_list(payment_type=pay_type)
    settings = get_shop_settings()
    return render_template('admin/payments.html', user=user, payments=payments_list, active_type=pay_type, settings=settings)

# 13. SALES HISTORY
@admin_bp.route('/sales')
def sales_history():
    user = get_current_user()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    sales = get_sales_list(start_date=start_date, end_date=end_date, search=search, limit=100)
    settings = get_shop_settings()
    return render_template('admin/sales_history.html', user=user, sales=sales, settings=settings)

# 14. REPORTS & ANALYTICS
@admin_bp.route('/reports')
def reports():
    user = get_current_user()
    report_type = request.args.get('type', 'daily_sales')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = get_report_data(report_type, start_date=start_date, end_date=end_date)
    metrics = get_dashboard_metrics()
    settings = get_shop_settings()
    return render_template(
        'admin/reports.html',
        user=user,
        report_type=report_type,
        data=data,
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
        settings=settings
    )

@admin_bp.route('/reports/export')
def export_report():
    report_type = request.args.get('type', 'daily_sales')
    export_format = request.args.get('format', 'csv')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data = get_report_data(report_type, start_date=start_date, end_date=end_date)

    if export_format == 'csv':
        csv_bytes = export_to_csv(data)
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={report_type}_report.csv"}
        )
    elif export_format == 'excel':
        excel_bytes = export_to_excel(data)
        return Response(
            excel_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-disposition": f"attachment; filename={report_type}_report.xlsx"}
        )
    else:
        # Fallback to CSV
        csv_bytes = export_to_csv(data)
        return Response(
            csv_bytes,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={report_type}_report.csv"}
        )

# 15. SHOP SETTINGS
@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings_page():
    user = get_current_user()
    if request.method == 'POST':
        success, msg = update_shop_settings(request.form.to_dict())
        flash(msg, "success" if success else "danger")
        return redirect(url_for('admin.settings_page'))

    settings = get_shop_settings()
    return render_template('admin/settings.html', user=user, settings=settings)

# 16. AUDIT LOGS
@admin_bp.route('/audit-logs')
def audit_logs():
    user = get_current_user()
    logs = get_audit_logs(limit=100)
    settings = get_shop_settings()
    return render_template('admin/audit_logs.html', user=user, logs=logs, settings=settings)

# 17. PROFILE
@admin_bp.route('/profile', methods=['GET', 'POST'])
def profile():
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
        return redirect(url_for('admin.profile'))

    settings = get_shop_settings()
    return render_template('admin/profile.html', user=user, settings=settings)

# INVOICE PRINT & PDF VIEWS
@admin_bp.route('/invoice/<invoice_number>/print')
def print_invoice(invoice_number):
    sale = get_sale_by_invoice(invoice_number)
    if not sale:
        flash("Invoice not found.", "warning")
        return redirect(url_for('admin.sales_history'))
    return render_template('admin/print_invoice.html', sale=sale)

@admin_bp.route('/invoice/<invoice_number>/pdf')
def download_invoice_pdf(invoice_number):
    sale = get_sale_by_invoice(invoice_number)
    if not sale:
        flash("Invoice not found.", "warning")
        return redirect(url_for('admin.sales_history'))
    pdf_bytes = generate_invoice_pdf(sale)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{invoice_number}.pdf"
    )
