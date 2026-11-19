import json
from backend.app import create_app

def test_categories_api():
    app = create_app()
    client = app.test_client()
    resp = client.get('/api/v1/categories')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['success'] is True
    assert set(data['categories']) == {'Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items'}

def test_products_api():
    app = create_app()
    client = app.test_client()
    resp = client.get('/api/v1/products')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['success'] is True
    assert len(data['data']) > 0

def test_cart_validate_api():
    app = create_app()
    client = app.test_client()
    
    # Fetch a product to test
    resp_prod = client.get('/api/v1/products')
    prods = json.loads(resp_prod.data)['data']
    p = prods[0]

    payload = {
        'items': [
            {'product_id': p['id'], 'quantity': 2.0}
        ]
    }
    resp = client.post('/api/v1/cart/validate', json=payload)
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['success'] is True
    assert data['subtotal'] > 0

def test_shop_settings_api():
    app = create_app()
    client = app.test_client()
    resp = client.get('/api/v1/shop-settings')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data['success'] is True
    assert 'shop_name' in data['data']

