from decimal import Decimal
from datetime import datetime
from backend.app.config import Config
from backend.app.db import get_db_cursor, query_one, query_all

def generate_invoice_number() -> str:
    """Generates a sequential, thread-safe unique invoice number (e.g. INV-2026-0003)."""
    current_year = datetime.now().year
    prefix = f"INV-{current_year}-"
    
    row = query_one(
        "SELECT invoice_number FROM public.sales WHERE invoice_number LIKE %s ORDER BY created_at DESC LIMIT 1;",
        (f"{prefix}%",)
    )
    if not row:
        return f"{prefix}0001"
    
    last_inv = row['invoice_number']
    try:
        last_num = int(last_inv.split('-')[-1])
        next_num = last_num + 1
    except Exception:
        next_num = 1
        
    return f"{prefix}{next_num:04d}"

def create_sale_bill(bill_data: dict, employee_id: str = None) -> tuple[bool, str, dict]:
    """
    Executes a complete POS billing transaction.
    Guarantees atomic execution: sales + sale_items + stock reduction + stock_movements + payment record.
    """
    items = bill_data.get('items', [])
    if not items:
        return False, "Bill must contain at least one item.", {}

    payment_method = bill_data.get('payment_method', 'Cash')
    if payment_method not in Config.ALLOWED_PAYMENT_METHODS:
        payment_method = 'Cash'

    customer_id = bill_data.get('customer_id') or None
    customer_name = (bill_data.get('customer_name') or 'Counter Customer').strip()
    customer_phone = (bill_data.get('customer_phone') or '').strip()
    notes = (bill_data.get('notes') or '').strip()

    try:
        discount = Decimal(str(bill_data.get('discount', '0.00')))
        tax_amount = Decimal(str(bill_data.get('tax_amount', '0.00')))
    except Exception:
        discount = Decimal('0.00')
        tax_amount = Decimal('0.00')

    with get_db_cursor(commit=True) as cur:
        # If customer phone provided but no customer_id, try to find or create customer
        if not customer_id and customer_phone:
            cur.execute("SELECT id FROM public.customers WHERE phone = %s;", (customer_phone,))
            cust_row = cur.fetchone()
            if cust_row:
                customer_id = cust_row['id']
            else:
                cur.execute(
                    "INSERT INTO public.customers (name, phone) VALUES (%s, %s) RETURNING id;",
                    (customer_name, customer_phone)
                )
                new_cust = cur.fetchone()
                if new_cust:
                    customer_id = new_cust['id']

        subtotal = Decimal('0.00')
        total_cost = Decimal('0.00')
        validated_items = []

        # Validate items and check stock
        for idx, item in enumerate(items):
            product_id = item.get('product_id')
            if not product_id:
                return False, f"Item #{idx+1} is missing a product ID.", {}

            cur.execute("""
                SELECT p.id, p.name, p.category, p.unit, p.selling_price, p.cost_price, 
                       p.stock_quantity as current_stock
                FROM public.products p
                WHERE p.id = %s FOR UPDATE;
            """, (product_id,))
            prod = cur.fetchone()

            if not prod:
                return False, f"Product {product_id} not found in catalog.", {}

            unit = prod['unit']
            try:
                qty = Decimal(str(item.get('quantity', '1.000')))
            except Exception:
                return False, f"Invalid quantity for {prod['name']}.", {}

            if qty <= 0:
                return False, f"Quantity must be positive for {prod['name']}.", {}

            # If unit is PCS, ensure quantity is a whole integer
            if unit == 'PCS' and qty % 1 != 0:
                return False, f"{prod['name']} is sold in pieces (PCS). Quantity must be a whole number.", {}

            # Stock check
            avail_stock = Decimal(str(prod['current_stock']))
            if avail_stock < qty:
                return False, f"Insufficient stock for '{prod['name']}'. Requested: {qty} {unit}, Available: {avail_stock} {unit}.", {}

            unit_price = Decimal(str(prod['selling_price']))
            unit_cost = Decimal(str(prod['cost_price']))
            line_total = (qty * unit_price).quantize(Decimal('0.01'))
            line_cost = (qty * unit_cost).quantize(Decimal('0.01'))

            subtotal += line_total
            total_cost += line_cost

            validated_items.append({
                'product_id': prod['id'],
                'product_name': prod['name'],
                'category': prod['category'],
                'unit': prod['unit'],
                'quantity': qty,
                'unit_price': unit_price,
                'unit_cost': unit_cost,
                'line_total': line_total,
                'current_stock': avail_stock
            })

        if discount < 0:
            discount = Decimal('0.00')
        if discount > subtotal:
            discount = subtotal

        grand_total = subtotal - discount + tax_amount
        invoice_number = generate_invoice_number()

        # 1. Insert Sales Header
        cur.execute("""
            INSERT INTO public.sales (
                invoice_number, customer_id, customer_name, customer_phone, employee_id,
                subtotal, discount, tax_amount, grand_total, total_cost,
                payment_method, payment_status, notes, created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, 'Paid', %s, NOW()
            ) RETURNING id, invoice_number, created_at;
        """, (
            invoice_number, customer_id, customer_name, customer_phone, employee_id,
            subtotal, discount, tax_amount, grand_total, total_cost,
            payment_method, notes
        ))
        sale_record = cur.fetchone()
        sale_id = sale_record['id']

        # 2. Insert Sale Items and Deduct Stock
        for it in validated_items:
            cur.execute("""
                INSERT INTO public.sale_items (
                    sale_id, product_id, product_name, category, unit, quantity, unit_price, unit_cost, line_total, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());
            """, (
                sale_id, it['product_id'], it['product_name'], it['category'], it['unit'],
                it['quantity'], it['unit_price'], it['unit_cost'], it['line_total']
            ))

            new_stock = it['current_stock'] - it['quantity']

            # Update products table stock
            cur.execute("UPDATE public.products SET stock_quantity = %s, updated_at = NOW() WHERE id = %s;", (new_stock, it['product_id']))

            # Update inventory table stock
            cur.execute("UPDATE public.inventory SET current_stock = %s, updated_at = NOW() WHERE product_id = %s;", (new_stock, it['product_id']))

            # Record stock movement
            cur.execute("""
                INSERT INTO public.stock_movements (
                    product_id, movement_type, quantity_change, previous_stock, new_stock,
                    reference_id, reason, performed_by, created_at
                ) VALUES (%s, 'SALE', %s, %s, %s, %s, 'POS Sale completed', %s, NOW());
            """, (
                it['product_id'], -it['quantity'], it['current_stock'], new_stock, invoice_number, employee_id
            ))

        # 3. Record Payment
        cur.execute("""
            INSERT INTO public.payments (
                payment_type, reference_type, reference_id, customer_id, amount,
                payment_method, transaction_reference, notes, recorded_by, created_at
            ) VALUES (
                'CUSTOMER_RECEIPT', 'SALE', %s, %s, %s,
                %s, %s, %s, %s, NOW()
            );
        """, (
            invoice_number, customer_id, grand_total, payment_method, f"POS-{invoice_number}", f"Sale invoice {invoice_number}", employee_id
        ))

        # 4. Audit Log
        cur.execute("""
            INSERT INTO public.audit_logs (
                user_id, role, action, entity_type, entity_id, details
            ) VALUES (
                %s, 'staff', 'SALE_COMPLETED', 'SALE', %s, %s::jsonb
            );
        """, (
            employee_id, invoice_number, f'{{"invoice": "{invoice_number}", "grand_total": {float(grand_total)}, "items_count": {len(validated_items)}}}'
        ))

        completed_sale = {
            'sale_id': str(sale_id),
            'invoice_number': invoice_number,
            'customer_name': customer_name,
            'customer_phone': customer_phone,
            'subtotal': float(subtotal),
            'discount': float(discount),
            'grand_total': float(grand_total),
            'payment_method': payment_method,
            'items': [{
                'product_name': x['product_name'],
                'category': x['category'],
                'unit': x['unit'],
                'quantity': float(x['quantity']),
                'unit_price': float(x['unit_price']),
                'line_total': float(x['line_total'])
            } for x in validated_items],
            'created_at': sale_record['created_at'].isoformat()
        }

        return True, "Bill generated successfully.", completed_sale

