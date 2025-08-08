-- MevzuatGPT Supabase Clean Setup (Mevcut Policy'leri Temizler)
-- Bu SQL scriptini Supabase Dashboard -> SQL Editor'da çalıştırın

-- 1. Mevcut policy'leri temizle
DROP POLICY IF EXISTS "Kullanıcılar kendi profilini görebilir" ON public.user_profiles;
DROP POLICY IF EXISTS "Kullanıcılar kendi profilini güncelleyebilir" ON public.user_profiles;
DROP POLICY IF EXISTS "Adminler tüm profilleri görebilir" ON public.user_profiles;
DROP POLICY IF EXISTS "Herkes tamamlanmış belgeleri görebilir" ON public.mevzuat_documents;
DROP POLICY IF EXISTS "Adminler tüm belgeleri yönetebilir" ON public.mevzuat_documents;
DROP POLICY IF EXISTS "Herkes embeddings'lerde arama yapabilir" ON public.mevzuat_embeddings;
DROP POLICY IF EXISTS "Adminler embeddings'leri yönetebilir" ON public.mevzuat_embeddings;
DROP POLICY IF EXISTS "Kullanıcılar kendi arama geçmişini görebilir" ON public.search_logs;
DROP POLICY IF EXISTS "Herkes arama logu ekleyebilir" ON public.search_logs;
DROP POLICY IF EXISTS "Adminler tüm arama loglarını görebilir" ON public.search_logs;

-- 2. Mevcut tabloları temizle (varsa)
DROP TABLE IF EXISTS public.search_logs CASCADE;
DROP TABLE IF EXISTS public.mevzuat_embeddings CASCADE;
DROP TABLE IF EXISTS public.mevzuat_documents CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;

-- 3. Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- 4. User profiles tablosu
CREATE TABLE public.user_profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    full_name TEXT,
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Documents tablosu
CREATE TABLE public.mevzuat_documents (
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

-- 6. Embeddings tablosu (1536 dimension)
CREATE TABLE public.mevzuat_embeddings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    document_id UUID REFERENCES public.mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Search logs tablosu
CREATE TABLE public.search_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    query TEXT NOT NULL,
    results_count INTEGER,
    execution_time FLOAT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. RLS etkinleştir
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.search_logs ENABLE ROW LEVEL SECURITY;

-- 9. RLS Politikaları (yeni isimlerle)
CREATE POLICY "users_can_view_own_profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "users_can_update_own_profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id);
CREATE POLICY "admins_can_manage_all_profiles" ON public.user_profiles
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "public_can_view_completed_docs" ON public.mevzuat_documents
    FOR SELECT USING (status = 'completed');
CREATE POLICY "admins_can_manage_all_docs" ON public.mevzuat_documents
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "public_can_search_embeddings" ON public.mevzuat_embeddings
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.mevzuat_documents WHERE id = document_id AND status = 'completed')
    );
CREATE POLICY "admins_can_manage_embeddings" ON public.mevzuat_embeddings
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role = 'admin')
    );

CREATE POLICY "users_can_view_own_searches" ON public.search_logs
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "public_can_insert_search_logs" ON public.search_logs
    FOR INSERT WITH CHECK (true);
CREATE POLICY "admins_can_view_all_searches" ON public.search_logs
    FOR ALL USING (
        EXISTS (SELECT 1 FROM public.user_profiles WHERE id = auth.uid() AND role = 'admin')
    );

-- 10. Trigger fonksiyonları
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_profiles (id, full_name, role)
    VALUES (
        new.id, 
        COALESCE(new.raw_user_meta_data->>'full_name', new.email),
        'user'
    );
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON public.user_profiles;
DROP TRIGGER IF EXISTS update_documents_updated_at ON public.mevzuat_documents;
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON public.mevzuat_documents
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- 11. Vektör arama fonksiyonu
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    document_id uuid,
    content text,
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

-- 12. Performance indexes
CREATE INDEX idx_embeddings_document_id ON public.mevzuat_embeddings(document_id);
CREATE INDEX idx_embeddings_vector ON public.mevzuat_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_documents_status ON public.mevzuat_documents(status);
CREATE INDEX idx_documents_upload_date ON public.mevzuat_documents(upload_date);
CREATE INDEX idx_search_logs_user_id ON public.search_logs(user_id);
CREATE INDEX idx_search_logs_created_at ON public.search_logs(created_at);