from decimal import Decimal
from datetime import datetime
from backend.app.db import get_db_cursor, query_one, query_all

def generate_purchase_number() -> str:
    """Generates unique purchase invoice number e.g. PUR-2026-0001."""
    current_year = datetime.now().year
    prefix = f"PUR-{current_year}-"
    row = query_one(
        "SELECT purchase_number FROM public.purchases WHERE purchase_number LIKE %s ORDER BY created_at DESC LIMIT 1;",
        (f"{prefix}%",)
    )
    if not row:
        return f"{prefix}0001"
    try:
        last_num = int(row['purchase_number'].split('-')[-1])
        next_num = last_num + 1
    except Exception:
        next_num = 1
    return f"{prefix}{next_num:04d}"

def get_suppliers_list():
    """Retrieves all suppliers with outstanding balance and purchase totals."""
    sql = """
        SELECT 
            s.*,
            COUNT(p.id) as total_purchases_count,
            COALESCE(SUM(p.total_amount), 0.00) as total_purchased_value
        FROM public.suppliers s
        LEFT JOIN public.purchases p ON s.id = p.supplier_id
        GROUP BY s.id
        ORDER BY s.is_active DESC, s.name ASC;
    """
    return query_all(sql)

def create_supplier(data: dict) -> tuple[bool, str, dict]:
    """Adds a new supplier."""
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    contact_person = (data.get('contact_person') or '').strip()
    email = (data.get('email') or '').strip()
    address = (data.get('address') or '').strip()
    notes = (data.get('notes') or '').strip()

    if not name or not phone:
        return False, "Supplier name and phone are required.", {}

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO public.suppliers (name, contact_person, phone, email, address, notes, outstanding_balance, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, 0.00, TRUE)
            RETURNING *;
        """, (name, contact_person, phone, email, address, notes))
        sup = cur.fetchone()
        return True, "Supplier created successfully.", sup

def update_supplier(supplier_id: str, data: dict) -> tuple[bool, str, dict]:
    """Updates supplier information."""
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    contact_person = (data.get('contact_person') or '').strip()
    email = (data.get('email') or '').strip()
    address = (data.get('address') or '').strip()
    notes = (data.get('notes') or '').strip()

    if not name or not phone:
        return False, "Supplier name and phone are required.", {}

    with get_db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE public.suppliers
            SET name = %s, contact_person = %s, phone = %s, email = %s, address = %s, notes = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *;
        """, (name, contact_person, phone, email, address, notes, supplier_id))
        sup = cur.fetchone()
        return True, "Supplier updated successfully.", sup

