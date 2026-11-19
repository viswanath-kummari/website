from decimal import Decimal
from backend.app.services.product_service import get_all_products
from backend.app.services.pos_service import create_sale_bill, get_sale_by_invoice

def test_pos_billing_execution():
    products = get_all_products(category='Chicken Items', active_only=True)
    assert len(products) > 0
    prod = products[0]

    initial_stock = Decimal(str(prod['available_stock']))
    assert initial_stock > Decimal('0.5')

    bill_payload = {
        'customer_name': 'Automated Test Customer',
        'customer_phone': '+91 99999 88888',
        'payment_method': 'Cash',
        'discount': 10.00,
        'items': [
            {
                'product_id': prod['id'],
                'quantity': 0.500 if prod['unit'] == 'KG' else 1.000
            }
        ]
    }

    success, msg, sale = create_sale_bill(bill_payload, employee_id='22222222-2222-2222-2222-222222222222')
    assert success is True, f"Billing failed: {msg}"
    assert 'invoice_number' in sale
    assert sale['grand_total'] > 0

    # Verify invoice can be retrieved
    inv = get_sale_by_invoice(sale['invoice_number'])
    assert inv is not None
    assert inv['invoice_number'] == sale['invoice_number']
    assert len(inv['items']) == 1

def test_pos_overselling_prevention():
    products = get_all_products(category='Eggs', active_only=True)
    prod = products[0]

    oversell_payload = {
        'customer_name': 'Greedy Buyer',
        'customer_phone': '+91 99999 11111',
        'payment_method': 'Cash',
        'items': [
            {
                'product_id': prod['id'],
                'quantity': 999999.000  # Impossible quantity
            }
        ]
    }

    success, msg, sale = create_sale_bill(oversell_payload)
    assert success is False
    assert "Insufficient stock" in msg
