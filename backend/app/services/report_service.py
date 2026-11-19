from decimal import Decimal
from datetime import datetime, timedelta
import pandas as pd
from backend.app.db import query_one, query_all

def get_dashboard_metrics():
    """
    Computes all 12 key retail business metrics from real database records.
    Accurately calculates Gross Profit (Revenue - COGS) and Net Operating Result (Gross Profit - Expenses).
    """
    # 1. Sales & Revenue Metrics
    sales_stats = query_one("""
        SELECT 
            COALESCE(SUM(grand_total), 0.00) as total_revenue,
            COALESCE(SUM(total_cost), 0.00) as total_cogs,
            COUNT(id) as total_bills,
            COALESCE(SUM(CASE WHEN created_at::date = CURRENT_DATE THEN grand_total ELSE 0.00 END), 0.00) as today_sales,
            COUNT(CASE WHEN created_at::date = CURRENT_DATE THEN id ELSE NULL END) as today_bills
        FROM public.sales;
    """) or {}

    total_revenue = Decimal(str(sales_stats.get('total_revenue', '0.00')))
    total_cogs = Decimal(str(sales_stats.get('total_cogs', '0.00')))
    today_sales = Decimal(str(sales_stats.get('today_sales', '0.00')))
    today_bills = int(sales_stats.get('today_bills', 0))

    # 2. Operating Expenses
    expense_stats = query_one("""
        SELECT COALESCE(SUM(amount), 0.00) as total_expenses FROM public.expenses;
    """) or {}
    total_expenses = Decimal(str(expense_stats.get('total_expenses', '0.00')))

    # 3. Profit Calculations
    gross_profit = total_revenue - total_cogs
    net_operating_result = gross_profit - total_expenses

    # 4. Inventory Metrics
    inventory_stats = query_one("""
        SELECT 
            COUNT(p.id) as total_products,
            COALESCE(SUM(COALESCE(i.current_stock, p.stock_quantity)), 0.000) as total_available_stock,
            COUNT(CASE WHEN COALESCE(i.current_stock, p.stock_quantity) <= COALESCE(i.reorder_threshold, p.min_stock_alert) THEN 1 ELSE NULL END) as low_stock_products
        FROM public.products p
        LEFT JOIN public.inventory i ON p.id = i.product_id
        WHERE p.is_active = TRUE;
    """) or {}

    total_products = int(inventory_stats.get('total_products', 0))
    total_stock = float(inventory_stats.get('total_available_stock', 0.000))
    low_stock_products = int(inventory_stats.get('low_stock_products', 0))

    # 5. Orders Metrics
    orders_stats = query_one("""
        SELECT 
            COUNT(CASE WHEN status = 'Pending' THEN 1 ELSE NULL END) as pending_orders,
            COUNT(id) as total_online_orders
        FROM public.online_orders;
    """) or {}
    pending_online_orders = int(orders_stats.get('pending_orders', 0))

    # 6. People Metrics
    people_stats = query_one("""
        SELECT 
            (SELECT COUNT(*) FROM public.customers) as total_customers,
            (SELECT COUNT(*) FROM public.profiles WHERE role = 'employee' AND is_active = TRUE) as total_employees;
    """) or {}
    total_customers = int(people_stats.get('total_customers', 0))
    total_employees = int(people_stats.get('total_employees', 0))

    return {
        'today_sales': float(today_sales),
        'today_bills': today_bills,
        'total_revenue': float(total_revenue),
        'total_expenses': float(total_expenses),
        'gross_profit': float(gross_profit),
        'net_operating_result': float(net_operating_result),
        'total_products': total_products,
        'available_stock': round(total_stock, 1),
        'low_stock_products': low_stock_products,
        'pending_online_orders': pending_online_orders,
        'total_customers': total_customers,
        'total_employees': total_employees
    }