def record_incoming_purchase(data: dict, admin_id: str = None) -> tuple[bool, str, dict]:
    """
    Records an incoming product purchase from a supplier.
    Atomically updates inventory, product cost prices, stock movements, and supplier balance.
    """
    supplier_id = data.get('supplier_id')
    items = data.get('items', [])
    invoice_ref = (data.get('invoice_reference') or '').strip()
    payment_method = data.get('payment_method', 'Cash')
    notes = (data.get('notes') or '').strip()

    if not supplier_id:
        return False, "Supplier is required.", {}

    if not items:
        return False, "Purchase must include at least one product.", {}

    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM public.suppliers WHERE id = %s FOR UPDATE;", (supplier_id,))
        supplier = cur.fetchone()
        if not supplier:
            return False, "Supplier not found.", {}

        total_amount = Decimal('0.00')
        validated_items = []

        for idx, item in enumerate(items):
            product_id = item.get('product_id')
            cur.execute("""
                SELECT p.id, p.name, p.unit, p.cost_price,
                       p.stock_quantity as current_stock
                FROM public.products p
                WHERE p.id = %s FOR UPDATE;
            """, (product_id,))
            prod = cur.fetchone()

            if not prod:
                return False, f"Product {product_id} not found.", {}

            try:
                qty = Decimal(str(item.get('quantity', '1.000')))
                unit_cost = Decimal(str(item.get('unit_cost', prod['cost_price'])))
            except Exception:
                return False, f"Invalid quantity or unit cost for '{prod['name']}'.", {}

            if qty <= 0 or unit_cost < 0:
                return False, f"Quantity must be positive and cost non-negative for '{prod['name']}'.", {}

            line_total = (qty * unit_cost).quantize(Decimal('0.01'))
            total_amount += line_total

            validated_items.append({
                'product_id': prod['id'],
                'product_name': prod['name'],
                'unit': prod['unit'],
                'quantity': qty,
                'unit_cost': unit_cost,
                'line_total': line_total,
                'current_stock': Decimal(str(prod['current_stock']))
            })

        try:
            paid_amount = Decimal(str(data.get('paid_amount', total_amount)))
        except Exception:
            paid_amount = total_amount

        if paid_amount > total_amount:
            paid_amount = total_amount

        balance_amount = total_amount - paid_amount
        payment_status = 'Paid' if balance_amount == 0 else ('Partial' if paid_amount > 0 else 'Pending')
        purchase_num = generate_purchase_number()

        # 1. Insert Purchase Header
        cur.execute("""
            INSERT INTO public.purchases (
                purchase_number, supplier_id, total_amount, paid_amount, balance_amount,
                payment_status, payment_method, invoice_reference, notes, recorded_by, created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, NOW()
            ) RETURNING id, purchase_number, created_at;
        """, (
            purchase_num, supplier_id, total_amount, paid_amount, balance_amount,
            payment_status, payment_method, invoice_ref, notes, admin_id
        ))
        purch_record = cur.fetchone()
        purchase_id = purch_record['id']

        # 2. Insert Items, Update Stock & Inventory, Log Movement
        for it in validated_items:
            cur.execute("""
                INSERT INTO public.purchase_items (
                    purchase_id, product_id, product_name, unit, quantity, unit_cost, line_total, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
            """, (
                purchase_id, it['product_id'], it['product_name'], it['unit'],
                it['quantity'], it['unit_cost'], it['line_total']
            ))

            new_stock = it['current_stock'] + it['quantity']

            # Update products table (stock & latest cost price)
            cur.execute("""
                UPDATE public.products
                SET stock_quantity = %s, cost_price = %s, updated_at = NOW()
                WHERE id = %s;
            """, (new_stock, it['unit_cost'], it['product_id']))

            # Update inventory table
            cur.execute("""
                INSERT INTO public.inventory (product_id, current_stock, last_restocked_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (product_id) DO UPDATE SET
                    current_stock = EXCLUDED.current_stock,
                    last_restocked_at = NOW(),
                    updated_at = NOW();
            """, (it['product_id'], new_stock))

            # Record stock movement
            cur.execute("""
                INSERT INTO public.stock_movements (
                    product_id, movement_type, quantity_change, previous_stock, new_stock,
                    reference_id, reason, performed_by, created_at
                ) VALUES (%s, 'PURCHASE', %s, %s, %s, %s, %s, %s, NOW());
            """, (
                it['product_id'], it['quantity'], it['current_stock'], new_stock,
                purchase_num, f"Purchase from {supplier['name']}", admin_id
            ))

        # 3. If paid_amount > 0, record supplier payment
        if paid_amount > 0:
            cur.execute("""
                INSERT INTO public.payments (
                    payment_type, reference_type, reference_id, supplier_id, amount,
                    payment_method, transaction_reference, notes, recorded_by, created_at
                ) VALUES (
                    'SUPPLIER_PAYMENT', 'PURCHASE', %s, %s, %s,
                    %s, %s, %s, %s, NOW()
                );
            """, (
                purchase_num, supplier_id, paid_amount, payment_method, f"PUR-{purchase_num}", f"Payment for purchase {purchase_num}", admin_id
            ))

        # 4. Update supplier outstanding balance
        if balance_amount > 0:
            cur.execute("""
                UPDATE public.suppliers
                SET outstanding_balance = outstanding_balance + %s, updated_at = NOW()
                WHERE id = %s;
            """, (balance_amount, supplier_id))

        # 5. Audit Log
        cur.execute("""
            INSERT INTO public.audit_logs (user_id, role, action, entity_type, entity_id, details)
            VALUES (%s, 'admin', 'PURCHASE_RECORDED', 'PURCHASE', %s, %s::jsonb);
        """, (
            admin_id, purchase_num,
            f'{{"purchase_number": "{purchase_num}", "supplier": "{supplier["name"]}", "total_amount": {float(total_amount)}, "paid": {float(paid_amount)}}}'
        ))

        return True, "Purchase order and stock addition completed successfully.", {
            'purchase_id': str(purchase_id),
            'purchase_number': purchase_num,
            'supplier_name': supplier['name'],
            'total_amount': float(total_amount),
            'paid_amount': float(paid_amount),
            'balance_amount': float(balance_amount)
        }

def get_purchases_list(supplier_id: str = None, limit: int = 100):
    """Retrieves purchase history with supplier details and item counts."""
    conditions = []
    params = []

    if supplier_id:
        conditions.append("p.supplier_id = %s")
        params.append(supplier_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            p.*,
            s.name as supplier_name,
            COUNT(pi.id) as items_count
        FROM public.purchases p
        JOIN public.suppliers s ON p.supplier_id = s.id
        LEFT JOIN public.purchase_items pi ON p.id = pi.purchase_id
        {where_clause}
        GROUP BY p.id, s.name
        ORDER BY p.created_at DESC
        LIMIT {limit};
    """
    return query_all(sql, params)
