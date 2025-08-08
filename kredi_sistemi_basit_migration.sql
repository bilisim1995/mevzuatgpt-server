-- ===================================================================
-- MEVZUATGPT KREDİ SİSTEMİ - BASİT MIGRATION (Hatasız Versiyon)
-- Bu SQL'i Supabase'de tek seferde çalıştırabilirsiniz
-- ===================================================================

-- 0. user_profiles tablosuna email kolonu ekle (yeni kayıtlar için)
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS email TEXT;

-- 1. Kredi transaction tablosu
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

-- 2. İndeksler
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);

-- 3. Bakiye view'i
CREATE OR REPLACE VIEW user_credit_balance AS 
SELECT 
    user_id, 
    COALESCE(SUM(amount), 0) as current_balance,
    COUNT(*) as transaction_count,
    MAX(created_at) as last_transaction
FROM user_credits 
GROUP BY user_id;

-- 4. RLS aktifleştir
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- 5. Basit politikalar (RLS)
CREATE POLICY "Users can view own credits" ON user_credits
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service can manage all credits" ON user_credits
    FOR ALL USING (true);

-- 6. Mevcut kullanıcılara kredi ver (basit versiyon)
INSERT INTO user_credits (user_id, transaction_type, amount, balance_after, description)
SELECT 
    id,
    'initial',
    30,
    30,
    'Sistem geçiş kredisi - Kredi sistemi aktivasyonu'
FROM user_profiles
ON CONFLICT DO NOTHING;

-- 7. Bakiye kontrolü fonksiyonu
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

-- Kaç kullanıcıya kredi verildi?
SELECT COUNT(*) as "Kredili Kullanıcı Sayısı"
FROM user_credits 
WHERE transaction_type = 'initial';

-- Kullanıcı bakiye listesi (basit)
SELECT 
    up.id,
    up.email,
    up.full_name,
    up.role,
    COALESCE(ucb.current_balance, 0) as credits
FROM user_profiles up
LEFT JOIN user_credit_balance ucb ON up.id = ucb.user_id
ORDER BY credits DESC;

-- Toplam verilen kredi
SELECT SUM(amount) as "Toplam Verilen Kredi"
FROM user_credits 
WHERE transaction_type = 'initial';

-- ===================================================================
-- Bu basit migration çalıştıktan sonra kredi sistemi aktif olacak!
-- ===================================================================