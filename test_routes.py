import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app import create_app

app = create_app()
client = app.test_client()

routes_to_test = [
    # Public & Auth
    ("/", 200, "Storefront Home"),
    ("/products", 200, "Catalog"),
    ("/cart", 200, "Cart"),
    ("/checkout", 200, "Checkout"),
    ("/auth/landing", 200, "Login Landing"),
    ("/auth/login/owner", 200, "Owner Login"),
    ("/auth/login/employee", 200, "Employee Login"),
    ("/auth/login/customer", 200, "Customer Login"),
    ("/auth/register/customer", 200, "Customer Register"),
]

admin_routes = [
    ("/admin/dashboard", 200, "Admin Dashboard"),
    ("/admin/products", 200, "Admin Products"),
    ("/admin/prices", 200, "Admin Prices"),
    ("/admin/pos", 200, "Admin POS"),
    ("/admin/inventory", 200, "Admin Inventory"),
    ("/admin/orders", 200, "Admin Orders"),
    ("/admin/customers", 200, "Admin Customers"),
    ("/admin/employees", 200, "Admin Employees"),
    ("/admin/suppliers", 200, "Admin Suppliers"),
    ("/admin/purchases", 200, "Admin Purchases"),
    ("/admin/expenses", 200, "Admin Expenses"),
    ("/admin/payments", 200, "Admin Payments"),
    ("/admin/sales", 200, "Admin Sales History"),
    ("/admin/reports", 200, "Admin Reports"),
    ("/admin/settings", 200, "Admin Settings"),
    ("/admin/audit-logs", 200, "Admin Audit Logs"),
    ("/admin/profile", 200, "Admin Profile"),
]

employee_routes = [
    ("/employee/dashboard", 200, "Employee Dashboard"),
    ("/employee/pos", 200, "Employee POS"),
    ("/employee/sales", 200, "Employee Sales"),
    ("/employee/stock", 200, "Employee Stock View"),
    ("/employee/orders", 200, "Employee Orders"),
    ("/employee/profile", 200, "Employee Profile"),
]

print("--- Testing Public & Customer Routes ---")
all_passed = True
for path, expected, label in routes_to_test:
    res = client.get(path)
    if res.status_code == expected:
        print(f"  [OK] {label} ({path}) -> {res.status_code}")
    else:
        print(f"  [FAIL] {label} ({path}) -> {res.status_code} (Expected {expected})")
        all_passed = False

print("\n--- Testing Owner / Admin 18 Sections (Authenticated) ---")
with client.session_transaction() as sess:
    sess['user_id'] = '11111111-1111-1111-1111-111111111111'
    sess['user_role'] = 'admin'
    sess['user_name'] = 'Viswanath Kummari (Owner)'

for path, expected, label in admin_routes:
    res = client.get(path)
    if res.status_code == expected:
        print(f"  [OK] {label} ({path}) -> {res.status_code}")
    else:
        print(f"  [FAIL] {label} ({path}) -> {res.status_code} (Expected {expected})")
        all_passed = False

print("\n--- Testing Employee Operational Portal (Authenticated) ---")
with client.session_transaction() as sess:
    sess['user_id'] = '22222222-2222-2222-2222-222222222222'
    sess['user_role'] = 'employee'
    sess['user_name'] = 'Rahul Sharma'

for path, expected, label in employee_routes:
    res = client.get(path)
    if res.status_code == expected:
        print(f"  [OK] {label} ({path}) -> {res.status_code}")
    else:
        print(f"  [FAIL] {label} ({path}) -> {res.status_code} (Expected {expected})")
        all_passed = False

# Test Employee trying to access Admin route (must be redirected or forbidden)
res = client.get("/admin/dashboard")
print(f"\nSecurity check: Employee accessing /admin/dashboard -> Status {res.status_code} (Redirected to /employee/dashboard: {res.headers.get('Location')})")
assert res.status_code == 302, "Employee must be denied admin access!"

print("\n========================================================")
if all_passed:
    print("ALL ROUTES VERIFIED AND FUNCTIONAL!")
else:
    print("SOME ROUTES FAILED!")
    sys.exit(1)
print("========================================================")

