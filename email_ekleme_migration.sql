-- ===================================================================
-- USER_PROFILES TABLOSUNA EMAIL KOLONU EKLEME + KREDİ SİSTEMİ
-- Bu migration hem email kolonunu ekler hem kredi sistemi kurar
-- ===================================================================

-- 1. user_profiles tablosuna email kolonu ekle
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS email TEXT;

-- 2. Mevcut kullanıcıların email bilgilerini auth.users tablosundan çek
UPDATE user_profiles 
SET email = au.email
FROM auth.users au
WHERE user_profiles.user_id = au.id 
AND user_profiles.email IS NULL;

-- 3. handle_new_user fonksiyonunu güncelle (yeni kayıtlarda email de kaydetsin)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, email, full_name, role)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'full_name', new.email),
        COALESCE(new.raw_user_meta_data->>'role', 'user')
    );
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 4. Kredi tablosu oluştur
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('initial', 'deduction', 'refund', 'admin_add', 'admin_set')),
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    query_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Kredi tablosu indeksleri
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);

-- 6. Bakiye view'i
CREATE OR REPLACE VIEW user_credit_balance AS 
SELECT 
    user_id, 
    COALESCE(SUM(amount), 0) as current_balance,
    COUNT(*) as transaction_count,
    MAX(created_at) as last_transaction
FROM user_credits 
GROUP BY user_id;

-- 7. RLS aktifleştir
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- 8. Basit RLS politikaları
CREATE POLICY "Users can view own credits" ON user_credits
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service can manage all credits" ON user_credits
    FOR ALL USING (true);

-- 9. Mevcut kullanıcılara 30 kredi ver
INSERT INTO user_credits (user_id, transaction_type, amount, balance_after, description)
SELECT 
    user_id,
    'initial',
    30,
    30,
    'Sistem geçiş kredisi - Email kolonu + Kredi sistemi aktivasyonu'
FROM user_profiles
ON CONFLICT DO NOTHING;

-- 10. Yardımcı fonksiyon
CREATE OR REPLACE FUNCTION get_user_credit_balance(target_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN COALESCE(
        (SELECT SUM(amount) FROM user_credits WHERE user_id = target_user_id),
        0
    );
END;
$$;

-- ===================================================================
-- DOĞRULAMA SORGULARI
-- ===================================================================

-- Email kolonunun eklendi mi?
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'user_profiles' 
AND column_name = 'email';

-- Kullanıcı listesi (email ile birlikte)
SELECT 
    up.user_id,
    up.email,
    up.full_name,
    up.role,
    COALESCE(ucb.current_balance, 0) as credits
FROM user_profiles up
LEFT JOIN user_credit_balance ucb ON up.user_id = ucb.user_id
ORDER BY credits DESC;

-- Kaç kullanıcıya kredi verildi?
SELECT COUNT(*) as "Kredili Kullanıcı Sayısı"
FROM user_credits 
WHERE transaction_type = 'initial';

-- ===================================================================
-- Bu migration sonrası:
-- ✅ user_profiles tablosunda email kolonu olacak  
-- ✅ Yeni kayıtlarda email otomatik kaydedilecek
-- ✅ Mevcut kullanıcıların email bilgisi auth.users'tan çekilecek
-- ✅ Kredi sistemi aktif olacak
-- ===================================================================