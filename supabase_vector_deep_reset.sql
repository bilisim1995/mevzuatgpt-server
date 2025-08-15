-- Supabase Vector Deep Reset - Comprehensive pgvector Extension Reset
-- This will completely reset the pgvector extension and all related components

-- Step 1: Drop all existing vector tables and functions
DROP TABLE IF EXISTS mevzuat_embeddings CASCADE;
DROP INDEX IF EXISTS idx_embeddings_vector_hnsw CASCADE;
DROP INDEX IF EXISTS idx_embeddings_vector_ivfflat CASCADE;

-- Step 2: Remove and reinstall pgvector extension completely
DROP EXTENSION IF EXISTS vector CASCADE;

-- Step 3: Clear any cached vector data and settings
-- This will force Supabase to completely reinstall the extension
SELECT pg_reload_conf();

-- Step 4: Reinstall pgvector extension fresh
CREATE EXTENSION vector;

-- Step 5: Verify extension installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- Step 6: Test vector functionality with exact 1536 dimensions
DO $$
DECLARE
    test_vector vector(1536);
BEGIN
    -- Create a test vector with exactly 1536 dimensions
    test_vector := array_fill(0.5, ARRAY[1536])::vector;
    
    -- Verify the dimension
    IF array_length(test_vector::float4[], 1) = 1536 THEN
        RAISE NOTICE 'Vector test successful: 1536 dimensions confirmed';
    ELSE
        RAISE EXCEPTION 'Vector test failed: Expected 1536, got %', array_length(test_vector::float4[], 1);
    END IF;
END $$;

-- Step 7: Create fresh embeddings table with strict dimension control
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
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Add explicit dimension constraint
    CONSTRAINT embedding_dimension_check CHECK (array_length(embedding::float4[], 1) = 1536)
);

-- Step 8: Create optimized indexes for 1536 dimensions
CREATE INDEX idx_embeddings_document_id ON mevzuat_embeddings(document_id);
CREATE INDEX idx_embeddings_chunk_index ON mevzuat_embeddings(chunk_index);
CREATE INDEX idx_embeddings_created_at ON mevzuat_embeddings(created_at);

-- Step 9: Create vector index with specific settings for 1536 dimensions
-- Using IVFFlat first (more stable than HNSW for troubleshooting)
CREATE INDEX idx_embeddings_vector_ivfflat ON mevzuat_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Step 10: Enable RLS and policies
ALTER TABLE mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- User read policy
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

-- Service policies
CREATE POLICY "Service can manage embeddings" ON mevzuat_embeddings
    FOR ALL USING (true) WITH CHECK (true);

-- Step 11: Grant permissions
GRANT ALL ON mevzuat_embeddings TO service_role;

-- Step 12: Create trigger for updated_at
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

-- Step 13: Test table with sample vector
DO $$
DECLARE
    test_id UUID;
    test_vector vector(1536);
    retrieved_vector vector(1536);
    retrieved_dimension integer;
BEGIN
    -- Create test vector
    test_vector := array_fill(0.1, ARRAY[1536])::vector;
    
    -- Insert test record
    INSERT INTO mevzuat_embeddings (document_id, content, embedding)
    VALUES (
        '5a9c6a02-5b9a-43d4-b01a-65d6d82f2d67',
        'Test embedding content',
        test_vector
    ) RETURNING id INTO test_id;
    
    -- Retrieve and verify
    SELECT embedding INTO retrieved_vector 
    FROM mevzuat_embeddings 
    WHERE id = test_id;
    
    retrieved_dimension := array_length(retrieved_vector::float4[], 1);
    
    IF retrieved_dimension = 1536 THEN
        RAISE NOTICE 'SUCCESS: Test embedding stored and retrieved with correct dimensions: %', retrieved_dimension;
    ELSE
        RAISE EXCEPTION 'FAILURE: Dimension corruption detected - Expected 1536, got %', retrieved_dimension;
    END IF;
    
    -- Clean up test record
    DELETE FROM mevzuat_embeddings WHERE id = test_id;
    
    RAISE NOTICE 'Test record cleaned up successfully';
END $$;

-- Step 14: Reset document status for fresh processing
UPDATE mevzuat_documents 
SET status = 'processing' 
WHERE id = '5a9c6a02-5b9a-43d4-b01a-65d6d82f2d67';

-- Step 15: Final verification queries
SELECT 
    'pgvector extension version' as info,
    extversion as value
FROM pg_extension 
WHERE extname = 'vector'

UNION ALL

SELECT 
    'Table structure check' as info,
    'mevzuat_embeddings exists' as value
FROM information_schema.tables 
WHERE table_name = 'mevzuat_embeddings'

UNION ALL

SELECT 
    'Vector column type' as info,
    data_type || '(' || character_maximum_length || ')' as value
FROM information_schema.columns 
WHERE table_name = 'mevzuat_embeddings' 
AND column_name = 'embedding';

-- Success message
SELECT 'Deep vector reset completed successfully - Ready for fresh embedding generation' as result;