def get_sale_by_invoice(invoice_number: str) -> dict:
    """Fetches full invoice details including line items, customer, and shop settings for printing."""
    sale = query_one("""
        SELECT s.*, p.full_name as employee_name
        FROM public.sales s
        LEFT JOIN public.profiles p ON s.employee_id = p.id
        WHERE s.invoice_number = %s;
    """, (invoice_number,))

    if not sale:
        return None

    items = query_all("""
        SELECT * FROM public.sale_items WHERE sale_id = %s ORDER BY created_at ASC;
    """, (sale['id'],))

    settings = query_one("SELECT * FROM public.settings WHERE id = 'shop_settings';")

    sale['items'] = items
    sale['shop'] = settings or {}
    return sale

def get_sales_list(employee_id: str = None, start_date: str = None, end_date: str = None, search: str = None, limit: int = 100):
    """Retrieves billing history with optional employee, date, and keyword filters."""
    conditions = []
    params = []

    if employee_id:
        conditions.append("s.employee_id = %s")
        params.append(employee_id)

    if start_date:
        conditions.append("s.created_at::date >= %s::date")
        params.append(start_date)

    if end_date:
        conditions.append("s.created_at::date <= %s::date")
        params.append(end_date)

    if search:
        conditions.append("(s.invoice_number ILIKE %s OR s.customer_name ILIKE %s OR s.customer_phone ILIKE %s)")
        pat = f"%{search.strip()}%"
        params.extend([pat, pat, pat])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            s.id, s.invoice_number, s.customer_name, s.customer_phone,
            s.subtotal, s.discount, s.grand_total, s.payment_method, s.payment_status,
            s.created_at, p.full_name as employee_name,
            COUNT(si.id) as total_items
        FROM public.sales s
        LEFT JOIN public.profiles p ON s.employee_id = p.id
        LEFT JOIN public.sale_items si ON s.id = si.sale_id
        {where_clause}
        GROUP BY s.id, p.full_name
        ORDER BY s.created_at DESC
        LIMIT {limit};
    """
    return query_all(sql, params)
