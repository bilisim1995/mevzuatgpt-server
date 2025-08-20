-- Quick fix for status constraint - allow 'completed' status
ALTER TABLE public.mevzuat_documents 
DROP CONSTRAINT IF EXISTS documents_status_check;

ALTER TABLE public.mevzuat_documents 
ADD CONSTRAINT documents_status_check 
CHECK (status IN ('active', 'archived', 'deleted', 'processing', 'completed', 'failed', 'inactive', 'pending'));

-- Verify fix
SELECT 'Status constraint now allows: active, archived, deleted, processing, completed, failed, inactive, pending' as result;