def get_dashboard_charts():
    """
    Retrieves aggregated time-series and categorical datasets for Chart.js.
    """
    # 1. Daily sales last 7 days
    daily_sales = query_all("""
        WITH dates AS (
            SELECT generate_series(CURRENT_DATE - INTERVAL '6 days', CURRENT_DATE, '1 day'::interval)::date as d
        )
        SELECT 
            TO_CHAR(dates.d, 'Dy (DD Mon)') as date_label,
            COALESCE(SUM(s.grand_total), 0.00) as revenue,
            COALESCE(SUM(s.total_cost), 0.00) as cost,
            COALESCE(SUM(s.grand_total - s.total_cost), 0.00) as profit,
            COUNT(s.id) as bill_count
        FROM dates
        LEFT JOIN public.sales s ON dates.d = s.created_at::date
        GROUP BY dates.d
        ORDER BY dates.d ASC;
    """)

    # 2. Category-wise sales
    category_sales = query_all("""
        SELECT 
            si.category,
            COALESCE(SUM(si.line_total), 0.00) as revenue,
            COALESCE(SUM(si.quantity), 0.00) as quantity_sold
        FROM public.sale_items si
        GROUP BY si.category
        ORDER BY revenue DESC;
    """)

    # 3. Top selling products
    product_sales = query_all("""
        SELECT 
            si.product_name,
            si.category,
            si.unit,
            COALESCE(SUM(si.line_total), 0.00) as revenue,
            COALESCE(SUM(si.quantity), 0.00) as quantity_sold
        FROM public.sale_items si
        GROUP BY si.product_name, si.category, si.unit
        ORDER BY revenue DESC
        LIMIT 6;
    """)

    # 4. Expense breakdown by category
    expense_breakdown = query_all("""
        SELECT 
            category,
            COALESCE(SUM(amount), 0.00) as total_amount
        FROM public.expenses
        GROUP BY category
        ORDER BY total_amount DESC;
    """)

    # 5. Monthly sales last 6 months
    monthly_sales = query_all("""
        SELECT 
            TO_CHAR(created_at, 'Mon YYYY') as month_label,
            DATE_TRUNC('month', created_at) as month_date,
            COALESCE(SUM(grand_total), 0.00) as revenue,
            COALESCE(SUM(total_cost), 0.00) as cost,
            COALESCE(SUM(grand_total - total_cost), 0.00) as profit
        FROM public.sales
        WHERE created_at >= CURRENT_DATE - INTERVAL '6 months'
        GROUP BY month_label, month_date
        ORDER BY month_date ASC;
    """)

    return {
        'daily_sales': daily_sales,
        'category_sales': category_sales,
        'product_sales': product_sales,
        'expense_breakdown': expense_breakdown,
        'monthly_sales': monthly_sales
    }

