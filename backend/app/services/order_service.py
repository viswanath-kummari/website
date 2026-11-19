from decimal import Decimal
from datetime import datetime
from backend.app.config import Config
from backend.app.db import get_db_cursor, query_one, query_all

def generate_order_number() -> str:
    """Generates unique order reference number e.g. ORD-2026-0002."""
    current_year = datetime.now().year
    prefix = f"ORD-{current_year}-"
    
    row = query_one(
        "SELECT order_number FROM public.online_orders WHERE order_number LIKE %s ORDER BY created_at DESC LIMIT 1;",
        (f"{prefix}%",)
    )
    if not row:
        return f"{prefix}0001"
    
    last_ord = row['order_number']
    try:
        last_num = int(last_ord.split('-')[-1])
        next_num = last_num + 1
    except Exception:
        next_num = 1
        
    return f"{prefix}{next_num:04d}"

def place_online_order(order_data: dict, customer_profile_id: str = None) -> tuple[bool, str, dict]:
    """
    Places an online order for shop pickup.
    Validates products, recalculates prices against database, and saves order items.
    """
    items = order_data.get('items', [])
    if not items:
        return False, "Your shopping cart is empty.", {}

    customer_name = (order_data.get('customer_name') or '').strip()
    customer_phone = (order_data.get('customer_phone') or '').strip()
    customer_email = (order_data.get('customer_email') or '').strip()
    pickup_time = (order_data.get('pickup_time') or 'Within 2 hours').strip()
    notes = (order_data.get('notes') or '').strip()
    payment_method = order_data.get('payment_method', 'Cash on Collection')

    if not customer_name or not customer_phone:
        return False, "Customer name and phone number are required.", {}

    with get_db_cursor(commit=True) as cur:
        subtotal = Decimal('0.00')
        validated_items = []

        for idx, item in enumerate(items):
            product_id = item.get('product_id')
            cur.execute("""
                SELECT p.id, p.name, p.category, p.unit, p.selling_price, p.cost_price, p.is_active,
                       p.stock_quantity as current_stock,
                       COALESCE((SELECT reserved_stock FROM public.inventory WHERE product_id = p.id), 0.000) as reserved_stock
                FROM public.products p
                WHERE p.id = %s FOR UPDATE;
            """, (product_id,))
            prod = cur.fetchone()

            if not prod or not prod['is_active']:
                return False, f"Product '{item.get('product_name', 'Item')}' is no longer available.", {}

            try:
                qty = Decimal(str(item.get('quantity', '1.000')))
            except Exception:
                return False, f"Invalid quantity for '{prod['name']}'.", {}

            if qty <= 0:
                return False, f"Quantity must be greater than zero for '{prod['name']}'.", {}

            if prod['unit'] == 'PCS' and qty % 1 != 0:
                return False, f"'{prod['name']}' is sold in whole pieces (PCS).", {}

            avail_stock = Decimal(str(prod['current_stock'])) - Decimal(str(prod['reserved_stock']))
            if avail_stock < qty:
                return False, f"Only {avail_stock} {prod['unit']} available for '{prod['name']}'. Please adjust your quantity.", {}

            unit_price = Decimal(str(prod['selling_price']))
            line_total = (qty * unit_price).quantize(Decimal('0.01'))
            subtotal += line_total

            validated_items.append({
                'product_id': prod['id'],
                'product_name': prod['name'],
                'category': prod['category'],
                'unit': prod['unit'],
                'quantity': qty,
                'unit_price': unit_price,
                'line_total': line_total
            })

        order_number = generate_order_number()
        grand_total = subtotal  # no discounts on online orders unless promotional

        # Insert Order Header
        cur.execute("""
            INSERT INTO public.online_orders (
                order_number, customer_profile_id, customer_name, customer_phone, customer_email,
                subtotal, discount, grand_total, status, payment_method, pickup_time, notes, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, 0.00, %s, 'Pending', %s, %s, %s, NOW(), NOW()
            ) RETURNING id, order_number, created_at;
        """, (
            order_number, customer_profile_id, customer_name, customer_phone, customer_email,
            subtotal, grand_total, payment_method, pickup_time, notes
        ))
        order_record = cur.fetchone()
        order_id = order_record['id']

        # Insert Order Items
        for it in validated_items:
            cur.execute("""
                INSERT INTO public.online_order_items (
                    order_id, product_id, product_name, category, unit, quantity, unit_price, line_total, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """, (
                order_id, it['product_id'], it['product_name'], it['category'], it['unit'],
                it['quantity'], it['unit_price'], it['line_total']
            ))

        # Log action
        cur.execute("""
            INSERT INTO public.audit_logs (user_id, role, action, entity_type, entity_id, details)
            VALUES (%s, 'customer', 'ONLINE_ORDER_PLACED', 'ORDER', %s, %s::jsonb);
        """, (
            customer_profile_id, order_number,
            f'{{"order_number": "{order_number}", "grand_total": {float(grand_total)}, "pickup_time": "{pickup_time}"}}'
        ))

        return True, "Order confirmed successfully! You can pick it up at the shop.", {
            'order_id': str(order_id),
            'order_number': order_number,
            'customer_name': customer_name,
            'grand_total': float(grand_total),
            'status': 'Pending',
            'pickup_time': pickup_time
        }

