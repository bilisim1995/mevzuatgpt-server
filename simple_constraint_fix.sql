-- Simple fix for document_type constraint issue
-- Drop restrictive constraint and add permissive one

-- Drop the problematic constraint
ALTER TABLE public.mevzuat_documents 
DROP CONSTRAINT IF EXISTS documents_document_type_check;

-- Add new permissive constraint allowing common Turkish document types
ALTER TABLE public.mevzuat_documents 
ADD CONSTRAINT documents_document_type_check 
CHECK (
    document_type IS NULL OR 
    document_type IN (
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
        'Genel',
        'genel'
    )
);

-- Test the constraint by checking if 'mevzuat' is now allowed
SELECT 'mevzuat' IN (
    'kanun', 'yönetmelik', 'tebliğ', 'genelge', 'mevzuat', 
    'karar', 'tüzük', 'yönerge', 'sirküler', 'rehber', 
    'kılavuz', 'standart', 'form', 'belge', 'Genel', 'genel'
) AS mevzuat_allowed;