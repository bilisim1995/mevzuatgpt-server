-- ===================================================================
-- MİGRATİON DOĞRULAMA SCRIPTİ
-- Migration'ın başarılı olup olmadığını kontrol eder
-- ===================================================================

-- 1. processing_status kolonunun varlığını kontrol et
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mevzuat_documents' 
            AND column_name = 'processing_status'
        ) THEN '✅ processing_status kolonu MEVCUT'
        ELSE '❌ processing_status kolonu EKSİK'
    END as processing_status_kontrolu;

-- 2. processing_error kolonunun varlığını kontrol et
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mevzuat_documents' 
            AND column_name = 'processing_error'
        ) THEN '✅ processing_error kolonu MEVCUT'
        ELSE '❌ processing_error kolonu EKSİK'
    END as processing_error_kontrolu;

-- 3. Kolon detaylarını göster
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'mevzuat_documents'
AND column_name IN ('processing_status', 'processing_error')
ORDER BY column_name;

-- 4. Mevcut kayıtların processing_status dağılımını göster
SELECT 
    processing_status,
    COUNT(*) as kayit_sayisi,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM public.mevzuat_documents), 2) as yuzde
FROM public.mevzuat_documents
GROUP BY processing_status
ORDER BY kayit_sayisi DESC;

-- 5. processing_status NULL olan kayıtları kontrol et (olması gerekmez)
SELECT 
    COUNT(*) as null_processing_status_sayisi
FROM public.mevzuat_documents
WHERE processing_status IS NULL;

-- 6. Index'in varlığını kontrol et
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'mevzuat_documents' 
            AND indexname = 'idx_mevzuat_documents_processing_status'
        ) THEN '✅ Index MEVCUT'
        ELSE '❌ Index EKSİK'
    END as index_kontrolu;

-- 7. Örnek kayıt göster (processing_status ile)
-- processing_error kolonu varsa onu da göster, yoksa sadece processing_status
SELECT 
    id,
    title,
    filename,
    status,
    processing_status,
    created_at
FROM public.mevzuat_documents
ORDER BY created_at DESC
LIMIT 5;

-- 8. processing_error kolonu varsa detaylı göster (opsiyonel)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mevzuat_documents' 
        AND column_name = 'processing_error'
    ) THEN
        RAISE NOTICE 'processing_error kolonu mevcut - hata mesajları gösteriliyor...';
        -- Bu kısım dinamik SQL ile çalıştırılmalı
    ELSE
        RAISE NOTICE '⚠️ processing_error kolonu HENÜZ EKLENMEMİŞ';
        RAISE NOTICE '💡 Eksik kolonu eklemek için: destek/add_processing_error_column_only.sql scriptini çalıştırın';
    END IF;
END $$;

