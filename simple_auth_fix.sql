-- ============================================================================
-- Simple Supabase Email Authentication SQL Fix
-- ============================================================================
-- Copy and paste these commands one by one in Supabase SQL Editor
-- ============================================================================

-- 1. Create auth config table
CREATE TABLE IF NOT EXISTS auth.config (
    parameter TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 2. Enable email authentication settings
INSERT INTO auth.config (parameter, value) VALUES ('GOTRUE_DISABLE_SIGNUP', 'false') 
ON CONFLICT (parameter) DO UPDATE SET value = 'false';

INSERT INTO auth.config (parameter, value) VALUES ('GOTRUE_ENABLE_SIGNUP', 'true') 
ON CONFLICT (parameter) DO UPDATE SET value = 'true';

INSERT INTO auth.config (parameter, value) VALUES ('GOTRUE_MAILER_AUTOCONFIRM', 'true') 
ON CONFLICT (parameter) DO UPDATE SET value = 'true';

INSERT INTO auth.config (parameter, value) VALUES ('GOTRUE_EXTERNAL_EMAIL_ENABLED', 'true') 
ON CONFLICT (parameter) DO UPDATE SET value = 'true';

-- 3. Verify settings
SELECT parameter, value FROM auth.config ORDER BY parameter;