-- Add missing category column to mevzuat_documents table
-- This will fix the Supabase schema cache error

-- Check if column exists first
DO $$ 
BEGIN 
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'mevzuat_documents' 
        AND column_name = 'category'
    ) THEN
        -- Add category column
        ALTER TABLE public.mevzuat_documents 
        ADD COLUMN category TEXT;
        
        -- Add index for better performance
        CREATE INDEX IF NOT EXISTS idx_mevzuat_documents_category 
        ON public.mevzuat_documents(category);
        
        -- Add comment
        COMMENT ON COLUMN public.mevzuat_documents.category 
        IS 'Document category for classification';
        
        RAISE NOTICE 'Category column added successfully';
    ELSE
        RAISE NOTICE 'Category column already exists';
    END IF;
END $$;

-- Update existing documents to have default category
UPDATE public.mevzuat_documents 
SET category = 'Genel' 
WHERE category IS NULL;

-- Optional: Add constraint to ensure category is not empty
-- ALTER TABLE public.mevzuat_documents 
-- ADD CONSTRAINT check_category_not_empty 
-- CHECK (category IS NOT NULL AND category != '');

-- Grant necessary permissions (if needed)
-- GRANT SELECT, INSERT, UPDATE ON public.mevzuat_documents TO authenticated;
-- GRANT SELECT, INSERT, UPDATE ON public.mevzuat_documents TO anon;