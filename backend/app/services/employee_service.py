from decimal import Decimal
from backend.app.db import get_db_cursor, query_one, query_all, execute
from backend.app.services.auth_service import hash_password

def get_employees_list():
    """Retrieves all employee profiles with employee code, designation, sales metrics, and status."""
    sql = """
        SELECT 
            p.id as profile_id,
            p.full_name,
            p.email,
            p.phone,
            p.is_active,
            p.created_at,
            e.id as employee_id,
            e.employee_code,
            e.designation,
            e.salary,
            e.joining_date,
            e.emergency_contact,
            COUNT(DISTINCT s.id) as total_bills_generated,
            COALESCE(SUM(s.grand_total), 0.00) as total_sales_volume
        FROM public.profiles p
        JOIN public.employees e ON p.id = e.profile_id
        LEFT JOIN public.sales s ON p.id = s.employee_id
        WHERE p.role = 'employee'
        GROUP BY p.id, e.id
        ORDER BY p.is_active DESC, e.employee_code ASC;
    """
    return query_all(sql)

def create_employee(data: dict, admin_id: str = None) -> tuple[bool, str, dict]:
    """Creates a new employee account with profile and employee records."""
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    phone = (data.get('phone') or '').strip()
    employee_code = (data.get('employee_code') or '').strip().upper()
    designation = (data.get('designation') or 'Shop Assistant').strip()
    
    try:
        salary = Decimal(str(data.get('salary', '0.00')))
    except Exception:
        salary = Decimal('0.00')

    if not full_name or not email or not password or not employee_code:
        return False, "Full name, email, password, and employee code are required.", {}

    if len(password) < 6:
        return False, "Password must be at least 6 characters.", {}

    with get_db_cursor(commit=True) as cur:
        # Check existing email
        cur.execute("SELECT id FROM public.profiles WHERE LOWER(email) = LOWER(%s);", (email,))
        if cur.fetchone():
            return False, "An account with this email address already exists.", {}

        # Check existing employee code
        cur.execute("SELECT id FROM public.employees WHERE employee_code = %s;", (employee_code,))
        if cur.fetchone():
            return False, f"Employee code '{employee_code}' is already assigned.", {}

        pwd_hash = hash_password(password)

        # 1. Insert Profile with role 'employee'
        cur.execute("""
            INSERT INTO public.profiles (email, password_hash, full_name, phone, role, is_active)
            VALUES (%s, %s, %s, %s, 'employee', TRUE)
            RETURNING id, email, full_name, role;
        """, (email, pwd_hash, full_name, phone))
        profile = cur.fetchone()
        profile_id = profile['id']

        # 2. Insert Employee record
        cur.execute("""
            INSERT INTO public.employees (profile_id, employee_code, designation, salary, emergency_contact)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, employee_code, designation;
        """, (profile_id, employee_code, designation, salary, data.get('emergency_contact', '')))
        emp = cur.fetchone()

        # 3. Audit log
        cur.execute("""
            INSERT INTO public.audit_logs (user_id, role, action, entity_type, entity_id, details)
            VALUES (%s, 'admin', 'EMPLOYEE_CREATED', 'EMPLOYEE', %s, %s::jsonb);
        """, (
            admin_id, str(profile_id),
            f'{{"employee_code": "{employee_code}", "name": "{full_name}", "email": "{email}"}}'
        ))

        return True, "Employee account created successfully.", {
            'profile_id': str(profile_id),
            'employee_code': employee_code,
            'full_name': full_name,
            'email': email
        }

def toggle_employee_status(profile_id: str, is_active: bool, admin_id: str = None) -> tuple[bool, str]:
    """Activates or deactivates an employee account."""
    execute(
        "UPDATE public.profiles SET is_active = %s, updated_at = NOW() WHERE id = %s AND role = 'employee';",
        (is_active, profile_id)
    )
    status_str = "activated" if is_active else "deactivated"
    return True, f"Employee account has been {status_str}."

def get_employee_sales_summary(profile_id: str):
    """Retrieves billing performance and recent sales for a specific employee."""
    stats = query_one("""
        SELECT 
            COUNT(id) as total_bills,
            COALESCE(SUM(grand_total), 0.00) as total_revenue,
            COALESCE(SUM(CASE WHEN created_at::date = CURRENT_DATE THEN grand_total ELSE 0.00 END), 0.00) as today_revenue,
            COUNT(CASE WHEN created_at::date = CURRENT_DATE THEN id ELSE NULL END) as today_bills
        FROM public.sales
        WHERE employee_id = %s;
    """, (profile_id,))

    recent_bills = query_all("""
        SELECT id, invoice_number, customer_name, grand_total, payment_method, created_at
        FROM public.sales
        WHERE employee_id = %s
        ORDER BY created_at DESC
        LIMIT 25;
    """, (profile_id,))

    return {
        'stats': stats or {},
        'recent_bills': recent_bills or []
    }
