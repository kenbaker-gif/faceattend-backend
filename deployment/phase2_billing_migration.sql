-- Phase 2 Billing Tables Migration
-- Run this in Supabase SQL Editor

-- ============================================================================
-- 1. INVOICES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    institution_id TEXT NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    plan TEXT NOT NULL CHECK (plan IN ('free', 'premium', 'enterprise')),
    amount DECIMAL(10, 2) NOT NULL,
    currency TEXT DEFAULT 'KES',
    issue_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_date TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'paid', 'overdue', 'cancelled')),
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_institution ON invoices(institution_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);

-- ============================================================================
-- 2. PAYMENTS TABLE (create or enhance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id TEXT NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    amount DECIMAL(10, 2) NOT NULL,
    currency TEXT DEFAULT 'KES',
    plan TEXT,
    payment_method TEXT DEFAULT 'pesapal',
    transaction_id TEXT,
    payment_date TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'success',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add columns if table already exists (will fail silently if columns exist)
DO $$ 
BEGIN
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS plan TEXT;
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_method TEXT DEFAULT 'pesapal';
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_id TEXT;
    ALTER TABLE payments ADD COLUMN IF NOT EXISTS payment_date TIMESTAMPTZ DEFAULT NOW();
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_payments_institution ON payments(institution_id);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);

-- ============================================================================
-- 3. PLAN CHANGE HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS plan_change_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id TEXT NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    old_plan TEXT NOT NULL,
    new_plan TEXT NOT NULL,
    prorated_amount DECIMAL(10, 2),
    change_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by UUID REFERENCES auth.users(id),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_plan_changes_institution ON plan_change_history(institution_id);
CREATE INDEX idx_plan_changes_date ON plan_change_history(change_date);

-- ============================================================================
-- 4. AUTO RENEWAL SETTINGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS auto_renewal_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id TEXT UNIQUE NOT NULL REFERENCES institutions(id) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT FALSE,
    plan TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    next_renewal_date TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_auto_renewal_institution ON auto_renewal_settings(institution_id);
CREATE INDEX idx_auto_renewal_next_date ON auto_renewal_settings(next_renewal_date);

-- ============================================================================
-- 5. GRACE PERIOD TRACKING
-- ============================================================================
ALTER TABLE institutions 
ADD COLUMN IF NOT EXISTS grace_period_start TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS grace_period_end TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'free',
ADD COLUMN IF NOT EXISTS subscription_end TIMESTAMPTZ;

-- ============================================================================
-- 6. RLS POLICIES
-- ============================================================================

-- Invoices RLS
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Institutions can view own invoices"
ON invoices FOR SELECT
USING (
    institution_id IN (
        SELECT institution_id FROM profiles WHERE id = auth.uid()
    )
);

-- Plan change history RLS
ALTER TABLE plan_change_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Institutions can view own plan changes"
ON plan_change_history FOR SELECT
USING (
    institution_id IN (
        SELECT institution_id FROM profiles WHERE id = auth.uid()
    )
);

-- Auto renewal settings RLS
ALTER TABLE auto_renewal_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Institutions can manage own auto renewal"
ON auto_renewal_settings FOR ALL
USING (
    institution_id IN (
        SELECT institution_id FROM profiles WHERE id = auth.uid()
    )
);

-- ============================================================================
-- 7. FUNCTIONS FOR AUTOMATED TASKS
-- ============================================================================

-- Function to mark overdue invoices
CREATE OR REPLACE FUNCTION mark_overdue_invoices()
RETURNS void AS $$
BEGIN
    UPDATE invoices
    SET status = 'overdue', updated_at = NOW()
    WHERE status = 'pending' AND due_date < NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to process auto renewals
CREATE OR REPLACE FUNCTION process_auto_renewals()
RETURNS TABLE(institution_id TEXT, plan TEXT, amount DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT ar.institution_id, ar.plan, 
           CASE ar.plan
               WHEN 'premium' THEN 5000
               WHEN 'enterprise' THEN 15000
               ELSE 0
           END::DECIMAL as amount
    FROM auto_renewal_settings ar
    WHERE ar.enabled = TRUE 
      AND ar.next_renewal_date <= NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check tables created
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('invoices', 'plan_change_history', 'auto_renewal_settings')
ORDER BY table_name;

-- Check new columns added
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'institutions' 
  AND column_name IN ('grace_period_start', 'grace_period_end');

SELECT column_name FROM information_schema.columns 
WHERE table_name = 'payments' 
  AND column_name IN ('plan', 'payment_method', 'transaction_id', 'payment_date');
