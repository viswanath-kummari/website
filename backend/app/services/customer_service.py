from decimal import Decimal
from backend.app.db import query_one, query_all, execute

def get_customers_list(search: str = None, limit: int = 100):
    """Retrieves all customers with spending summary and order counts."""
    conditions = []
    params = []

    if search:
        conditions.append("(c.name ILIKE %s OR c.phone ILIKE %s OR c.email ILIKE %s)")
        pat = f"%{search.strip()}%"
        params.extend([pat, pat, pat])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            c.id, c.name, c.phone, c.email, c.address, c.outstanding_balance, c.created_at,
            COUNT(DISTINCT s.id) as pos_bills_count,
            COALESCE(SUM(s.grand_total), 0.00) as total_pos_spend,
            COUNT(DISTINCT o.id) as online_orders_count
        FROM public.customers c
        LEFT JOIN public.sales s ON c.id = s.customer_id
        LEFT JOIN public.online_orders o ON c.profile_id = o.customer_profile_id
        {where_clause}
        GROUP BY c.id
        ORDER BY total_pos_spend DESC, c.name ASC
        LIMIT {limit};
    """
    return query_all(sql, params)

def get_customer_details(customer_id: str):
    """Retrieves single customer profile, POS purchase history, and online orders."""
    customer = query_one("SELECT * FROM public.customers WHERE id = %s;", (customer_id,))
    if not customer:
        return None

    # Get recent sales
    sales = query_all("""
        SELECT id, invoice_number, grand_total, payment_method, created_at
        FROM public.sales
        WHERE customer_id = %s
        ORDER BY created_at DESC
        LIMIT 20;
    """, (customer_id,))

    # Get online orders
    orders = []
    if customer.get('profile_id'):
        orders = query_all("""
            SELECT id, order_number, grand_total, status, created_at
            FROM public.online_orders
            WHERE customer_profile_id = %s
            ORDER BY created_at DESC
            LIMIT 20;
        """, (customer['profile_id'],))

    customer['sales'] = sales
    customer['orders'] = orders
    return customer

