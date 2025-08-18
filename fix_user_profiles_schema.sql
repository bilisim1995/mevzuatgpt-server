-- ============================================================================
-- Fix user_profiles table schema for registration
-- ============================================================================

-- Check current user_profiles structure
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'user_profiles' 
AND table_schema = 'public'
ORDER BY ordinal_position;

-- Add missing preferences column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_profiles' 
        AND column_name = 'preferences' 
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE user_profiles ADD COLUMN preferences JSONB DEFAULT '{}';
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'user_profiles' 
AND table_schema = 'public'
ORDER BY ordinal_position;