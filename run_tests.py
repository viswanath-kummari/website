import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tests.test_auth import (
    test_password_hashing, test_jwt_generation,
    test_owner_authentication_success, test_employee_authentication_success,
    test_role_mismatch_rejection, test_invalid_password_rejection
)
from tests.test_pos_billing import (
    test_pos_billing_execution, test_pos_overselling_prevention
)
from tests.test_api import (
    test_categories_api, test_products_api,
    test_cart_validate_api, test_shop_settings_api
)

tests = [
    ("Auth: Password Hashing", test_password_hashing),
    ("Auth: JWT Generation", test_jwt_generation),
    ("Auth: Owner Sign In", test_owner_authentication_success),
    ("Auth: Employee Sign In", test_employee_authentication_success),
    ("Auth: Role Mismatch Rejection", test_role_mismatch_rejection),
    ("Auth: Invalid Password Rejection", test_invalid_password_rejection),
    ("POS: Bill Creation & Stock Deduction", test_pos_billing_execution),
    ("POS: Overselling Prevention", test_pos_overselling_prevention),
    ("API: Strict 4 Categories Endpoint", test_categories_api),
    ("API: Products Catalog Endpoint", test_products_api),
    ("API: Cart Live Validation Endpoint", test_cart_validate_api),
    ("API: Shop Settings Endpoint", test_shop_settings_api),
]

passed = 0
failed = 0

print("======================================================================")
print("RUNNING FRESH CUT MEAT SHOP TEST SUITE")
print("======================================================================")

for name, test_fn in tests:
    try:
        test_fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__} -> {e}")
        failed += 1

print("======================================================================")
print(f"RESULTS: {passed} PASSED, {failed} FAILED (TOTAL {len(tests)})")
print("======================================================================")

if failed > 0:
    sys.exit(1)
