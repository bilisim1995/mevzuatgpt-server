-- MevzuatGPT Embedding Table Setup for 1536 dimensions
-- Compatible with text-embedding-3-small model

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create or replace the embeddings table with 1536 dimensions
DROP TABLE IF EXISTS mevzuat_embeddings CASCADE;

CREATE TABLE mevzuat_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- text-embedding-3-small dimension
    chunk_index INTEGER DEFAULT 0,
    
    -- Enhanced source tracking columns
    page_number INTEGER,
    line_start INTEGER,
    line_end INTEGER,
    
    -- Metadata and timestamps
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_embeddings_document_id ON mevzuat_embeddings(document_id);
CREATE INDEX idx_embeddings_chunk_index ON mevzuat_embeddings(chunk_index);
CREATE INDEX idx_embeddings_page_number ON mevzuat_embeddings(page_number);
CREATE INDEX idx_embeddings_created_at ON mevzuat_embeddings(created_at);

-- Create vector similarity index (HNSW for 1536 dimensions)
CREATE INDEX idx_embeddings_vector_hnsw ON mevzuat_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Row Level Security (RLS) policies
ALTER TABLE mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read embeddings for documents they have access to
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

-- Policy: Only system/service can insert embeddings
CREATE POLICY "Service can insert embeddings" ON mevzuat_embeddings
    FOR INSERT WITH CHECK (true);

-- Policy: Only system/service can update embeddings
CREATE POLICY "Service can update embeddings" ON mevzuat_embeddings
    FOR UPDATE USING (true);

-- Policy: Only system/service can delete embeddings
CREATE POLICY "Service can delete embeddings" ON mevzuat_embeddings
    FOR DELETE USING (true);

-- Create trigger for updated_at timestamp
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

-- Grant necessary permissions to service role
GRANT ALL ON mevzuat_embeddings TO service_role;

-- Verify table structure
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'mevzuat_embeddings' 
ORDER BY ordinal_position;

-- Check vector column dimension
SELECT 
    atttypmod 
FROM pg_attribute 
WHERE attrelid = 'mevzuat_embeddings'::regclass 
AND attname = 'embedding';

COMMENT ON TABLE mevzuat_embeddings IS 'Stores vector embeddings for document chunks using text-embedding-3-small (1536 dimensions)';
COMMENT ON COLUMN mevzuat_embeddings.embedding IS 'Vector embedding with 1536 dimensions from OpenAI text-embedding-3-small model';
COMMENT ON INDEX idx_embeddings_vector_hnsw IS 'HNSW index for fast cosine similarity search on 1536-dimensional vectors';