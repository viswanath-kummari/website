from decimal import Decimal
from backend.app.db import query_one, query_all, execute

def get_shop_settings():
    """Retrieves current shop configuration."""
    row = query_one("SELECT * FROM public.settings WHERE id = 'shop_settings';")
    if not row:
        return {
            'shop_name': 'Fresh Cut Meat Shop',
            'tagline': 'Premium Fresh Meat & Poultry',
            'phone': '+91 98765 43210',
            'email': 'support@freshcutmeatshop.com',
            'address': 'Shop #12, Market Main Road, Jubilee Hills, Hyderabad',
            'opening_hours': 'Mon - Sun: 7:00 AM - 9:00 PM',
            'currency_symbol': '₹',
            'tax_percentage': 0.00,
            'low_stock_default': 5.000,
            'invoice_footer_message': 'Thank you for shopping at Fresh Cut!'
        }
    return row

def update_shop_settings(data: dict) -> tuple[bool, str]:
    """Updates shop details, currency, address, and invoice footer."""
    shop_name = (data.get('shop_name') or 'Fresh Cut Meat Shop').strip()
    tagline = (data.get('tagline') or '').strip()
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    address = (data.get('address') or '').strip()
    opening_hours = (data.get('opening_hours') or '').strip()
    currency_symbol = (data.get('currency_symbol') or '₹').strip()
    invoice_footer_message = (data.get('invoice_footer_message') or '').strip()

    try:
        tax_percentage = Decimal(str(data.get('tax_percentage', '0.00')))
        low_stock_default = Decimal(str(data.get('low_stock_default', '5.000')))
    except Exception:
        tax_percentage = Decimal('0.00')
        low_stock_default = Decimal('5.000')

    execute("""
        INSERT INTO public.settings (
            id, shop_name, tagline, phone, email, address, opening_hours,
            currency_symbol, tax_percentage, low_stock_default, invoice_footer_message, updated_at
        ) VALUES (
            'shop_settings', %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, NOW()
        ) ON CONFLICT (id) DO UPDATE SET
            shop_name = EXCLUDED.shop_name,
            tagline = EXCLUDED.tagline,
            phone = EXCLUDED.phone,
            email = EXCLUDED.email,
            address = EXCLUDED.address,
            opening_hours = EXCLUDED.opening_hours,
            currency_symbol = EXCLUDED.currency_symbol,
            tax_percentage = EXCLUDED.tax_percentage,
            low_stock_default = EXCLUDED.low_stock_default,
            invoice_footer_message = EXCLUDED.invoice_footer_message,
            updated_at = NOW();
    """, (
        shop_name, tagline, phone, email, address, opening_hours,
        currency_symbol, tax_percentage, low_stock_default, invoice_footer_message
    ))

    return True, "Shop settings updated successfully."

def get_audit_logs(limit: int = 100):
    """Retrieves system audit trail."""
    sql = """
        SELECT 
            a.*,
            COALESCE(p.full_name, a.user_name, 'System') as actor_name
        FROM public.audit_logs a
        LEFT JOIN public.profiles p ON a.user_id = p.id
        ORDER BY a.created_at DESC
        LIMIT %s;
    """
    return query_all(sql, (limit,))
