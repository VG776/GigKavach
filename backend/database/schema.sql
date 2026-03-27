-- database/schema.sql
-- Run this in your Supabase SQL Editor to create the necessary tables for GigKavach

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1. WORKERS TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS workers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    phone_number VARCHAR(20),
    upi_id VARCHAR(100),
    pin_codes TEXT[] DEFAULT ARRAY[]::TEXT[],
    shift VARCHAR(50),
    shift_start TIME,
    shift_end TIME,
    language VARCHAR(50) DEFAULT 'English',
    plan VARCHAR(50) DEFAULT 'Shield Basic',
    coverage_pct INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_workers_is_active ON workers (is_active);
CREATE INDEX idx_workers_created_at ON workers (created_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2. POLICIES TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    plan VARCHAR(50) DEFAULT 'Shield Basic',
    status VARCHAR(50) DEFAULT 'active',
    week_start DATE NOT NULL,
    coverage_pct INTEGER DEFAULT 0,
    weekly_premium INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_policies_worker_id ON policies (worker_id);
CREATE INDEX idx_policies_week_start ON policies (week_start DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3. PAYOUTS TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    base_amount INTEGER DEFAULT 0,
    surge_multiplier DECIMAL(5, 2) DEFAULT 1.0,
    final_amount INTEGER DEFAULT 0,
    fraud_score DECIMAL(5, 2) DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_payouts_worker_id ON payouts (worker_id);
CREATE INDEX idx_payouts_triggered_at ON payouts (triggered_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4. ACTIVITIES TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    description TEXT,
    date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_activities_worker_id ON activities (worker_id);
CREATE INDEX idx_activities_date ON activities (date DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 5. ACTIVITY_LOG TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    log_date TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    first_login_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    active_hours INTEGER DEFAULT 0,
    orders_completed INTEGER DEFAULT 0,
    estimated_earnings INTEGER DEFAULT 0,
    zone_pin_codes TEXT[] DEFAULT ARRAY[]::TEXT[],
    platform_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_activity_log_worker_id ON activity_log (worker_id);
CREATE INDEX idx_activity_log_date ON activity_log (log_date DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 6. ACTIVITY_HISTORY TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS activity_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    history_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_activity_history_worker_id ON activity_history (worker_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 7. DCI_LOGS TABLE: Tracks every 5-min calculation for active zones
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS dci_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pincode VARCHAR(20) NOT NULL,
    total_score INTEGER NOT NULL,
    rainfall_score INTEGER NOT NULL DEFAULT 0,
    aqi_score INTEGER NOT NULL DEFAULT 0,
    heat_score INTEGER NOT NULL DEFAULT 0,
    social_score INTEGER NOT NULL DEFAULT 0,
    platform_score INTEGER NOT NULL DEFAULT 0,
    severity_tier VARCHAR(50) NOT NULL,
    is_shift_window_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

CREATE INDEX idx_dci_logs_pincode_time ON dci_logs (pincode, created_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- 8. FRAUD_FLAGS TABLE
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS fraud_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    worker_id UUID NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    flag_type VARCHAR(100),
    severity VARCHAR(50),
    message TEXT,
    is_resolved BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_fraud_flags_worker_id ON fraud_flags (worker_id);

-- Enable Row Level Security (RLS)
ALTER TABLE dci_logs ENABLE ROW LEVEL SECURITY;
