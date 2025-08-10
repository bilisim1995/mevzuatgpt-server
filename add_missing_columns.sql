-- Add missing columns to mevzuat_documents table
ALTER TABLE public.mevzuat_documents 
ADD COLUMN IF NOT EXISTS source_institution VARCHAR(200),
ADD COLUMN IF NOT EXISTS category VARCHAR(100),
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS keywords TEXT[],
ADD COLUMN IF NOT EXISTS publish_date TIMESTAMPTZ;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_source_institution ON public.mevzuat_documents(source_institution);
CREATE INDEX IF NOT EXISTS idx_category ON public.mevzuat_documents(category);
CREATE INDEX IF NOT EXISTS idx_publish_date ON public.mevzuat_documents(publish_date);

-- Update existing documents with sample data
UPDATE public.mevzuat_documents SET 
    source_institution = 'Sosyal Güvenlik Kurumu',
    category = 'Sigortalılık',
    description = 'Mevzuat belgesi'
WHERE source_institution IS NULL;
