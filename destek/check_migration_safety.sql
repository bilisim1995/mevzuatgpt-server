-- ===================================================================
-- MİGRATİON GÜVENLİK KONTROLÜ
-- Bu scripti migration'dan ÖNCE çalıştırarak güvenliği kontrol edin
-- Hiçbir değişiklik yapmaz, sadece bilgi verir
-- ===================================================================

-- 1. Mevcut tablo yapısını kontrol et
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'mevzuat_documents'
ORDER BY ordinal_position;

-- 2. Mevcut kayıt sayısını kontrol et
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
    COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing_count
FROM public.mevzuat_documents;

-- 3. processing_status ve processing_error kolonlarının varlığını kontrol et
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mevzuat_documents' 
            AND column_name = 'processing_status'
        ) THEN 'VAR'
        ELSE 'YOK'
    END as processing_status_kolonu,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mevzuat_documents' 
            AND column_name = 'processing_error'
        ) THEN 'VAR'
        ELSE 'YOK'
    END as processing_error_kolonu;

-- 4. Mevcut RLS politikalarını listele
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'public' 
AND tablename IN ('mevzuat_documents', 'mevzuat_embeddings')
ORDER BY tablename, policyname;

-- 5. Mevcut indexleri listele
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public' 
AND tablename = 'mevzuat_documents'
ORDER BY indexname;

