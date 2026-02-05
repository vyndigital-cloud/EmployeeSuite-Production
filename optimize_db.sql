-- Migration to add missing columns to production database
-- Run this against your Render PostgreSQL database

-- 1. Add trial_used_at specifically (The error source)
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_used_at TIMESTAMP;

-- 2. Add other potential missing columns for future safety
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_subscribed BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_email_hash VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_ip_hash VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_browser_fingerprint VARCHAR(64);

-- 3. ensure basic indices exist
CREATE INDEX IF NOT EXISTS idx_user_subscription ON users(is_subscribed, trial_ends_at);
