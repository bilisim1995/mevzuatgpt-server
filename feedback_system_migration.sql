-- ===================================================================
-- MEVZUATGPT FEEDBACK SİSTEMİ - SUPABASE MIGRATION
-- Bu SQL'i Supabase SQL Editor'da çalıştırın
-- Replit veritabanı KULLANILMAZ - Sadece Supabase!
-- ===================================================================

-- 1. user_feedback tablosu oluştur
CREATE TABLE IF NOT EXISTS user_feedback (
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
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_search_log_id ON user_feedback(search_log_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at DESC);

-- 3. updated_at otomatik güncelleme trigger'ı
CREATE OR REPLACE FUNCTION update_feedback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_feedback_updated_at
    BEFORE UPDATE ON user_feedback
    FOR EACH ROW
    EXECUTE FUNCTION update_feedback_updated_at();

-- 4. RLS (Row Level Security) politikaları
ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

-- Kullanıcılar sadece kendi feedback'lerini görebilir
CREATE POLICY "Users can view own feedback" ON user_feedback
    FOR SELECT USING (auth.uid() = user_id);

-- Kullanıcılar kendi feedback'lerini ekleyebilir/güncelleyebilir
CREATE POLICY "Users can manage own feedback" ON user_feedback
    FOR ALL USING (auth.uid() = user_id);

-- Admin kullanıcılar tüm feedback'leri görebilir
CREATE POLICY "Admins can view all feedback" ON user_feedback
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Sistem servisi tüm feedback'leri yönetebilir
CREATE POLICY "Service can manage all feedback" ON user_feedback
    FOR ALL USING (true);

-- ===================================================================
-- DOĞRULAMA SORGULARI
-- ===================================================================

-- 1. Tablo oluşturuldu mu?
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'user_feedback'
) as table_exists;

-- 2. İndeksler oluşturuldu mu?
SELECT indexname 
FROM pg_indexes 
WHERE tablename = 'user_feedback';

-- 3. RLS politikaları kontrol
SELECT policyname, cmd, permissive 
FROM pg_policies 
WHERE tablename = 'user_feedback';

-- 4. Trigger kontrol
SELECT tgname 
FROM pg_trigger 
WHERE tgrelid = 'user_feedback'::regclass;

-- ===================================================================
-- NOT: Bu migration sonrası feedback sistemi database seviyesinde hazır
-- Artık API endpoint'ler ve servis katmanı oluşturulabilir
-- ===================================================================