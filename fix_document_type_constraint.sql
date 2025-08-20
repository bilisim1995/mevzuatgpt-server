-- Fix document_type check constraint to allow 'mevzuat' value
-- Current constraint is rejecting 'mevzuat' category

-- First, check current constraint
SELECT conname, pg_get_constraintdef(oid) as constraint_definition
FROM pg_constraint 
WHERE conrelid = 'mevzuat_documents'::regclass 
AND contype = 'c'
AND conname LIKE '%document_type%';

-- Drop the restrictive check constraint
ALTER TABLE public.mevzuat_documents 
DROP CONSTRAINT IF EXISTS documents_document_type_check;

-- Add a new more permissive constraint that allows common document types
ALTER TABLE public.mevzuat_documents 
ADD CONSTRAINT documents_document_type_check 
CHECK (document_type IN (
    'kanun',
    'yönetmelik', 
    'tebliğ',
    'genelge',
    'mevzuat',
    'karar',
    'tüzük',
    'yönerge',
    'sirküler',
    'rehber',
    'kılavuz',
    'standart',
    'form',
    'belge',
    'Genel'
) OR document_type IS NULL);

-- Update any existing records that might be causing issues
UPDATE public.mevzuat_documents 
SET document_type = 'mevzuat' 
WHERE document_type NOT IN (
    'kanun', 'yönetmelik', 'tebliğ', 'genelge', 'mevzuat', 
    'karar', 'tüzük', 'yönerge', 'sirküler', 'rehber', 
    'kılavuz', 'standart', 'form', 'belge', 'Genel'
) AND document_type IS NOT NULL;

-- Verify the fix
SELECT document_type, COUNT(*) as count 
FROM public.mevzuat_documents 
GROUP BY document_type 
ORDER BY count DESC;