-- ====================================================================
-- Fresh Cut Meat Shop Management System
-- Row Level Security (RLS) Policies for Supabase PostgreSQL
-- ====================================================================

-- Enable RLS on core tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sales ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sale_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.online_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.online_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stock_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.purchase_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

-- Helper functions for role identification
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'admin' AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.is_employee()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'employee' AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 1. PROFILES POLICIES
DROP POLICY IF EXISTS "Allow user to view own profile or admin view all" ON public.profiles;
CREATE POLICY "Allow user to view own profile or admin view all"
ON public.profiles FOR SELECT
USING (auth.uid() = id OR public.is_admin());

DROP POLICY IF EXISTS "Allow user to update own profile" ON public.profiles;
CREATE POLICY "Allow user to update own profile"
ON public.profiles FOR UPDATE
USING (auth.uid() = id OR public.is_admin());

-- 2. PRODUCTS POLICIES
-- Everyone (including anon customers) can view active products
DROP POLICY IF EXISTS "Anyone can view active products" ON public.products;
CREATE POLICY "Anyone can view active products"
ON public.products FOR SELECT
USING (is_active = TRUE OR public.is_admin() OR public.is_employee());

-- Only admin can modify products
DROP POLICY IF EXISTS "Only admin can insert products" ON public.products;
CREATE POLICY "Only admin can insert products"
ON public.products FOR INSERT
WITH CHECK (public.is_admin());

DROP POLICY IF EXISTS "Only admin can update products" ON public.products;
CREATE POLICY "Only admin can update products"
ON public.products FOR UPDATE
USING (public.is_admin());

DROP POLICY IF EXISTS "Only admin can delete products" ON public.products;
CREATE POLICY "Only admin can delete products"
ON public.products FOR DELETE
USING (public.is_admin());

-- 3. CUSTOMERS POLICIES
DROP POLICY IF EXISTS "Admin and employee view customers" ON public.customers;
CREATE POLICY "Admin and employee view customers"
ON public.customers FOR SELECT
USING (public.is_admin() OR public.is_employee() OR profile_id = auth.uid());

-- 4. SALES AND SALE ITEMS POLICIES
DROP POLICY IF EXISTS "Admin view all sales, employee view own" ON public.sales;
CREATE POLICY "Admin view all sales, employee view own"
ON public.sales FOR SELECT
USING (public.is_admin() OR employee_id = auth.uid());

DROP POLICY IF EXISTS "Admin and employee create sales" ON public.sales;
CREATE POLICY "Admin and employee create sales"
ON public.sales FOR INSERT
WITH CHECK (public.is_admin() OR public.is_employee());

DROP POLICY IF EXISTS "Admin view all sale items, employee view own" ON public.sale_items;
CREATE POLICY "Admin view all sale items, employee view own"
ON public.sale_items FOR SELECT
USING (
    public.is_admin() OR 
    EXISTS (SELECT 1 FROM public.sales s WHERE s.id = sale_id AND s.employee_id = auth.uid())
);

-- 5. ONLINE ORDERS POLICIES
DROP POLICY IF EXISTS "Customer view own orders, admin and employee view all" ON public.online_orders;
CREATE POLICY "Customer view own orders, admin and employee view all"
ON public.online_orders FOR SELECT
USING (customer_profile_id = auth.uid() OR public.is_admin() OR public.is_employee());

DROP POLICY IF EXISTS "Customer can place online order" ON public.online_orders;
CREATE POLICY "Customer can place online order"
ON public.online_orders FOR INSERT
WITH CHECK (customer_profile_id = auth.uid() OR customer_profile_id IS NULL OR public.is_admin());

DROP POLICY IF EXISTS "Admin and employee can update order status" ON public.online_orders;
CREATE POLICY "Admin and employee can update order status"
ON public.online_orders FOR UPDATE
USING (public.is_admin() OR public.is_employee());

-- 6. SETTINGS POLICIES
DROP POLICY IF EXISTS "Anyone can read shop settings" ON public.settings;
CREATE POLICY "Anyone can read shop settings"
ON public.settings FOR SELECT
USING (TRUE);

DROP POLICY IF EXISTS "Only admin can modify shop settings" ON public.settings;
CREATE POLICY "Only admin can modify shop settings"
ON public.settings FOR ALL
USING (public.is_admin());

