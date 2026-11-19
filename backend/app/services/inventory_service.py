from decimal import Decimal
from backend.app.db import get_db_cursor, query_one, query_all

def get_inventory_status(category=None, low_stock_only=False):
    """
    Returns complete inventory view across products.
    Calculates low_stock alert when current_stock <= reorder_threshold.
    """
    conditions = []
    params = []

    if category:
        conditions.append("p.category = %s")
        params.append(category)

    if low_stock_only:
        conditions.append("COALESCE(i.current_stock, p.stock_quantity) <= COALESCE(i.reorder_threshold, p.min_stock_alert)")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            p.id as product_id,
            p.name as product_name,
            p.category,
            p.unit,
            p.selling_price,
            p.cost_price,
            COALESCE(i.current_stock, p.stock_quantity) as current_stock,
            COALESCE(i.reserved_stock, 0.000) as reserved_stock,
            (COALESCE(i.current_stock, p.stock_quantity) - COALESCE(i.reserved_stock, 0.000)) as available_stock,
            COALESCE(i.reorder_threshold, p.min_stock_alert) as min_stock_alert,
            i.last_restocked_at,
            (COALESCE(i.current_stock, p.stock_quantity) <= COALESCE(i.reorder_threshold, p.min_stock_alert)) as is_low_stock,
            p.is_active
        FROM public.products p
        LEFT JOIN public.inventory i ON p.id = i.product_id
        {where_clause}
        ORDER BY is_low_stock DESC, p.category, p.name ASC;
    """
    return query_all(sql, params)

def record_stock_adjustment(product_id: str, quantity_change, movement_type: str, reason: str, reference_id: str = None, user_id: str = None) -> tuple[bool, str, dict]:
    """
    Adjusts product inventory balance and logs audit trail in stock_movements.
    Movement types: 'PURCHASE', 'SALE', 'WASTAGE', 'DAMAGE', 'RETURN', 'ADJUSTMENT'.
    """
    try:
        qty_change = Decimal(str(quantity_change))
    except Exception:
        return False, "Invalid quantity change value.", {}

    if movement_type not in ['PURCHASE', 'SALE', 'ONLINE_ORDER', 'WASTAGE', 'DAMAGE', 'RETURN', 'ADJUSTMENT']:
        return False, f"Invalid movement type: {movement_type}", {}

    # Wastage or damage must decrease stock (so qty_change is negative)
    if movement_type in ['WASTAGE', 'DAMAGE'] and qty_change > 0:
        qty_change = -qty_change

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            SELECT p.id, p.name, p.unit, p.stock_quantity as current_stock
            FROM public.products p
            WHERE p.id = %s FOR UPDATE;
        """, (product_id,))
        prod = cur.fetchone()

        if not prod:
            return False, "Product not found.", {}

        prev_stock = Decimal(str(prod['current_stock']))
        new_stock = prev_stock + qty_change

        if new_stock < 0:
            return False, f"Operation rejected: Stock cannot become negative. (Current: {prev_stock}, Change: {qty_change})", {}

        # Update product stock
        cur.execute("UPDATE public.products SET stock_quantity = %s, updated_at = NOW() WHERE id = %s;", (new_stock, product_id))

        # Update inventory table
        cur.execute("""
            INSERT INTO public.inventory (product_id, current_stock, last_restocked_at, updated_at)
            VALUES (%s, %s, CASE WHEN %s > 0 THEN NOW() ELSE NULL END, NOW())
            ON CONFLICT (product_id) DO UPDATE SET
                current_stock = EXCLUDED.current_stock,
                last_restocked_at = CASE WHEN %s > 0 THEN NOW() ELSE inventory.last_restocked_at END,
                updated_at = NOW();
        """, (product_id, new_stock, qty_change, qty_change))

        # Record stock movement
        cur.execute("""
            INSERT INTO public.stock_movements (
                product_id, movement_type, quantity_change, previous_stock, new_stock,
                reference_id, reason, performed_by, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, created_at;
        """, (
            product_id, movement_type, qty_change, prev_stock, new_stock,
            reference_id or 'MANUAL_ADJ', reason or movement_type, user_id
        ))
        mov = cur.fetchone()

        # Audit log
        cur.execute("""
            INSERT INTO public.audit_logs (user_id, role, action, entity_type, entity_id, details)
            VALUES (%s, 'admin', 'STOCK_ADJUSTMENT', 'INVENTORY', %s, %s::jsonb);
        """, (
            user_id, product_id,
            f'{{"product_name": "{prod["name"]}", "movement_type": "{movement_type}", "prev_stock": {float(prev_stock)}, "change": {float(qty_change)}, "new_stock": {float(new_stock)}, "reason": "{reason}"}}'
        ))

        return True, "Stock adjustment recorded successfully.", {
            'product_id': product_id,
            'product_name': prod['name'],
            'previous_stock': float(prev_stock),
            'quantity_change': float(qty_change),
            'new_stock': float(new_stock),
            'movement_type': movement_type
        }

def get_stock_movements(product_id: str = None, movement_type: str = None, limit: int = 100):
    """Retrieves chronological stock movement history with product and user details."""
    conditions = []
    params = []

    if product_id:
        conditions.append("sm.product_id = %s")
        params.append(product_id)

    if movement_type:
        conditions.append("sm.movement_type = %s")
        params.append(movement_type)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            sm.id, sm.product_id, p.name as product_name, p.category, p.unit,
            sm.movement_type, sm.quantity_change, sm.previous_stock, sm.new_stock,
            sm.reference_id, sm.reason, sm.created_at,
            COALESCE(u.full_name, 'System') as performed_by_name
        FROM public.stock_movements sm
        JOIN public.products p ON sm.product_id = p.id
        LEFT JOIN public.profiles u ON sm.performed_by = u.id
        {where_clause}
        ORDER BY sm.created_at DESC
        LIMIT {limit};
    """
    return query_all(sql, params)
