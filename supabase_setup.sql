-- MevzuatGPT Supabase Database Setup
-- Bu SQL scriptini Supabase Dashboard -> SQL Editor'da çalıştırın

-- 1. pgvector extension'ı etkinleştir
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Users tablosu (Supabase Auth ile entegre)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Documents tablosu
CREATE TABLE IF NOT EXISTS public.mevzuat_documents (
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
    uploaded_by UUID NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Embeddings tablosu (3072 dimension for text-embedding-3-large)
CREATE TABLE IF NOT EXISTS public.mevzuat_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(3072) NOT NULL,
    chunk_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Search logs tablosu
CREATE TABLE IF NOT EXISTS public.search_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id),
    query TEXT NOT NULL,
    results_count INTEGER NOT NULL DEFAULT 0,
    execution_time FLOAT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Processing jobs tablosu
CREATE TABLE IF NOT EXISTS public.processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.mevzuat_documents(id) ON DELETE CASCADE,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    progress INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Indexes
CREATE INDEX IF NOT EXISTS idx_documents_category ON public.mevzuat_documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.mevzuat_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON public.mevzuat_documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON public.mevzuat_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON public.mevzuat_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON public.search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_document_id ON public.processing_jobs(document_id);

-- 8. Admin kullanıcısı ekle
INSERT INTO public.users (id, email, role) 
VALUES ('0dea4151-9ab9-453e-8ef9-2bb94649cc16', 'admin@mevzuatgpt.com', 'admin')
ON CONFLICT (id) DO NOTHING;

-- 9. Test belgesi ekle
INSERT INTO public.mevzuat_documents 
(id, title, category, description, keywords, source_institution, file_name, file_url, file_size, uploaded_by)
VALUES 
('sample-doc-001', 'Supabase Test Belgesi', 'mevzuat', 'Supabase veritabanı test belgesi', 
 ARRAY['test', 'supabase', 'mevzuat'], 'Test Kurumu', 'supabase-test.pdf', 
 'https://cdn.mevzuatgpt.org/supabase-test.pdf', 25000, '0dea4151-9ab9-453e-8ef9-2bb94649cc16')
ON CONFLICT (id) DO NOTHING;

-- 10. Row Level Security (RLS) politikaları
ALTER TABLE public.mevzuat_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- Admin kullanıcıları her şeyi görebilir
CREATE POLICY "Admins can manage all documents" ON public.mevzuat_documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Normal kullanıcılar sadece aktif belgeleri görebilir
CREATE POLICY "Users can view active documents" ON public.mevzuat_documents
    FOR SELECT USING (status = 'active' AND processing_status = 'completed');

-- Embeddings için admin politikası
CREATE POLICY "Admins can manage all embeddings" ON public.mevzuat_embeddings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.users 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Normal kullanıcılar embeddings okuyabilir
CREATE POLICY "Users can view completed embeddings" ON public.mevzuat_embeddings
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.mevzuat_documents 
            WHERE id = document_id 
            AND status = 'active' 
            AND processing_status = 'completed'
        )
    );