-- ===================================================================
-- SADECE processing_error KOLONUNU EKLEME
-- Eğer migration çalıştırıldı ama processing_error kolonu eklenmediyse
-- Bu scripti çalıştırarak sadece eksik kolonu ekleyebilirsiniz
-- ===================================================================

BEGIN;

-- processing_error kolonunu ekle (sadece yoksa)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mevzuat_documents' 
        AND column_name = 'processing_error'
    ) THEN
        ALTER TABLE public.mevzuat_documents 
        ADD COLUMN processing_error TEXT;
        
        RAISE NOTICE '✅ processing_error kolonu başarıyla eklendi';
    ELSE
        RAISE NOTICE 'ℹ️ processing_error kolonu zaten mevcut';
    END IF;
END $$;

COMMIT;

-- Doğrulama
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'mevzuat_documents' 
            AND column_name = 'processing_error'
        ) THEN '✅ processing_error kolonu MEVCUT'
        ELSE '❌ processing_error kolonu EKSİK'
    END as sonuc;

