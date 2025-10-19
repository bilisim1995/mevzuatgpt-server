-- SQL Migration: Add belge_adi column to mevzuat_documents table
-- This column will store the document name/title in addition to existing fields

-- Add belge_adi column to mevzuat_documents table
ALTER TABLE mevzuat_documents 
ADD COLUMN IF NOT EXISTS belge_adi TEXT;

-- Add comment to explain the column
COMMENT ON COLUMN mevzuat_documents.belge_adi IS 'Belge adı - Document name field for additional identification';

-- For existing records, set belge_adi to NULL (will be filled later)
-- New records will include this field from the upload endpoint

-- Optional: Create index for faster searches on belge_adi
CREATE INDEX IF NOT EXISTS idx_mevzuat_documents_belge_adi ON mevzuat_documents(belge_adi);

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'mevzuat_documents' 
AND column_name = 'belge_adi';
