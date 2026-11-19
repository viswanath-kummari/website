from backend.app.services.auth_service import hash_password, check_password, authenticate, register_customer, generate_jwt_token

def test_password_hashing():
    pwd = "SecretPassword123"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert check_password(pwd, hashed) is True
    assert check_password("WrongPassword", hashed) is False

def test_jwt_generation():
    fake_user = {
        'id': '11111111-1111-1111-1111-111111111111',
        'email': 'test@freshcut.com',
        'role': 'admin',
        'full_name': 'Test Admin'
    }
    token = generate_jwt_token(fake_user)
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20

def test_owner_authentication_success():
    success, msg, user = authenticate('owner@freshcut.com', 'Owner@123', intended_role='admin')
    assert success is True
    assert user['role'] == 'admin'
    assert 'token' in user

def test_employee_authentication_success():
    success, msg, user = authenticate('employee@freshcut.com', 'Employee@123', intended_role='employee')
    assert success is True
    assert user['role'] == 'employee'

def test_role_mismatch_rejection():
    # Attempting to login as admin with customer credentials must fail
    success, msg, user = authenticate('customer@freshcut.com', 'Customer@123', intended_role='admin')
    assert success is False
    assert "Access denied" in msg

def test_invalid_password_rejection():
    success, msg, user = authenticate('owner@freshcut.com', 'WrongPassword999', intended_role='admin')
    assert success is False
