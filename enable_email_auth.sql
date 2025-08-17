-- ============================================================================
-- Supabase Self-hosted Email Authentication Enabler
-- ============================================================================
-- This script enables email authentication on self-hosted Supabase instance
-- Run this in your Supabase SQL Editor or directly in PostgreSQL
-- ============================================================================

-- 1. Check current auth configuration
SELECT 
    'Current Auth Settings' as check_type,
    schemaname,
    tablename
FROM pg_tables 
WHERE schemaname = 'auth' 
ORDER BY tablename;

-- 2. Enable email authentication in auth config
-- Insert or update auth configuration settings
DO $$
BEGIN
    -- Create auth.config table if it doesn't exist
    IF NOT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'auth' AND table_name = 'config'
    ) THEN
        CREATE TABLE IF NOT EXISTS auth.config (
            parameter TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        RAISE NOTICE 'Created auth.config table';
    END IF;

    -- Enable email signup
    INSERT INTO auth.config (parameter, value) 
    VALUES ('GOTRUE_DISABLE_SIGNUP', 'false')
    ON CONFLICT (parameter) DO UPDATE SET value = 'false';

    -- Enable email signin
    INSERT INTO auth.config (parameter, value) 
    VALUES ('GOTRUE_ENABLE_SIGNUP', 'true')
    ON CONFLICT (parameter) DO UPDATE SET value = 'true';

    -- Set email confirmation requirement (optional - set to false for testing)
    INSERT INTO auth.config (parameter, value) 
    VALUES ('GOTRUE_MAILER_AUTOCONFIRM', 'true')
    ON CONFLICT (parameter) DO UPDATE SET value = 'true';

    -- Enable email provider
    INSERT INTO auth.config (parameter, value) 
    VALUES ('GOTRUE_EXTERNAL_EMAIL_ENABLED', 'true')
    ON CONFLICT (parameter) DO UPDATE SET value = 'true';

    RAISE NOTICE 'Email authentication settings updated';
END $$;

-- 3. Update existing admin user to ensure it's properly configured
UPDATE auth.users 
SET 
    email_confirmed_at = COALESCE(email_confirmed_at, NOW()),
    raw_app_meta_data = COALESCE(raw_app_meta_data, '{}')::jsonb || '{"provider":"email","providers":["email"]}'::jsonb,
    raw_user_meta_data = COALESCE(raw_user_meta_data, '{}')::jsonb || '{"email_verified":true}'::jsonb
WHERE email = 'admin@mevzuatgpt.com';

-- 4. Check if instance configuration table exists and update
DO $$
BEGIN
    -- Try to update instance config if table exists
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'extensions' AND table_name = 'supabase_settings'
    ) THEN
        UPDATE extensions.supabase_settings 
        SET value = 'false' 
        WHERE name = 'disable_signup';
        
        RAISE NOTICE 'Updated instance settings';
    ELSE
        RAISE NOTICE 'Instance settings table not found - use environment variables';
    END IF;
END $$;

-- 5. Environment Variables Guide (for Docker Compose or .env file)
SELECT '-- ============================================================================' as guide
UNION ALL
SELECT '-- Environment Variables to Add to Your Supabase Self-hosted Setup:'
UNION ALL
SELECT '-- ============================================================================'
UNION ALL
SELECT '-- In your docker-compose.yml or .env file, add these variables:'
UNION ALL
SELECT '--'
UNION ALL
SELECT '-- GOTRUE_DISABLE_SIGNUP=false'
UNION ALL
SELECT '-- GOTRUE_ENABLE_SIGNUP=true'
UNION ALL
SELECT '-- GOTRUE_MAILER_AUTOCONFIRM=true'
UNION ALL
SELECT '-- GOTRUE_EXTERNAL_EMAIL_ENABLED=true'
UNION ALL
SELECT '-- GOTRUE_SMTP_HOST=your-smtp-host'
UNION ALL
SELECT '-- GOTRUE_SMTP_PORT=587'
UNION ALL
SELECT '-- GOTRUE_SMTP_USER=your-smtp-user'
UNION ALL
SELECT '-- GOTRUE_SMTP_PASS=your-smtp-password'
UNION ALL
SELECT '-- GOTRUE_SMTP_ADMIN_EMAIL=admin@mevzuatgpt.com'
UNION ALL
SELECT '--'
UNION ALL
SELECT '-- After adding these variables, restart your Supabase containers:'
UNION ALL
SELECT '-- docker-compose down && docker-compose up -d';

-- 6. Verify configuration
SELECT 
    'Auth Configuration Status' as status,
    parameter,
    value
FROM auth.config 
WHERE parameter LIKE '%SIGNUP%' 
   OR parameter LIKE '%EMAIL%'
   OR parameter LIKE '%MAILER%'
ORDER BY parameter;

-- 7. Verify admin user status
SELECT 
    'Admin User Status' as check_type,
    email,
    email_confirmed_at IS NOT NULL as email_confirmed,
    raw_app_meta_data->'provider' as auth_provider,
    raw_user_meta_data->'email_verified' as email_verified
FROM auth.users 
WHERE email = 'admin@mevzuatgpt.com';

-- 8. Test authentication readiness
SELECT 
    'Authentication Test Readiness' as test_type,
    CASE 
        WHEN email_confirmed_at IS NOT NULL 
         AND encrypted_password IS NOT NULL 
         AND length(encrypted_password) > 10
        THEN 'READY FOR LOGIN'
        ELSE 'NOT READY - Missing password or confirmation'
    END as status
FROM auth.users 
WHERE email = 'admin@mevzuatgpt.com';

COMMIT;