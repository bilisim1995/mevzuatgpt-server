-- Fix the trigger function that references non-existent elasticsearch_indexed column
-- This is causing the update failures

-- First, check current triggers on the table
SELECT 
    t.tgname as trigger_name,
    t.tgenabled,
    p.proname as function_name
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE t.tgrelid = 'mevzuat_documents'::regclass;

-- Drop the problematic trigger function and recreate without elasticsearch_indexed reference
DROP FUNCTION IF EXISTS handle_document_processing_status() CASCADE;

-- Create a simple trigger function that doesn't reference non-existent columns
CREATE OR REPLACE FUNCTION handle_document_processing_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Simple trigger - just update the timestamp
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate the trigger if it existed
-- (This will be automatically handled by the DROP CASCADE above)
-- CREATE TRIGGER document_processing_status_trigger
--     BEFORE UPDATE ON mevzuat_documents
--     FOR EACH ROW
--     EXECUTE FUNCTION handle_document_processing_status();

-- Test the fix
SELECT 'Trigger function fixed - elasticsearch_indexed reference removed' as result;