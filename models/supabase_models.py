"""
Supabase database models and table schemas
SQL scripts for creating Supabase tables with vector support
"""

# SQL for creating Supabase tables and functions

SUPABASE_SCHEMA_SQL = """
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (extends auth.users)
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS (Row Level Security)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles" ON public.user_profiles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Documents table
CREATE TABLE IF NOT EXISTS public.mevzuat_documents (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size BIGINT,
    content_preview TEXT,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    uploaded_by UUID REFERENCES auth.users(id),
    status TEXT DEFAULT 'processing' CHECK (status IN ('processing', 'completed', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.mevzuat_documents ENABLE ROW LEVEL SECURITY;

-- RLS Policies for documents
CREATE POLICY "Anyone can view completed documents" ON public.mevzuat_documents
    FOR SELECT USING (status = 'completed');

CREATE POLICY "Admins can manage all documents" ON public.mevzuat_documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Embeddings table for vector search with enhanced source information
CREATE TABLE IF NOT EXISTS public.mevzuat_embeddings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    document_id UUID REFERENCES public.mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INTEGER,
    line_start INTEGER,
    line_end INTEGER,
    embedding vector(1536), -- OpenAI text-embedding-3-large dimension
    chunk_index INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- RLS Policies for embeddings
CREATE POLICY "Anyone can search embeddings" ON public.mevzuat_embeddings
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.mevzuat_documents 
            WHERE id = document_id AND status = 'completed'
        )
    );

CREATE POLICY "Admins can manage embeddings" ON public.mevzuat_embeddings
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Search logs for analytics
CREATE TABLE IF NOT EXISTS public.search_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    query TEXT NOT NULL,
    results_count INTEGER,
    execution_time FLOAT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.search_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for search logs
CREATE POLICY "Users can view own search history" ON public.search_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Anyone can insert search logs" ON public.search_logs
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Admins can view all search logs" ON public.search_logs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Vector search function
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
    page_number integer,
    line_start integer,
    line_end integer,
    similarity float,
    document_title text,
    document_filename text
)
LANGUAGE sql STABLE
AS $$
    SELECT 
        e.id,
        e.document_id,
        e.content,
        e.page_number,
        e.line_start,
        e.line_end,
        1 - (e.embedding <=> query_embedding) AS similarity,
        d.title AS document_title,
        d.filename AS document_filename
    FROM mevzuat_embeddings e
    JOIN mevzuat_documents d ON e.document_id = d.id
    WHERE 
        d.status = 'completed'
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_profiles (id, email, full_name, role)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', new.email),
        COALESCE(new.raw_user_meta_data->>'role', 'user')
    );
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON public.mevzuat_documents
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON public.mevzuat_embeddings(document_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON public.mevzuat_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.mevzuat_documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON public.mevzuat_documents(upload_date);
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON public.search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON public.search_logs(created_at);
"""

SUPABASE_SEED_DATA_SQL = """
-- Insert sample admin user (will be created manually)
-- Password will be set through Supabase Auth UI

-- Insert sample documents (for testing)
INSERT INTO public.mevzuat_documents (
    title, filename, file_url, file_size, content_preview, status, metadata
) VALUES (
    'Örnek Mevzuat Belgesi',
    'ornek_belge.pdf',
    'https://example.com/ornek_belge.pdf',
    1024000,
    'Bu örnek bir mevzuat belgesidir...',
    'completed',
    '{"category": "test", "year": 2024}'
) ON CONFLICT DO NOTHING;
"""