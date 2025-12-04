-- ===================================================================
-- SUPABASE MİGRATİON: processing_status ve processing_error kolonları ekleme
-- GÜVENLİ VERSİYON - Canlı veritabanı için hazırlanmıştır
-- Bu SQL kodunu Supabase SQL Editor'da çalıştırın
-- ===================================================================

-- ÖNEMLİ: Bu script sadece YENİ kolonlar ekler, mevcut verilere ZARAR VERMEZ
-- Transaction içinde çalıştırılır, hata durumunda otomatik rollback yapar

BEGIN;

-- 1. Önce mevcut durumu kontrol et (opsiyonel - sadece bilgi için)
DO $$
DECLARE
    col_exists_processing_status BOOLEAN;
    col_exists_processing_error BOOLEAN;
    total_records INTEGER;
BEGIN
    -- Kolonların varlığını kontrol et
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mevzuat_documents' 
        AND column_name = 'processing_status'
    ) INTO col_exists_processing_status;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'mevzuat_documents' 
        AND column_name = 'processing_error'
    ) INTO col_exists_processing_error;
    
    -- Toplam kayıt sayısını kontrol et
    SELECT COUNT(*) INTO total_records FROM public.mevzuat_documents;
    
    RAISE NOTICE 'Migration başlıyor...';
    RAISE NOTICE 'Toplam kayıt sayısı: %', total_records;
    RAISE NOTICE 'processing_status kolonu mevcut mu: %', col_exists_processing_status;
    RAISE NOTICE 'processing_error kolonu mevcut mu: %', col_exists_processing_error;
END $$;

-- 2. Mevcut mevzuat_documents tablosuna eksik kolonları ekle (GÜVENLİ - IF NOT EXISTS)
-- Bu komut sadece kolon yoksa ekler, mevcut verilere dokunmaz
ALTER TABLE public.mevzuat_documents 
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending' 
CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'));

ALTER TABLE public.mevzuat_documents 
ADD COLUMN IF NOT EXISTS processing_error TEXT;

-- 3. Mevcut kayıtlar için processing_status değerini status'a göre güncelle
-- SADECE NULL veya 'pending' olan kayıtları günceller, diğerlerine dokunmaz
UPDATE public.mevzuat_documents 
SET processing_status = CASE 
    WHEN status = 'completed' THEN 'completed'
    WHEN status = 'failed' THEN 'failed'
    WHEN status = 'processing' THEN 'processing'
    ELSE 'pending'
END
WHERE processing_status IS NULL OR processing_status = 'pending';

-- processing_status için index ekle (performans için)
CREATE INDEX IF NOT EXISTS idx_mevzuat_documents_processing_status 
ON public.mevzuat_documents(processing_status);

-- RLS politikalarını güncelle (processing_status kullanarak)
DROP POLICY IF EXISTS "Anyone can view completed documents" ON public.mevzuat_documents;
CREATE POLICY "Anyone can view completed documents" ON public.mevzuat_documents
    FOR SELECT USING (processing_status = 'completed' OR status = 'completed');

-- Vector search fonksiyonunu güncelle (processing_status kullanarak)
-- Sadece mevzuat_embeddings tablosu varsa güncelle
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'mevzuat_embeddings'
    ) THEN
        -- Tablo varsa fonksiyonu güncelle
        EXECUTE '
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
        AS $func$
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
                (d.processing_status = ''completed'' OR d.status = ''completed'')
                AND 1 - (e.embedding <=> query_embedding) > match_threshold
            ORDER BY e.embedding <=> query_embedding
            LIMIT match_count;
        $func$';
        
        RAISE NOTICE 'search_embeddings fonksiyonu güncellendi';
    ELSE
        RAISE NOTICE 'mevzuat_embeddings tablosu bulunamadı, fonksiyon atlandı';
    END IF;
END $$;

-- RLS politikasını embeddings için güncelle (sadece tablo varsa)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'mevzuat_embeddings'
    ) THEN
        -- Tablo varsa RLS politikasını güncelle
        DROP POLICY IF EXISTS "Anyone can search embeddings" ON public.mevzuat_embeddings;
        CREATE POLICY "Anyone can search embeddings" ON public.mevzuat_embeddings
            FOR SELECT USING (
                EXISTS (
                    SELECT 1 FROM public.mevzuat_documents 
                    WHERE id = document_id 
                    AND (processing_status = 'completed' OR status = 'completed')
                )
            );
        
        RAISE NOTICE 'mevzuat_embeddings RLS politikası güncellendi';
    ELSE
        RAISE NOTICE 'mevzuat_embeddings tablosu bulunamadı, RLS politikası atlandı';
    END IF;
END $$;

-- 4. Migration başarılı - Transaction'ı commit et
COMMIT;

-- 5. Sonuç kontrolü (opsiyonel - bilgi amaçlı)
DO $$
DECLARE
    total_records INTEGER;
    completed_count INTEGER;
    failed_count INTEGER;
    processing_count INTEGER;
    pending_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_records FROM public.mevzuat_documents;
    SELECT COUNT(*) INTO completed_count FROM public.mevzuat_documents WHERE processing_status = 'completed';
    SELECT COUNT(*) INTO failed_count FROM public.mevzuat_documents WHERE processing_status = 'failed';
    SELECT COUNT(*) INTO processing_count FROM public.mevzuat_documents WHERE processing_status = 'processing';
    SELECT COUNT(*) INTO pending_count FROM public.mevzuat_documents WHERE processing_status = 'pending';
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration başarıyla tamamlandı!';
    RAISE NOTICE 'Toplam kayıt: %', total_records;
    RAISE NOTICE 'Completed: %', completed_count;
    RAISE NOTICE 'Failed: %', failed_count;
    RAISE NOTICE 'Processing: %', processing_count;
    RAISE NOTICE 'Pending: %', pending_count;
    RAISE NOTICE '========================================';
END $$;

