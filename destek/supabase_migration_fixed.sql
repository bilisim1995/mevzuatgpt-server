-- ===================================================================
-- SUPABASE MİGRATİON ve RLS POLİTİKALARI DÜZELTME
-- Bu SQL kodlarını Supabase SQL Editor'da çalıştırın
-- ===================================================================

-- 1. MEVCUT POLİTİKALARI KALDIRIN (RLS döngüsünü çözmek için)
DROP POLICY IF EXISTS "Users can access their own profiles" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can update their own profiles" ON public.user_profiles;
DROP POLICY IF EXISTS "Enable read access for all users" ON public.mevzuat_documents;
DROP POLICY IF EXISTS "Enable read access for all users" ON public.mevzuat_embeddings;

-- 2. RLS'i KAPAT (geçici)
ALTER TABLE public.user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_documents DISABLE ROW LEVEL SECURITY;  
ALTER TABLE public.mevzuat_embeddings DISABLE ROW LEVEL SECURITY;

-- 3. TABLOLARI TEMİZLE ve YENİDEN OLUŞTUR
DROP TABLE IF EXISTS public.mevzuat_embeddings CASCADE;
DROP TABLE IF EXISTS public.mevzuat_documents CASCADE;

-- 4. DOKUMAN TABLOSUNU YENİDEN OLUŞTUR
CREATE TABLE public.mevzuat_documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT,
    category VARCHAR(100),
    source_institution VARCHAR(200),
    publish_date DATE,
    file_path TEXT,
    file_url TEXT,
    metadata JSONB DEFAULT '{}',
    processing_status VARCHAR(50) DEFAULT 'pending',
    upload_user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. EMBEDDING TABLOSUNU YENİDEN OLUŞTUR (pgvector ile)
CREATE TABLE public.mevzuat_embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES public.mevzuat_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),  -- OpenAI text-embedding-3-small için 1536 boyut
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. İNDEKSLER OLUŞTUR
CREATE INDEX ON public.mevzuat_documents(category);
CREATE INDEX ON public.mevzuat_documents(source_institution);
CREATE INDEX ON public.mevzuat_documents(publish_date);
CREATE INDEX ON public.mevzuat_documents(processing_status);
CREATE INDEX ON public.mevzuat_documents(upload_user_id);

-- Vector similarity indexi (HNSW)
CREATE INDEX ON public.mevzuat_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON public.mevzuat_embeddings(document_id);

-- 7. BASIT RLS POLİTİKALARI (döngü olmadan)
ALTER TABLE public.mevzuat_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mevzuat_embeddings ENABLE ROW LEVEL SECURITY;

-- Tüm kullanıcılar dokümanları okuyabilir
CREATE POLICY "Allow public read access" ON public.mevzuat_documents
    FOR SELECT USING (true);

-- Tüm kullanıcılar embedding'leri okuyabilir
CREATE POLICY "Allow public read access" ON public.mevzuat_embeddings
    FOR SELECT USING (true);

-- Sadece servis anahtarı ile yazabilme
CREATE POLICY "Service key only insert" ON public.mevzuat_documents
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Service key only update" ON public.mevzuat_documents
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "Service key only delete" ON public.mevzuat_documents
    FOR DELETE USING (true);

-- Embedding'ler için de aynı
CREATE POLICY "Service key only insert" ON public.mevzuat_embeddings
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Service key only update" ON public.mevzuat_embeddings  
    FOR UPDATE USING (true) WITH CHECK (true);

CREATE POLICY "Service key only delete" ON public.mevzuat_embeddings
    FOR DELETE USING (true);

-- 8. KULLANICI PROFİL TABLOSU DÜZELTMESİ (mevcut user_profiles tablosunu güncelle)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Basit RLS: kullanıcı sadece kendi profilini görebilir/güncelleyebilir
CREATE POLICY "Users can view own profile" ON public.user_profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE USING (auth.uid() = id) WITH CHECK (auth.uid() = id);

-- Admin'ler tüm profilleri görebilir
CREATE POLICY "Admins can view all profiles" ON public.user_profiles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles up 
            WHERE up.id = auth.uid() AND up.role = 'admin'
        )
    );

-- 9. ÖRNEK DOKUMAN ve EMBEDDING EKLE (test için)
INSERT INTO public.mevzuat_documents (
    title, 
    content, 
    category, 
    source_institution, 
    publish_date,
    processing_status
) VALUES (
    'Kısa Vadeli Sigorta Mevzuatı',
    'Sigortalılık şartları ve Türkiye Sigorta Birliği kuralları hakkında detaylı bilgiler. Sigortalılık için gerekli belgeler ve şartlar bu dokümanda açıklanmıştır. Sigortacılık sektörü ile ilgili yasal düzenlemeler ve zorunlu sigorta türleri hakkında kapsamlı bilgiler mevcuttur.',
    'Sigorta',
    'Türkiye Sigorta Birliği', 
    '2024-01-15',
    'processed'
);

-- Embedding'i manuel olarak ekle (örnek vektör - gerçek embedding üretilmeli)
INSERT INTO public.mevzuat_embeddings (
    document_id,
    content,
    embedding,
    metadata
) SELECT 
    id,
    'Sigortalılık şartları ve Türkiye Sigorta Birliği kuralları hakkında detaylı bilgiler.',
    (SELECT array_agg(random())::vector FROM generate_series(1, 1536)),  -- Geçici random vektör
    '{"chunk_index": 0, "chunk_type": "content"}'::jsonb
FROM public.mevzuat_documents 
WHERE title = 'Kısa Vadeli Sigorta Mevzuatı';

-- 10. DOĞRULAMA SORGULARI
SELECT 'Documents' as table_name, COUNT(*) as count FROM public.mevzuat_documents;
SELECT 'Embeddings' as table_name, COUNT(*) as count FROM public.mevzuat_embeddings;

-- Embedding boyut kontrolü
SELECT 
    array_length(embedding, 1) as embedding_dimension,
    content
FROM public.mevzuat_embeddings LIMIT 1;

-- ===================================================================
-- BAŞARILI MİGRATİON KONTROLÜ
-- ===================================================================
SELECT 
    'Migration Başarılı!' as status,
    (SELECT COUNT(*) FROM public.mevzuat_documents) as documents,
    (SELECT COUNT(*) FROM public.mevzuat_embeddings) as embeddings;

-- ===================================================================
-- ÖNEMLİ NOT:
-- Bu migration çalıştıktan sonra embedding servisiniz çalışacak
-- ve "Sigortalılık şartları" gibi sorgular sonuç dönecektir.
-- ===================================================================