-- Supabase Simple Vector Reset - Permission-Safe Approach
-- This avoids functions requiring superuser permissions

-- Step 1: Drop existing table and indexes
DROP TABLE IF EXISTS mevzuat_embeddings CASCADE;

-- Step 2: Create fresh table with exact vector(1536) specification
CREATE TABLE mevzuat_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- Exactly 1536 dimensions
    chunk_index INTEGER DEFAULT 0,
    
    -- Source tracking
    page_number INTEGER,
    line_start INTEGER,
    line_end INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Add explicit dimension constraint
ALTER TABLE mevzuat_embeddings 
ADD CONSTRAINT embedding_dimension_check 
CHECK (array_length(embedding::float4[], 1) = 1536);

-- Step 4: Create performance indexes
CREATE INDEX idx_embeddings_document_id ON mevzuat_embeddings(document_id);
CREATE INDEX idx_embeddings_chunk_index ON mevzuat_embeddings(chunk_index);
CREATE INDEX idx_embeddings_page_number ON mevzuat_embeddings(page_number);
CREATE INDEX idx_embeddings_created_at ON mevzuat_embeddings(created_at);

-- Step 5: Create vector similarity index (using IVFFlat for stability)
CREATE INDEX idx_embeddings_vector_ivfflat ON mevzuat_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

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

CREATE POLICY "Service can manage embeddings" ON mevzuat_embeddings
    FOR ALL USING (true) WITH CHECK (true);

-- Step 8: Grant permissions
GRANT ALL ON mevzuat_embeddings TO service_role;

-- Step 9: Create updated_at trigger
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

-- Step 10: Test table functionality
-- Insert a test vector and verify dimensions
INSERT INTO mevzuat_embeddings (document_id, content, embedding)
VALUES (
    '5a9c6a02-5b9a-43d4-b01a-65d6d82f2d67',
    'Test vector for dimension verification',
    array_fill(0.5, ARRAY[1536])::vector(1536)
);

-- Step 11: Verify the test vector
SELECT 
    id,
    content,
    array_length(embedding::float4[], 1) as vector_dimension,
    created_at
FROM mevzuat_embeddings 
WHERE content = 'Test vector for dimension verification';

-- Step 12: Clean up test vector
DELETE FROM mevzuat_embeddings 
WHERE content = 'Test vector for dimension verification';

-- Step 13: Reset document status for fresh processing
UPDATE mevzuat_documents 
SET status = 'processing' 
WHERE id = '5a9c6a02-5b9a-43d4-b01a-65d6d82f2d67';

-- Step 14: Verification queries
SELECT 
    table_name,
    column_name,
    data_type,
    character_maximum_length as max_length
FROM information_schema.columns 
WHERE table_name = 'mevzuat_embeddings' 
AND column_name = 'embedding';

-- Step 15: Check constraints
SELECT 
    constraint_name,
    constraint_type,
    check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc 
    ON tc.constraint_name = cc.constraint_name
WHERE tc.table_name = 'mevzuat_embeddings';

-- Success message
SELECT 'Simple vector reset completed - Table ready for 1536-dimensional embeddings' as result;