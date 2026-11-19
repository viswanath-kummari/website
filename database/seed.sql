-- ====================================================================
-- Fresh Cut Meat Shop Management System
-- Seed Data for Supabase PostgreSQL
-- ====================================================================

-- 1. SHOP SETTINGS
INSERT INTO public.settings (
    id, shop_name, tagline, phone, email, address, opening_hours, currency_symbol, tax_percentage, low_stock_default, invoice_footer_message
) VALUES (
    'shop_settings',
    'Fresh Cut Meat Shop',
    'Artisanal Quality Fresh Chicken, Mutton, Eggs & Seafood',
    '+91 98765 43210',
    'support@freshcutmeatshop.com',
    'Shop #12, Market Main Road, Jubilee Hills, Hyderabad - 500033',
    'Mon - Sun: 7:00 AM - 9:00 PM',
    '₹',
    0.00,
    5.000,
    'Thank you for shopping at Fresh Cut! 100% Halal, Cleaned & Hygienically Packed. Please visit again.'
) ON CONFLICT (id) DO UPDATE SET
    shop_name = EXCLUDED.shop_name,
    tagline = EXCLUDED.tagline,
    phone = EXCLUDED.phone,
    address = EXCLUDED.address;

-- 2. USERS AND PROFILES (Default Admin, Employee, Customer)
-- Passwords:
-- Admin: Owner@123
-- Employee: Employee@123
-- Customer: Customer@123

INSERT INTO public.profiles (id, email, password_hash, full_name, phone, role, is_active)
VALUES 
    (
        '11111111-1111-1111-1111-111111111111',
        'owner@freshcut.com',
        crypt('Owner@123', gen_salt('bf', 10)),
        'Viswanath Kummari (Owner)',
        '+91 98765 00001',
        'admin',
        TRUE
    ),
    (
        '22222222-2222-2222-2222-222222222222',
        'employee@freshcut.com',
        crypt('Employee@123', gen_salt('bf', 10)),
        'Rahul Sharma (Billing Counter)',
        '+91 98765 00002',
        'employee',
        TRUE
    ),
    (
        '33333333-3333-3333-3333-333333333333',
        'customer@freshcut.com',
        crypt('Customer@123', gen_salt('bf', 10)),
        'Priya Reddy (Customer)',
        '+91 98765 00003',
        'customer',
        TRUE
    )
ON CONFLICT (email) DO NOTHING;

-- 3. EMPLOYEE DETAILS
INSERT INTO public.employees (id, profile_id, employee_code, designation, salary, joining_date, emergency_contact)
VALUES (
    'aa222222-2222-2222-2222-222222222222',
    '22222222-2222-2222-2222-222222222222',
    'EMP-001',
    'Head Cashier & Counter Executive',
    18500.00,
    CURRENT_DATE - INTERVAL '180 days',
    '+91 98765 99999'
) ON CONFLICT (profile_id) DO NOTHING;

-- 4. CUSTOMER PROFILE
INSERT INTO public.customers (id, profile_id, name, phone, email, address, outstanding_balance)
VALUES (
    '44444444-4444-4444-4444-444444444444',
    '33333333-3333-3333-3333-333333333333',
    'Priya Reddy',
    '+91 98765 00003',
    'customer@freshcut.com',
    'Plot 42, Road #10, Banjara Hills, Hyderabad',
    0.00
) ON CONFLICT (id) DO NOTHING;

-- 5. PRODUCTS (Strictly 4 categories: 'Chicken Items', 'Mutton Items', 'Eggs', 'Fish Items' and units: 'KG', 'PCS')

