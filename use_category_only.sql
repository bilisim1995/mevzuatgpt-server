-- Use only category column, remove document_type constraints and standardize
-- This eliminates the confusion between document_type and category

-- Remove document_type constraint (if exists)
ALTER TABLE public.mevzuat_documents 
DROP CONSTRAINT IF EXISTS documents_document_type_check;

-- Copy existing document_type values to category column if needed
UPDATE public.mevzuat_documents 
SET category = document_type 
WHERE category IS NULL AND document_type IS NOT NULL;

-- Optional: Drop document_type column entirely to avoid confusion
-- ALTER TABLE public.mevzuat_documents DROP COLUMN IF EXISTS document_type;

-- Verify data
SELECT 
    category,
    document_type,
    COUNT(*) as count
FROM public.mevzuat_documents 
GROUP BY category, document_type 
ORDER BY count DESC;

-- Show final result
SELECT 'Category column will be used for document classification' as result;