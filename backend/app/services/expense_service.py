from decimal import Decimal
from datetime import datetime
from backend.app.db import get_db_cursor, query_one, query_all

ALLOWED_EXPENSE_CATEGORIES = [
    'Shop rent', 'Electricity', 'Employee salaries',
    'Transportation', 'Packaging', 'Maintenance', 'Other business expenses'
]

def get_expenses_list(category: str = None, start_date: str = None, end_date: str = None, limit: int = 100):
    """Retrieves business expenses with optional category and date range filters."""
    conditions = []
    params = []

    if category and category in ALLOWED_EXPENSE_CATEGORIES:
        conditions.append("e.category = %s")
        params.append(category)

    if start_date:
        conditions.append("e.expense_date >= %s::date")
        params.append(start_date)

    if end_date:
        conditions.append("e.expense_date <= %s::date")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            e.*,
            COALESCE(p.full_name, 'Admin') as recorded_by_name
        FROM public.expenses e
        LEFT JOIN public.profiles p ON e.recorded_by = p.id
        {where_clause}
        ORDER BY e.expense_date DESC, e.created_at DESC
        LIMIT {limit};
    """
    return query_all(sql, params)

def record_expense(data: dict, admin_id: str = None) -> tuple[bool, str, dict]:
    """Records a new business operating expense and associated payment transaction."""
    category = (data.get('category') or '').strip()
    if category not in ALLOWED_EXPENSE_CATEGORIES:
        return False, f"Invalid category. Allowed: {', '.join(ALLOWED_EXPENSE_CATEGORIES)}", {}

    try:
        amount = Decimal(str(data.get('amount', '0.00')))
        if amount <= 0:
            return False, "Expense amount must be greater than zero.", {}
    except Exception:
        return False, "Invalid expense amount.", {}

    expense_date = data.get('expense_date') or datetime.now().strftime('%Y-%m-%d')
    payment_method = data.get('payment_method', 'Cash')
    notes = (data.get('notes') or '').strip()
    attachment_url = (data.get('attachment_url') or '').strip()

    with get_db_cursor(commit=True) as cur:
        # Insert expense
        cur.execute("""
            INSERT INTO public.expenses (
                category, amount, expense_date, payment_method, notes, attachment_url, recorded_by, created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, NOW()
            ) RETURNING *;
        """, (category, amount, expense_date, payment_method, notes, attachment_url, admin_id))
        expense = cur.fetchone()

        # Insert corresponding payment record
        cur.execute("""
            INSERT INTO public.payments (
                payment_type, reference_type, reference_id, amount,
                payment_method, transaction_reference, notes, recorded_by, created_at
            ) VALUES (
                'EXPENSE_PAYMENT', 'EXPENSE', %s, %s,
                %s, %s, %s, %s, NOW()
            );
        """, (
            str(expense['id']), amount, payment_method, f"EXP-{category[:4].upper()}", notes, admin_id
        ))

        # Audit log
        cur.execute("""
            INSERT INTO public.audit_logs (user_id, role, action, entity_type, entity_id, details)
            VALUES (%s, 'admin', 'EXPENSE_RECORDED', 'EXPENSE', %s, %s::jsonb);
        """, (
            admin_id, str(expense['id']),
            f'{{"category": "{category}", "amount": {float(amount)}, "date": "{expense_date}"}}'
        ))

        return True, "Expense recorded successfully.", expense

def get_payments_list(payment_type: str = None, limit: int = 100):
    """Retrieves all payment transactions (Customer receipts, supplier payouts, expense payouts)."""
    conditions = []
    params = []

    if payment_type:
        conditions.append("pm.payment_type = %s")
        params.append(payment_type)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            pm.*,
            c.name as customer_name,
            s.name as supplier_name,
            u.full_name as recorded_by_name
        FROM public.payments pm
        LEFT JOIN public.customers c ON pm.customer_id = c.id
        LEFT JOIN public.suppliers s ON pm.supplier_id = s.id
        LEFT JOIN public.profiles u ON pm.recorded_by = u.id
        {where_clause}
        ORDER BY pm.created_at DESC
        LIMIT {limit};
    """
    return query_all(sql, params)
