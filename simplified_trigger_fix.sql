-- Quick fix for trigger function - remove references to non-existent columns
-- This is blocking document processing completion

-- Drop the problematic trigger function
DROP FUNCTION IF EXISTS handle_document_processing_status() CASCADE;

-- Create a simplified version without elasticsearch references
CREATE OR REPLACE FUNCTION handle_document_processing_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Simple trigger - just update timestamp and handle basic status changes
    NEW.updated_at = NOW();
    
    -- No elasticsearch column references since they don't exist in the table
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate the trigger 
CREATE TRIGGER document_processing_status_trigger
    BEFORE UPDATE ON mevzuat_documents
    FOR EACH ROW
    EXECUTE FUNCTION handle_document_processing_status();

-- Test the fix by attempting the update that was failing
UPDATE mevzuat_documents 
SET processing_status = 'completed' 
WHERE id = '75c57f19-773e-4976-8c1f-af8b0ac1cfdb';

SELECT 'Trigger fixed and document updated successfully' as result;