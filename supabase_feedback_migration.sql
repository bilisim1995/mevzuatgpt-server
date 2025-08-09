-- ===================================================================
-- MEVZUATGPT FEEDBACK SİSTEMİ - SUPABASE MIGRATION
-- Bu SQL kodlarını Supabase SQL Editor'da çalıştırın
-- ===================================================================

-- 1. user_feedback tablosu oluştur (Supabase'de)
CREATE TABLE IF NOT EXISTS public.user_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    search_log_id UUID NOT NULL,
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('positive', 'negative')),
    feedback_comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Spam koruması: Aynı kullanıcı aynı sorguya tek feedback verebilir
    UNIQUE(user_id, search_log_id)
);

-- 2. İndeksler (performans için)
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON public.user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_search_log_id ON public.user_feedback(search_log_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_feedback_type ON public.user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON public.user_feedback(created_at DESC);

-- 3. updated_at otomatik güncelleme fonksiyonu
CREATE OR REPLACE FUNCTION public.update_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Trigger oluştur
DROP TRIGGER IF EXISTS update_user_feedback_updated_at ON public.user_feedback;
CREATE TRIGGER update_user_feedback_updated_at
    BEFORE UPDATE ON public.user_feedback
    FOR EACH ROW
    EXECUTE FUNCTION public.update_feedback_updated_at();

-- 5. RLS (Row Level Security) aktifleştir
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

-- 6. RLS Politikaları
-- Mevcut politikaları sil
DROP POLICY IF EXISTS "Users can view own feedback" ON public.user_feedback;
DROP POLICY IF EXISTS "Users can manage own feedback" ON public.user_feedback;
DROP POLICY IF EXISTS "Admins can view all feedback" ON public.user_feedback;
DROP POLICY IF EXISTS "Service can manage all feedback" ON public.user_feedback;

-- Kullanıcılar sadece kendi feedback'lerini görebilir
CREATE POLICY "Users can view own feedback" ON public.user_feedback
    FOR SELECT USING (auth.uid() = user_id);

-- Kullanıcılar kendi feedback'lerini ekleyebilir/güncelleyebilir
CREATE POLICY "Users can manage own feedback" ON public.user_feedback
    FOR ALL USING (auth.uid() = user_id);

-- Admin kullanıcılar tüm feedback'leri görebilir (user_profiles.role kontrolü)
CREATE POLICY "Admins can view all feedback" ON public.user_feedback
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Admin kullanıcılar tüm feedback'leri yönetebilir
CREATE POLICY "Admins can manage all feedback" ON public.user_feedback
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Service role için özel politika (backend işlemleri için)
CREATE POLICY "Service can manage all feedback" ON public.user_feedback
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- ===================================================================
-- DOĞRULAMA SORGULARI - Supabase SQL Editor'da test edin
-- ===================================================================

-- 1. Tablo oluşturuldu mu?
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'user_feedback'
) as table_exists;

-- 2. Kolonlar doğru mu?
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name = 'user_feedback'
ORDER BY ordinal_position;

-- 3. İndeksler oluşturuldu mu?
SELECT indexname, indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename = 'user_feedback';

-- 4. RLS politikaları kontrol
SELECT policyname, cmd, permissive, roles, qual
FROM pg_policies 
WHERE schemaname = 'public' 
AND tablename = 'user_feedback';

-- 5. Trigger kontrol
SELECT trigger_name, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'public'
AND event_object_table = 'user_feedback';

-- 6. Test insert (manuel test için)
-- INSERT INTO public.user_feedback (user_id, search_log_id, query_text, answer_text, feedback_type)
-- VALUES (auth.uid(), gen_random_uuid(), 'Test soru', 'Test cevap', 'positive');

-- ===================================================================
-- NOT: Bu migration sonrası feedback sistemi Supabase'de hazır
-- Backend servisleri otomatik olarak Supabase'i kullanacak
-- ===================================================================