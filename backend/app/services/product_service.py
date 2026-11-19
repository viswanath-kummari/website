from decimal import Decimal
from backend.app.config import Config
from backend.app.db import query_one, query_all, execute, execute_returning

def get_all_products(category=None, active_only=True, search=None):
    """
    Retrieves products with optional category, status, and search filters.
    Includes inventory current_stock and reserved_stock.
    """
    conditions = []
    params = []

    if active_only:
        conditions.append("p.is_active = TRUE")

    if category and category in Config.ALLOWED_CATEGORIES:
        conditions.append("p.category = %s")
        params.append(category)

    if search:
        conditions.append("(p.name ILIKE %s OR p.description ILIKE %s)")
        search_pattern = f"%{search.strip()}%"
        params.extend([search_pattern, search_pattern])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT 
            p.id, p.name, p.category, p.unit, 
            p.selling_price, p.cost_price, 
            COALESCE(i.current_stock, p.stock_quantity) as stock_quantity,
            COALESCE(i.reserved_stock, 0.000) as reserved_stock,
            (COALESCE(i.current_stock, p.stock_quantity) - COALESCE(i.reserved_stock, 0.000)) as available_stock,
            p.min_stock_alert, p.description, p.image_url, 
            p.is_active, p.created_at, p.updated_at
        FROM public.products p
        LEFT JOIN public.inventory i ON p.id = i.product_id
        {where_clause}
        ORDER BY p.category, p.name ASC;
    """
    return query_all(sql, params)

def get_product_by_id(product_id: str):
    """Fetches single product details with inventory."""
    sql = """
        SELECT 
            p.id, p.name, p.category, p.unit, 
            p.selling_price, p.cost_price, 
            COALESCE(i.current_stock, p.stock_quantity) as stock_quantity,
            COALESCE(i.reserved_stock, 0.000) as reserved_stock,
            (COALESCE(i.current_stock, p.stock_quantity) - COALESCE(i.reserved_stock, 0.000)) as available_stock,
            p.min_stock_alert, p.description, p.image_url, 
            p.is_active, p.created_at, p.updated_at
        FROM public.products p
        LEFT JOIN public.inventory i ON p.id = i.product_id
        WHERE p.id = %s;
    """
    return query_one(sql, (product_id,))

def create_product(data: dict, user_id: str = None) -> tuple[bool, str, dict]:
    """Creates a new product with strict category and unit validation."""
    name = (data.get('name') or '').strip()
    category = (data.get('category') or '').strip()
    unit = (data.get('unit') or '').strip().upper()
    
    if not name:
        return False, "Product name is required.", {}

    if category not in Config.ALLOWED_CATEGORIES:
        return False, f"Invalid category. Allowed categories: {', '.join(Config.ALLOWED_CATEGORIES)}", {}

    if unit not in Config.ALLOWED_UNITS:
        return False, f"Invalid unit. Allowed units: {', '.join(Config.ALLOWED_UNITS)}", {}

    try:
        selling_price = Decimal(str(data.get('selling_price', '0.00')))
        cost_price = Decimal(str(data.get('cost_price', '0.00')))
        stock_quantity = Decimal(str(data.get('stock_quantity', '0.000')))
        min_stock_alert = Decimal(str(data.get('min_stock_alert', '5.000')))
    except Exception:
        return False, "Prices and stock quantities must be valid numbers.", {}

    if selling_price < 0 or cost_price < 0 or stock_quantity < 0:
        return False, "Prices and stock quantities cannot be negative.", {}

    description = (data.get('description') or '').strip()
    image_url = (data.get('image_url') or '').strip() or '/static/images/default_product.jpg'

    sql_product = """
        INSERT INTO public.products (
            name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, description, image_url, is_active
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
        RETURNING id, name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, is_active;
    """
    product = execute_returning(
        sql_product,
        (name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, description, image_url)
    )

    if not product:
        return False, "Failed to create product.", {}

    product_id = str(product['id'])

    # Create associated inventory record
    execute(
        """
        INSERT INTO public.inventory (product_id, current_stock, reorder_threshold, last_restocked_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (product_id) DO UPDATE SET
            current_stock = EXCLUDED.current_stock,
            reorder_threshold = EXCLUDED.reorder_threshold;
        """,
        (product_id, stock_quantity, min_stock_alert)
    )

    # Initial stock movement
    if stock_quantity > 0:
        execute(
            """
            INSERT INTO public.stock_movements (
                product_id, movement_type, quantity_change, previous_stock, new_stock, reference_id, reason, performed_by
            ) VALUES (%s, 'ADJUSTMENT', %s, 0.000, %s, 'INIT', 'Initial product stock creation', %s);
            """,
            (product_id, stock_quantity, stock_quantity, user_id)
        )

    return True, "Product created successfully.", product

def update_product(product_id: str, data: dict, user_id: str = None) -> tuple[bool, str, dict]:
    """Updates product attributes and prices."""
    existing = get_product_by_id(product_id)
    if not existing:
        return False, "Product not found.", {}

    name = (data.get('name') or existing['name']).strip()
    category = (data.get('category') or existing['category']).strip()
    unit = (data.get('unit') or existing['unit']).strip().upper()

    if category not in Config.ALLOWED_CATEGORIES:
        return False, f"Invalid category. Allowed: {', '.join(Config.ALLOWED_CATEGORIES)}", {}

    if unit not in Config.ALLOWED_UNITS:
        return False, f"Invalid unit. Allowed: {', '.join(Config.ALLOWED_UNITS)}", {}

    try:
        selling_price = Decimal(str(data.get('selling_price', existing['selling_price'])))
        cost_price = Decimal(str(data.get('cost_price', existing['cost_price'])))
        min_stock_alert = Decimal(str(data.get('min_stock_alert', existing['min_stock_alert'])))
    except Exception:
        return False, "Prices and thresholds must be valid numbers.", {}

    description = (data.get('description') or existing.get('description') or '').strip()
    image_url = (data.get('image_url') or existing.get('image_url') or '').strip()

    sql = """
        UPDATE public.products
        SET name = %s, category = %s, unit = %s, selling_price = %s, cost_price = %s,
            min_stock_alert = %s, description = %s, image_url = %s, updated_at = NOW()
        WHERE id = %s
        RETURNING *;
    """
    updated = execute_returning(
        sql,
        (name, category, unit, selling_price, cost_price, min_stock_alert, description, image_url, product_id)
    )

    # Sync reorder threshold in inventory
    execute(
        "UPDATE public.inventory SET reorder_threshold = %s, updated_at = NOW() WHERE product_id = %s;",
        (min_stock_alert, product_id)
    )

    return True, "Product updated successfully.", updated

def update_product_price(product_id: str, selling_price, cost_price=None, user_id: str = None) -> tuple[bool, str]:
    """Quick update of selling price and cost price."""
    try:
        sp = Decimal(str(selling_price))
        if sp < 0:
            return False, "Selling price cannot be negative."
    except Exception:
        return False, "Invalid selling price format."

    if cost_price is not None:
        try:
            cp = Decimal(str(cost_price))
            if cp < 0:
                return False, "Cost price cannot be negative."
            sql = "UPDATE public.products SET selling_price = %s, cost_price = %s, updated_at = NOW() WHERE id = %s;"
            params = (sp, cp, product_id)
        except Exception:
            return False, "Invalid cost price format."
    else:
        sql = "UPDATE public.products SET selling_price = %s, updated_at = NOW() WHERE id = %s;"
        params = (sp, product_id)

    rowcount = execute(sql, params)
    if rowcount == 0:
        return False, "Product not found."
    return True, "Price updated successfully."

def toggle_product_status(product_id: str, is_active: bool) -> tuple[bool, str]:
    """Activates or deactivates a product."""
    execute(
        "UPDATE public.products SET is_active = %s, updated_at = NOW() WHERE id = %s;",
        (is_active, product_id)
    )
    status_str = "activated" if is_active else "deactivated"
    return True, f"Product successfully {status_str}."