def update_order_status(order_id: str, new_status: str, user_id: str = None) -> tuple[bool, str]:
    """
    Transitions order status and handles stock reservations or deductions.
    Allowed statuses: 'Pending', 'Accepted', 'Ready for Collection', 'Completed', 'Cancelled'.
    """
    if new_status not in Config.ALLOWED_ORDER_STATUSES:
        return False, f"Invalid order status. Allowed: {', '.join(Config.ALLOWED_ORDER_STATUSES)}"

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM public.online_orders WHERE id = %s FOR UPDATE;", (order_id,))
        order = cur.fetchone()
        if not order:
            return False, "Order not found."

        old_status = order['status']
        if old_status == new_status:
            return True, f"Order is already marked as {new_status}."

        cur.execute("SELECT * FROM public.online_order_items WHERE order_id = %s;", (order_id,))
        items = cur.fetchall()

        # Handle Stock logic depending on status transitions
        # 1. Transitioning to 'Accepted' from 'Pending': Reserve stock
        if new_status == 'Accepted' and old_status == 'Pending':
            for it in items:
                cur.execute("""
                    UPDATE public.inventory
                    SET reserved_stock = reserved_stock + %s, updated_at = NOW()
                    WHERE product_id = %s;
                """, (it['quantity'], it['product_id']))

        # 2. Transitioning to 'Completed': Deduct stock and release reservation
        elif new_status == 'Completed':
            for it in items:
                # Deduct from actual current stock
                cur.execute("""
                    UPDATE public.products
                    SET stock_quantity = GREATEST(0.000, stock_quantity - %s), updated_at = NOW()
                    WHERE id = %s;
                """, (it['quantity'], it['product_id']))

                # Update inventory: reduce stock and reduce reserved if previously accepted
                if old_status in ['Accepted', 'Ready for Collection']:
                    cur.execute("""
                        UPDATE public.inventory
                        SET current_stock = GREATEST(0.000, current_stock - %s),
                            reserved_stock = GREATEST(0.000, reserved_stock - %s),
                            updated_at = NOW()
                        WHERE product_id = %s;
                    """, (it['quantity'], it['quantity'], it['product_id']))
                else:
                    cur.execute("""
                        UPDATE public.inventory
                        SET current_stock = GREATEST(0.000, current_stock - %s),
                            updated_at = NOW()
                        WHERE product_id = %s;
                    """, (it['quantity'], it['product_id']))

                # Record stock movement
                cur.execute("""
                    INSERT INTO public.stock_movements (
                        product_id, movement_type, quantity_change, previous_stock, new_stock,
                        reference_id, reason, performed_by, created_at
                    ) VALUES (%s, 'ONLINE_ORDER', %s, 0.000, 0.000, %s, 'Online order completed and collected', %s, NOW());
                """, (it['product_id'], -it['quantity'], order['order_number'], user_id))

        # 3. Transitioning to 'Cancelled': Release reservation if it was reserved
        elif new_status == 'Cancelled' and old_status in ['Accepted', 'Ready for Collection']:
            for it in items:
                cur.execute("""
                    UPDATE public.inventory
                    SET reserved_stock = GREATEST(0.000, reserved_stock - %s), updated_at = NOW()
                    WHERE product_id = %s;
                """, (it['quantity'], it['product_id']))

        # Update order status
        cur.execute("""
            UPDATE public.online_orders
            SET status = %s, processed_by = %s, updated_at = NOW()
            WHERE id = %s;
        """, (new_status, user_id, order_id))

        # Audit log
        cur.execute("""
            INSERT INTO public.audit_logs (user_id, role, action, entity_type, entity_id, details)
            VALUES (%s, 'staff', 'ORDER_STATUS_CHANGED', 'ORDER', %s, %s::jsonb);
        """, (
            user_id, order['order_number'],
            f'{{"order_number": "{order["order_number"]}", "from": "{old_status}", "to": "{new_status}"}}'
        ))

        return True, f"Order {order['order_number']} status updated to '{new_status}'."

def get_orders_list(customer_profile_id: str = None, status_filter: str = None, limit: int = 50):
    """Retrieves orders with item summaries."""
    conditions = []
    params = []

    if customer_profile_id:
        conditions.append("o.customer_profile_id = %s")
        params.append(customer_profile_id)

    if status_filter and status_filter != 'All':
        conditions.append("o.status = %s")
        params.append(status_filter)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            o.id, o.order_number, o.customer_name, o.customer_phone, o.customer_email,
            o.subtotal, o.discount, o.grand_total, o.status, o.payment_method,
            o.pickup_time, o.notes, o.created_at, o.updated_at,
            COUNT(oi.id) as total_items,
            COALESCE(p.full_name, 'Unassigned') as processed_by_name
        FROM public.online_orders o
        LEFT JOIN public.online_order_items oi ON o.id = oi.order_id
        LEFT JOIN public.profiles p ON o.processed_by = p.id
        {where_clause}
        GROUP BY o.id, p.full_name
        ORDER BY o.created_at DESC
        LIMIT {limit};
    """
    return query_all(sql, params)

def get_order_details(order_id: str) -> dict:
    """Fetches full order details including line items."""
    order = query_one("""
        SELECT o.*, p.full_name as processed_by_name
        FROM public.online_orders o
        LEFT JOIN public.profiles p ON o.processed_by = p.id
        WHERE o.id = %s OR o.order_number = %s;
    """, (order_id, order_id))

    if not order:
        return None

    items = query_all("""
        SELECT * FROM public.online_order_items WHERE order_id = %s ORDER BY created_at ASC;
    """, (order['id'],))

    order['items'] = items
    return order
