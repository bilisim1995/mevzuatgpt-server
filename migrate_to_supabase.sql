-- MevzuatGPT Supabase Migration Script
-- Bu script mevcut tablolarımızı Supabase'e taşır

-- Önce pgvector extension'ı etkinleştir
CREATE EXTENSION IF NOT EXISTS vector;

-- Users tablosu (Supabase Auth ile entegre)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents tablosu
CREATE TABLE IF NOT EXISTS mevzuat_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    keywords TEXT[],
    source_institution VARCHAR(200),
    publish_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    file_name VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_size BIGINT,
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processing_error TEXT,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Embeddings tablosu
CREATE TABLE IF NOT EXISTS mevzuat_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(3072) NOT NULL,
    chunk_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_documents_category ON mevzuat_documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_status ON mevzuat_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON mevzuat_documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON mevzuat_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON mevzuat_embeddings USING ivfflat (embedding vector_cosine_ops);

-- Search logs tablosu
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    query TEXT NOT NULL,
    results_count INTEGER NOT NULL DEFAULT 0,
    execution_time FLOAT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Processing jobs tablosu
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES mevzuat_documents(id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS Policies (Row Level Security)
ALTER TABLE mevzuat_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- Admin kullanıcıları her şeyi görebilir
CREATE POLICY "Admins can view all documents" ON mevzuat_documents
    FOR ALL USING (auth.jwt() ->> 'role' = 'admin');

-- Normal kullanıcılar sadece aktif belgeleri görebilir
CREATE POLICY "Users can view active documents" ON mevzuat_documents
    FOR SELECT USING (status = 'active' AND processing_status = 'completed');

-- Embeddings için benzer politikalar
CREATE POLICY "Admins can view all embeddings" ON mevzuat_embeddings
    FOR ALL USING (auth.jwt() ->> 'role' = 'admin');

CREATE POLICY "Users can view completed embeddings" ON mevzuat_embeddings
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM mevzuat_documents 
            WHERE id = document_id 
            AND status = 'active' 
            AND processing_status = 'completed'
        )
    );

-- Test admin kullanıcısı ekle
INSERT INTO users (id, email, role) 
VALUES ('0dea4151-9ab9-453e-8ef9-2bb94649cc16', 'admin@mevzuatgpt.com', 'admin')
ON CONFLICT (id) DO NOTHING;