-- ============================================================================
-- MevzuatGPT Auth Status Summary
-- ============================================================================
-- Final verification of auth system setup
-- ============================================================================

-- Check complete auth integration
SELECT 
    'Auth Integration Status' as status_check,
    au.id as auth_user_id,
    au.email,
    au.email_confirmed_at IS NOT NULL as email_confirmed,
    au.raw_app_meta_data,
    au.raw_user_meta_data,
    up.id as profile_id,
    up.role as profile_role,
    up.credits,
    up.is_active,
    up.email_verified
FROM auth.users au
LEFT JOIN user_profiles up ON au.id = up.user_id
WHERE au.email = 'admin@mevzuatgpt.com';

-- Verify role-based access
SELECT 
    'Role Verification' as check_type,
    COUNT(*) FILTER (WHERE role = 'admin') as admin_count,
    COUNT(*) FILTER (WHERE role = 'user') as user_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    COUNT(*) as total_profiles
FROM user_profiles;

-- Check auth schema completeness
SELECT 
    'Schema Status' as info,
    (SELECT COUNT(*) FROM auth.users) as auth_users,
    (SELECT COUNT(*) FROM user_profiles) as user_profiles,
    (SELECT COUNT(*) FROM documents) as documents,
    (SELECT COUNT(*) FROM search_history) as search_history;

COMMIT;