def get_report_data(report_type: str, start_date: str = None, end_date: str = None, extra_param: str = None):
    """
    Generates structured Pandas DataFrame or list of dicts for reporting and file exports.
    Types: 'daily_sales', 'weekly_sales', 'monthly_sales', 'product_sales', 'category_sales',
           'employee_sales', 'purchase', 'inventory', 'wastage', 'expense', 'profit_loss'.
    """
    date_filter = ""
    params = []
    if start_date:
        date_filter += " AND s.created_at::date >= %s::date"
        params.append(start_date)
    if end_date:
        date_filter += " AND s.created_at::date <= %s::date"
        params.append(end_date)

    if report_type == 'daily_sales':
        sql = f"""
            SELECT 
                s.created_at::date as date,
                COUNT(s.id) as bills_count,
                SUM(s.subtotal) as subtotal,
                SUM(s.discount) as discount,
                SUM(s.grand_total) as grand_total,
                SUM(s.total_cost) as total_cogs,
                (SUM(s.grand_total) - SUM(s.total_cost)) as gross_profit
            FROM public.sales s
            WHERE 1=1 {date_filter}
            GROUP BY s.created_at::date
            ORDER BY date DESC;
        """
        return query_all(sql, params)

    elif report_type == 'product_sales':
        sql = f"""
            SELECT 
                si.product_name,
                si.category,
                si.unit,
                SUM(si.quantity) as total_quantity,
                SUM(si.line_total) as total_revenue,
                SUM(si.quantity * si.unit_cost) as total_cost,
                (SUM(si.line_total) - SUM(si.quantity * si.unit_cost)) as gross_profit,
                COUNT(DISTINCT si.sale_id) as sales_count
            FROM public.sale_items si
            JOIN public.sales s ON si.sale_id = s.id
            WHERE 1=1 {date_filter}
            GROUP BY si.product_name, si.category, si.unit
            ORDER BY total_revenue DESC;
        """
        return query_all(sql, params)

    elif report_type == 'category_sales':
        sql = f"""
            SELECT 
                si.category,
                SUM(si.quantity) as total_quantity,
                SUM(si.line_total) as total_revenue,
                SUM(si.quantity * si.unit_cost) as total_cost,
                (SUM(si.line_total) - SUM(si.quantity * si.unit_cost)) as gross_profit
            FROM public.sale_items si
            JOIN public.sales s ON si.sale_id = s.id
            WHERE 1=1 {date_filter}
            GROUP BY si.category
            ORDER BY total_revenue DESC;
        """
        return query_all(sql, params)

    elif report_type == 'employee_sales':
        sql = f"""
            SELECT 
                COALESCE(p.full_name, 'Self Service / Online') as employee_name,
                COUNT(s.id) as bills_generated,
                SUM(s.grand_total) as total_revenue,
                SUM(s.discount) as total_discounts_given
            FROM public.sales s
            LEFT JOIN public.profiles p ON s.employee_id = p.id
            WHERE 1=1 {date_filter}
            GROUP BY p.full_name
            ORDER BY total_revenue DESC;
        """
        return query_all(sql, params)

    elif report_type == 'inventory':
        sql = """
            SELECT 
                p.name as product_name,
                p.category,
                p.unit,
                COALESCE(i.current_stock, p.stock_quantity) as current_stock,
                COALESCE(i.reorder_threshold, p.min_stock_alert) as reorder_level,
                p.cost_price,
                p.selling_price,
                (COALESCE(i.current_stock, p.stock_quantity) * p.cost_price) as stock_valuation,
                CASE WHEN COALESCE(i.current_stock, p.stock_quantity) <= COALESCE(i.reorder_threshold, p.min_stock_alert) THEN 'LOW STOCK' ELSE 'ADEQUATE' END as status
            FROM public.products p
            LEFT JOIN public.inventory i ON p.id = i.product_id
            WHERE p.is_active = TRUE
            ORDER BY p.category, p.name ASC;
        """
        return query_all(sql)

    elif report_type == 'wastage':
        sql = """
            SELECT 
                sm.created_at::date as date,
                p.name as product_name,
                p.category,
                p.unit,
                ABS(sm.quantity_change) as wasted_quantity,
                p.cost_price as unit_cost,
                (ABS(sm.quantity_change) * p.cost_price) as total_loss,
                sm.movement_type,
                sm.reason,
                COALESCE(u.full_name, 'Staff') as recorded_by
            FROM public.stock_movements sm
            JOIN public.products p ON sm.product_id = p.id
            LEFT JOIN public.profiles u ON sm.performed_by = u.id
            WHERE sm.movement_type IN ('WASTAGE', 'DAMAGE')
            ORDER BY sm.created_at DESC;
        """
        return query_all(sql)

    elif report_type == 'purchase':
        sql = """
            SELECT 
                p.purchase_number,
                p.received_date,
                s.name as supplier_name,
                p.total_amount,
                p.paid_amount,
                p.balance_amount,
                p.payment_status,
                p.payment_method
            FROM public.purchases p
            JOIN public.suppliers s ON p.supplier_id = s.id
            ORDER BY p.received_date DESC;
        """
        return query_all(sql)

    elif report_type == 'expense':
        sql = """
            SELECT 
                e.expense_date,
                e.category,
                e.amount,
                e.payment_method,
                e.notes,
                COALESCE(u.full_name, 'Admin') as recorded_by
            FROM public.expenses e
            LEFT JOIN public.profiles u ON e.recorded_by = u.id
            ORDER BY e.expense_date DESC;
        """
        return query_all(sql)

    elif report_type == 'profit_loss':
        metrics = get_dashboard_metrics()
        return [
            {'metric': 'Gross Sales Revenue', 'amount': metrics['total_revenue']},
            {'metric': 'Less: Cost of Goods Sold (COGS)', 'amount': -float(Decimal(str(metrics['total_revenue'])) - Decimal(str(metrics['gross_profit'])))},
            {'metric': 'GROSS PROFIT', 'amount': metrics['gross_profit']},
            {'metric': 'Less: Operating Expenses', 'amount': -metrics['total_expenses']},
            {'metric': 'NET OPERATING RESULT (PROFIT/LOSS)', 'amount': metrics['net_operating_result']}
        ]

    return []

