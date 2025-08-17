-- ============================================================================
-- Supabase Auth Configuration Fix
-- ============================================================================
-- Enable email authentication and configure settings
-- Run this in Supabase SQL Editor or directly in PostgreSQL
-- ============================================================================

-- Check current auth configuration
SELECT 
    'Current Auth Config' as info,
    id,
    raw_app_meta_data,
    raw_user_meta_data,
    email_confirmed_at IS NOT NULL as email_confirmed,
    is_super_admin
FROM auth.users 
WHERE email = 'admin@mevzuatgpt.com';

-- Update auth user to ensure proper configuration
UPDATE auth.users 
SET 
    email_confirmed_at = COALESCE(email_confirmed_at, NOW()),
    confirmed_at = COALESCE(confirmed_at, NOW()),
    raw_app_meta_data = COALESCE(raw_app_meta_data, '{}')::jsonb || '{"provider":"email","providers":["email"]}'::jsonb,
    raw_user_meta_data = COALESCE(raw_user_meta_data, '{}')::jsonb || '{"email_verified":true,"email":"admin@mevzuatgpt.com"}'::jsonb
WHERE email = 'admin@mevzuatgpt.com';

-- Verify the updates
SELECT 
    'Updated Auth Config' as info,
    id,
    email,
    email_confirmed_at,
    confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data
FROM auth.users 
WHERE email = 'admin@mevzuatgpt.com';

-- Check if auth.config table exists and update email settings
DO $$
BEGIN
    -- Try to enable email authentication in auth config if table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'config') THEN
        -- Enable email auth
        INSERT INTO auth.config (parameter, value) 
        VALUES ('auth.email.enable_signup', 'true')
        ON CONFLICT (parameter) DO UPDATE SET value = 'true';
        
        INSERT INTO auth.config (parameter, value) 
        VALUES ('auth.email.enable_signin', 'true')
        ON CONFLICT (parameter) DO UPDATE SET value = 'true';
        
        RAISE NOTICE 'Email authentication enabled in auth.config';
    ELSE
        RAISE NOTICE 'auth.config table not found - configuration must be done via environment variables';
    END IF;
END $$;

-- Create a function to generate a fresh JWT token for admin user
CREATE OR REPLACE FUNCTION generate_admin_token(user_uuid UUID)
RETURNS TEXT AS $$
DECLARE
    header JSONB;
    payload JSONB;
    secret TEXT;
BEGIN
    -- This is a simplified token structure for testing
    -- In production, use proper JWT libraries
    header := '{"alg":"HS256","typ":"JWT"}';
    payload := jsonb_build_object(
        'aud', 'authenticated',
        'exp', extract(epoch from now() + interval '1 hour'),
        'iat', extract(epoch from now()),
        'iss', 'supabase',
        'sub', user_uuid,
        'email', 'admin@mevzuatgpt.com',
        'role', 'authenticated',
        'app_metadata', '{"provider":"email","providers":["email"]}',
        'user_metadata', '{"email":"admin@mevzuatgpt.com"}'
    );
    
    RETURN 'Token generation requires JWT signing - use Supabase client libraries';
END;
$$ LANGUAGE plpgsql;

-- Show summary
SELECT 
    'Auth Setup Summary' as section,
    COUNT(*) as total_users,
    COUNT(*) FILTER (WHERE email_confirmed_at IS NOT NULL) as confirmed_users,
    COUNT(*) FILTER (WHERE is_super_admin = true) as super_admins
FROM auth.users;

-- Show user_profiles integration
SELECT 
    'User Profiles Summary' as section,
    COUNT(*) as total_profiles,
    COUNT(*) FILTER (WHERE role = 'admin') as admin_profiles,
    COUNT(*) FILTER (WHERE is_active = true) as active_profiles
FROM user_profiles;

COMMIT;