-- Chicken Items
INSERT INTO public.products (id, name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, description, image_url, is_active)
VALUES
    ('ca111111-1111-1111-1111-000000000001', 'Fresh Whole Chicken (Curry Cut)', 'Chicken Items', 'KG', 240.00, 180.00, 45.500, 10.000, 'Tender, skinless bone-in pieces crafted specifically for rich curries and gravies. Daily fresh dressed.', '/static/images/chicken_curry_cut.jpg', TRUE),
    ('ca111111-1111-1111-1111-000000000002', 'Premium Boneless Chicken Breast', 'Chicken Items', 'KG', 340.00, 260.00, 32.000, 8.000, 'Juicy, lean, tender boneless breast fillets. Ideal for grilling, stir-fries, and protein-packed fitness diets.', '/static/images/chicken_breast.jpg', TRUE),
    ('ca111111-1111-1111-1111-000000000003', 'Chicken Drumsticks (Skinless)', 'Chicken Items', 'KG', 290.00, 220.00, 24.000, 5.000, 'Plump, succulent chicken legs cut to perfection. Perfect for tandoor, frying, and roasting.', '/static/images/chicken_drumsticks.jpg', TRUE),
    ('ca111111-1111-1111-1111-000000000004', 'Chicken Keema (Fine Mince)', 'Chicken Items', 'KG', 360.00, 280.00, 18.500, 5.000, 'Freshly ground chicken breast and thigh meat. Ideal for chicken kebabs, patties, and savory keema masala.', '/static/images/chicken_keema.jpg', TRUE),
    ('ca111111-1111-1111-1111-000000000005', 'Country Chicken (Natukodi)', 'Chicken Items', 'KG', 480.00, 370.00, 15.000, 5.000, 'Authentic free-range country bird with robust flavor and firm texture. Best for traditional spicy broth and pulusu.', '/static/images/country_chicken.jpg', TRUE),
    ('ca111111-1111-1111-1111-000000000006', 'Chicken Liver & Gizzard (Cleaned)', 'Chicken Items', 'KG', 160.00, 110.00, 12.000, 4.000, 'Thoroughly cleaned nutrient-dense chicken organ cuts. Great for spicy dry roasts.', '/static/images/chicken_liver.jpg', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Mutton Items
INSERT INTO public.products (id, name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, description, image_url, is_active)
VALUES
    ('ba222222-2222-2222-2222-000000000001', 'Tender Goat Curry Cut (Mix)', 'Mutton Items', 'KG', 880.00, 710.00, 36.500, 8.000, 'Even balance of succulent bone-in shoulder, rib, and leg chunks from pasture-reared goats.', '/static/images/mutton_curry_cut.jpg', TRUE),
    ('ba222222-2222-2222-2222-000000000002', 'Premium Mutton Boneless Chunks', 'Mutton Items', 'KG', 1100.00, 890.00, 18.000, 5.000, 'Trimmed fat-free prime goat leg cuts. Ideal for biryanis, boti roasts, and gourmet gravies.', '/static/images/mutton_boneless.jpg', TRUE),
    ('ba222222-2222-2222-2222-000000000003', 'Fresh Mutton Keema (Finely Minced)', 'Mutton Items', 'KG', 960.00, 780.00, 14.000, 4.000, 'Pure goat mince from leg cuts. Rich taste, perfect for shami kebabs, samosas, and keema matar.', '/static/images/mutton_keema.jpg', TRUE),
    ('ba222222-2222-2222-2222-000000000004', 'Mutton Chops & Ribs (Chaap)', 'Mutton Items', 'KG', 940.00, 760.00, 16.000, 4.000, 'Flavorful goat ribs and prime cut chops. Ideal for pan searing, barbeque, and slow-cooked tawa fry.', '/static/images/mutton_chops.jpg', TRUE),
    ('ba222222-2222-2222-2222-000000000005', 'Fresh Goat Liver (Kaleji)', 'Mutton Items', 'KG', 650.00, 490.00, 10.000, 3.000, 'Velvety smooth, iron-rich fresh goat liver. Excellent when sautéed with crushed pepper and onions.', '/static/images/mutton_liver.jpg', TRUE),
    ('ba222222-2222-2222-2222-000000000006', 'Mutton Paya (Trotters, 4 Pcs)', 'Mutton Items', 'PCS', 380.00, 270.00, 20.000, 5.000, 'Cleaned and torched lamb trotters. Rich in collagen, unmatched for restorative bone-broth and shorba.', '/static/images/mutton_paya.jpg', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Eggs
INSERT INTO public.products (id, name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, description, image_url, is_active)
VALUES
    ('ea333333-3333-3333-3333-000000000001', 'Farm Fresh White Eggs (Pack of 6)', 'Eggs', 'PCS', 45.00, 33.00, 75.000, 15.000, 'Grade-A clean white eggs from healthy, grain-fed hens. Packed with protein and essential vitamins.', '/static/images/eggs_pack6.jpg', TRUE),
    ('ea333333-3333-3333-3333-000000000002', 'Farm Fresh White Eggs (Pack of 12)', 'Eggs', 'PCS', 88.00, 65.00, 50.000, 10.000, 'Value pack of a dozen freshly candled and sanitized white shell eggs.', '/static/images/eggs_pack12.jpg', TRUE),
    ('ea333333-3333-3333-3333-000000000003', 'Farm Fresh White Eggs (Tray of 30)', 'Eggs', 'PCS', 215.00, 162.00, 40.000, 8.000, 'Wholesale family tray of 30 eggs. Perfect for weekly breakfast and culinary baking needs.', '/static/images/eggs_tray30.jpg', TRUE),
    ('ea333333-3333-3333-3333-000000000004', 'Organic Country Brown Eggs (Pack of 6)', 'Eggs', 'PCS', 78.00, 56.00, 35.000, 10.000, 'Golden-yolk rich brown eggs laid by pasture-raised desi hens on natural herbal feeds.', '/static/images/eggs_brown.jpg', TRUE),
    ('ea333333-3333-3333-3333-000000000005', 'Kadaknath Natural Black Eggs (Pack of 6)', 'Eggs', 'PCS', 150.00, 110.00, 20.000, 5.000, 'Rare nutritional superfood eggs from purebred Kadaknath fowls. High in iron, protein, and amino acids.', '/static/images/eggs_kadaknath.jpg', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Fish Items
INSERT INTO public.products (id, name, category, unit, selling_price, cost_price, stock_quantity, min_stock_alert, description, image_url, is_active)
VALUES
    ('fa444444-4444-4444-4444-000000000001', 'Fresh River Rohu (Curry Cut)', 'Fish Items', 'KG', 260.00, 195.00, 30.000, 8.000, 'Freshwater sweet Rohu dressed and sliced into clean curry steaks. Perfect for comforting village style fish curry.', '/static/images/fish_rohu.jpg', TRUE),
    ('fa444444-4444-4444-4444-000000000002', 'Fresh River Catla (Bengal Cut)', 'Fish Items', 'KG', 280.00, 210.00, 25.000, 6.000, 'Large-size Catla fish steaks with head pieces. Ideal for authentic Bengali Macher Jhol.', '/static/images/fish_catla.jpg', TRUE),
    ('fa444444-4444-4444-4444-000000000003', 'King Seer Fish (Vanjaram Steaks)', 'Fish Items', 'KG', 980.00, 780.00, 22.000, 5.000, 'The undisputed monarch of sea fish. Firm boneless medallions designed for spicy masala rava fry.', '/static/images/fish_vanjaram.jpg', TRUE),
    ('fa444444-4444-4444-4444-000000000004', 'Jumbo Tiger Prawns (Cleaned & Deveined)', 'Fish Items', 'KG', 720.00, 540.00, 20.000, 5.000, 'Ready-to-cook plump coastal sea prawns. Deveined with tail on for garlic butter toss and biryani.', '/static/images/prawns_tiger.jpg', TRUE),
    ('fa444444-4444-4444-4444-000000000005', 'White Pomfret (Whole Cleaned & Gutted)', 'Fish Items', 'KG', 850.00, 660.00, 16.000, 4.000, 'Delicate, buttery-textured premium white pomfret. Cleaned and slashed for tandoori roasting.', '/static/images/fish_pomfret.jpg', TRUE),
    ('fa444444-4444-4444-4444-000000000006', 'Indian Salmon (Rawas Boneless Fillets)', 'Fish Items', 'KG', 890.00, 700.00, 14.000, 4.000, 'Pink, flaky delicate flesh loaded with Omega-3 fats. Superior flavor when grilled with herbs.', '/static/images/fish_rawas.jpg', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 6. INVENTORY INITIALIZATION
INSERT INTO public.inventory (product_id, current_stock, reorder_threshold, last_restocked_at)
SELECT id, stock_quantity, min_stock_alert, NOW()
FROM public.products
ON CONFLICT (product_id) DO UPDATE SET
    current_stock = EXCLUDED.current_stock,
    reorder_threshold = EXCLUDED.reorder_threshold;

-- 7. SUPPLIERS
INSERT INTO public.suppliers (id, name, contact_person, phone, email, address, outstanding_balance)
VALUES
    ('ba111111-1111-1111-1111-111111111111', 'Deccan Broiler Farms & Hatcheries', 'Suresh Naidu', '+91 94401 23456', 'orders@deccanfarms.com', 'Survey #88, Shamshabad Rural, Hyderabad', 12400.00),
    ('ba222222-2222-2222-2222-222222222222', 'Telangana Sheep & Goat Breeders Co-op', 'Mohd. Khaleel', '+91 98490 87654', 'khaleel@tgcoopmutton.org', 'Nalgonda Highway Junction, Hayathnagar', 35000.00),
    ('ba333333-3333-3333-3333-333333333333', 'Godavari Coastal Fisheries & Prawns', 'K. Venkat Rao', '+91 97012 34567', 'sales@godavaricoastal.com', 'Fisheries Wharf, Kakinada / Hyderabad Depot', 18500.00)
ON CONFLICT (id) DO NOTHING;

-- 8. INITIAL EXPENSES
INSERT INTO public.expenses (category, amount, expense_date, payment_method, notes, recorded_by)
VALUES
    ('Shop rent', 35000.00, CURRENT_DATE - INTERVAL '15 days', 'Bank Transfer', 'Monthly commercial lease for Jubilee Hills retail store', '11111111-1111-1111-1111-111111111111'),
    ('Electricity', 11200.00, CURRENT_DATE - INTERVAL '10 days', 'UPI', 'Commercial electricity bill for cold room, freezers & display chillers', '11111111-1111-1111-1111-111111111111'),
    ('Packaging', 4800.00, CURRENT_DATE - INTERVAL '6 days', 'Cash', 'Food-grade vacuum pouches, meat trays, kraft carry bags', '11111111-1111-1111-1111-111111111111'),
    ('Transportation', 3200.00, CURRENT_DATE - INTERVAL '3 days', 'UPI', 'Refrigerated van logistics from morning wholesale depot', '11111111-1111-1111-1111-111111111111'),
    ('Maintenance', 2500.00, CURRENT_DATE - INTERVAL '1 day', 'Cash', 'Meat slicer blade sharpening and cold-storage thermostat servicing', '11111111-1111-1111-1111-111111111111');

-- 9. RECENT COMPLETED POS SALES (For rich initial dashboard analytics)
-- Sale 1
INSERT INTO public.sales (id, invoice_number, customer_id, customer_name, customer_phone, employee_id, subtotal, discount, tax_amount, grand_total, total_cost, payment_method, payment_status, notes, created_at)
VALUES (
    'aa111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'INV-2026-0001',
    '44444444-4444-4444-4444-444444444444',
    'Priya Reddy',
    '+91 98765 00003',
    '22222222-2222-2222-2222-222222222222',
    820.00,
    20.00,
    0.00,
    800.00,
    620.00,
    'UPI',
    'Paid',
    'Walk-in customer regular discount applied',
    NOW() - INTERVAL '2 hours'
) ON CONFLICT (invoice_number) DO NOTHING;

INSERT INTO public.sale_items (sale_id, product_id, product_name, category, unit, quantity, unit_price, unit_cost, line_total, created_at)
VALUES 
    ('aa111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ca111111-1111-1111-1111-000000000001', 'Fresh Whole Chicken (Curry Cut)', 'Chicken Items', 'KG', 2.000, 240.00, 180.00, 480.00, NOW() - INTERVAL '2 hours'),
    ('aa111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'ca111111-1111-1111-1111-000000000002', 'Premium Boneless Chicken Breast', 'Chicken Items', 'KG', 1.000, 340.00, 260.00, 340.00, NOW() - INTERVAL '2 hours');

-- Sale 2
INSERT INTO public.sales (id, invoice_number, customer_id, customer_name, customer_phone, employee_id, subtotal, discount, tax_amount, grand_total, total_cost, payment_method, payment_status, notes, created_at)
VALUES (
    'bb222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    'INV-2026-0002',
    NULL,
    'Rajesh Verma',
    '+91 99887 76655',
    '22222222-2222-2222-2222-222222222222',
    1325.00,
    0.00,
    0.00,
    1325.00,
    1043.00,
    'Cash',
    'Paid',
    'Counter cash billing',
    NOW() - INTERVAL '1 hour'
) ON CONFLICT (invoice_number) DO NOTHING;

INSERT INTO public.sale_items (sale_id, product_id, product_name, category, unit, quantity, unit_price, unit_cost, line_total, created_at)
VALUES 
    ('bb222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'ba222222-2222-2222-2222-000000000001', 'Tender Goat Curry Cut (Mix)', 'Mutton Items', 'KG', 1.000, 880.00, 710.00, 880.00, NOW() - INTERVAL '1 hour'),
    ('bb222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'ea333333-3333-3333-3333-000000000001', 'Farm Fresh White Eggs (Pack of 6)', 'Eggs', 'PCS', 1.000, 45.00, 33.00, 45.00, NOW() - INTERVAL '1 hour'),
    ('bb222222-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'ba222222-2222-2222-2222-000000000006', 'Mutton Paya (Trotters, 4 Pcs)', 'Mutton Items', 'PCS', 1.000, 380.00, 270.00, 380.00, NOW() - INTERVAL '1 hour');

-- 10. SAMPLE ONLINE ORDER
INSERT INTO public.online_orders (
    id, order_number, customer_profile_id, customer_name, customer_phone, customer_email, subtotal, discount, grand_total, status, payment_method, pickup_time, notes, created_at
) VALUES (
    'da111111-1111-1111-1111-000000000001',
    'ORD-2026-0001',
    '33333333-3333-3333-3333-333333333333',
    'Priya Reddy',
    '+91 98765 00003',
    'customer@freshcut.com',
    1240.00,
    0.00,
    1240.00,
    'Pending',
    'Cash on Collection',
    'Today at 6:30 PM',
    'Please pack neatly in separate vacuum bags',
    NOW() - INTERVAL '30 minutes'
) ON CONFLICT (order_number) DO NOTHING;

INSERT INTO public.online_order_items (order_id, product_id, product_name, category, unit, quantity, unit_price, line_total)
VALUES
    ('da111111-1111-1111-1111-000000000001', 'fa444444-4444-4444-4444-000000000003', 'King Seer Fish (Vanjaram Steaks)', 'Fish Items', 'KG', 1.000, 980.00, 980.00),
    ('da111111-1111-1111-1111-000000000001', 'fa444444-4444-4444-4444-000000000001', 'Fresh River Rohu (Curry Cut)', 'Fish Items', 'KG', 1.000, 260.00, 260.00);

-- 11. AUDIT LOG INITIALIZATION
INSERT INTO public.audit_logs (user_id, user_name, role, action, entity_type, entity_id, details)
VALUES 
    ('11111111-1111-1111-1111-111111111111', 'Viswanath Kummari (Owner)', 'admin', 'SYSTEM_INITIALIZATION', 'SYSTEM', 'INIT-001', '{"status": "Database initialized with production schema, products and settings"}'::jsonb);
