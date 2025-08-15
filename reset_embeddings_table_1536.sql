-- MevzuatGPT Embedding Table Reset - Full Reconstruction for 1536 dimensions
-- This will completely drop and recreate the table with proper vector(1536) configuration

-- Step 1: Drop existing table and all related objects
DROP TABLE IF EXISTS mevzuat_embeddings CASCADE;
DROP INDEX IF EXISTS idx_embeddings_vector_hnsw;
DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat;
DROP INDEX IF EXISTS idx_embeddings_document_id;
DROP INDEX IF EXISTS idx_embeddings_chunk_index;
DROP INDEX IF EXISTS idx_embeddings_page_number;
DROP INDEX IF EXISTS idx_embeddings_created_at;

-- Step 2: Ensure pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 3: Create fresh embeddings table with exact 1536 dimensions
CREATE TABLE mevzuat_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- Exactly 1536 dimensions for text-embedding-3-small
    chunk_index INTEGER DEFAULT 0,
    
    -- Source tracking columns
    page_number INTEGER,
    line_start INTEGER,
    line_end INTEGER,
    
    -- Metadata and timestamps
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 4: Create performance indexes
CREATE INDEX idx_embeddings_document_id ON mevzuat_embeddings(document_id);
CREATE INDEX idx_embeddings_chunk_index ON mevzuat_embeddings(chunk_index);
CREATE INDEX idx_embeddings_page_number ON mevzuat_embeddings(page_number);
CREATE INDEX idx_embeddings_created_at ON mevzuat_embeddings(created_at);

-- Step 5: Create vector similarity index with optimal settings for 1536 dimensions
-- Using HNSW index which is best for 1536 dimensions
CREATE INDEX idx_embeddings_vector_hnsw ON mevzuat_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Step 6: Enable Row Level Security
ALTER TABLE mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- Step 7: Create RLS policies
CREATE POLICY "Users can read embeddings" ON mevzuat_embeddings
    FOR SELECT USING (
        document_id IN (
            SELECT id FROM mevzuat_documents 
            WHERE uploaded_by = auth.uid()
            OR EXISTS (
                SELECT 1 FROM auth.users 
                WHERE id = auth.uid() 
                AND raw_user_meta_data->>'role' = 'admin'
            )
        )
    );

CREATE POLICY "Service can insert embeddings" ON mevzuat_embeddings
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Service can update embeddings" ON mevzuat_embeddings
    FOR UPDATE USING (true);

CREATE POLICY "Service can delete embeddings" ON mevzuat_embeddings
    FOR DELETE USING (true);

-- Step 8: Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_embeddings_updated_at 
    BEFORE UPDATE ON mevzuat_embeddings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Step 9: Grant permissions to service role
GRANT ALL ON mevzuat_embeddings TO service_role;

-- Step 10: Add helpful comments
COMMENT ON TABLE mevzuat_embeddings IS 'Document embeddings table using text-embedding-3-small (1536 dimensions)';
COMMENT ON COLUMN mevzuat_embeddings.embedding IS 'Vector embedding with exactly 1536 dimensions';
COMMENT ON INDEX idx_embeddings_vector_hnsw IS 'HNSW index optimized for 1536-dimensional cosine similarity search';

-- Step 11: Verify table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'mevzuat_embeddings' 
ORDER BY ordinal_position;

-- Step 12: Check vector column dimension constraint
SELECT 
    atttypmod 
FROM pg_attribute 
WHERE attrelid = 'mevzuat_embeddings'::regclass 
AND attname = 'embedding';

-- Expected result: atttypmod should be 1540 (1536 + 4 for pgvector internal structure)

-- Step 13: Reset document status for fresh processing
UPDATE mevzuat_documents 
SET status = 'processing' 
WHERE id = '5a9c6a02-5b9a-43d4-b01a-65d6d82f2d67';

-- Success message
SELECT 'Embeddings table successfully reset for 1536 dimensions' as result;