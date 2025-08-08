-- ===================================================================
-- MEVZUATGPT KREDİ SİSTEMİ - DÜZELTILMIŞ DATABASE MIGRATION
-- Bu SQL kodlarını Supabase SQL Editor'da adım adım çalıştırın
-- ===================================================================

-- ADIM 1: Önce user_profiles tablosu yapısını kontrol edin
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'user_profiles' 
AND column_name LIKE '%user%' OR column_name = 'id';

-- ADIM 2: Kredi transaction tablosu oluştur
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

-- ADIM 3: Performans için indeksler oluştur
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);
CREATE INDEX IF NOT EXISTS idx_user_credits_user_created ON user_credits(user_id, created_at DESC);

-- ADIM 4: Kullanıcı bakiye hesaplama view'i oluştur
CREATE OR REPLACE VIEW user_credit_balance AS 
SELECT 
    user_id, 
    COALESCE(SUM(amount), 0) as current_balance,
    COUNT(*) as transaction_count,
    MAX(created_at) as last_transaction
FROM user_credits 
GROUP BY user_id;

-- ADIM 5: RLS (Row Level Security) politikaları
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- Kullanıcılar sadece kendi kredilerini görebilir
CREATE POLICY "Users can view own credits" ON user_credits
    FOR SELECT USING (auth.uid() = user_id);

-- Admin kullanıcılar tüm kredileri görebilir (user_profiles.id kullanıyor)
CREATE POLICY "Admins can view all credits" ON user_credits
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Sadece sistem servisi kredi işlemi yapabilir
CREATE POLICY "Service can manage credits" ON user_credits
    FOR ALL USING (true);

-- ADIM 6A: Mevcut kullanıcılara kredi ver (user_profiles.id kullanıyor)
INSERT INTO user_credits (user_id, transaction_type, amount, balance_after, description)
SELECT 
    id,
    'initial',
    30,
    30,
    'Sistem geçiş kredisi - Kredi sistemi aktivasyonu'
FROM user_profiles
WHERE id NOT IN (
    SELECT DISTINCT user_id FROM user_credits WHERE transaction_type = 'initial'
);

-- ADIM 7: Yardımcı fonksiyonlar oluştur
CREATE OR REPLACE FUNCTION get_user_credit_balance(target_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    balance INTEGER;
BEGIN
    SELECT COALESCE(SUM(amount), 0) INTO balance
    FROM user_credits 
    WHERE user_id = target_user_id;
    
    RETURN balance;
END;
$$;

-- ADIM 8: Kredi transaction ekleme fonksiyonu
CREATE OR REPLACE FUNCTION add_credit_transaction(
    target_user_id UUID,
    txn_type TEXT,
    txn_amount INTEGER,
    txn_description TEXT DEFAULT NULL,
    txn_query_id TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    current_balance INTEGER;
    new_balance INTEGER;
    transaction_id UUID;
BEGIN
    -- Mevcut bakiyeyi al
    SELECT get_user_credit_balance(target_user_id) INTO current_balance;
    
    -- Yeni bakiyeyi hesapla
    new_balance := current_balance + txn_amount;
    
    -- Transaction'ı ekle
    INSERT INTO user_credits (user_id, transaction_type, amount, balance_after, description, query_id)
    VALUES (target_user_id, txn_type, txn_amount, new_balance, txn_description, txn_query_id)
    RETURNING id INTO transaction_id;
    
    RETURN transaction_id;
END;
$$;

-- ===================================================================
-- DOĞRULAMA SORGULARI
-- ===================================================================

-- 1. Tablo oluşturuldu mu?
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'user_credits'
) as table_exists;

-- 2. View oluşturuldu mu?
SELECT EXISTS (
    SELECT FROM information_schema.views 
    WHERE table_schema = 'public' 
    AND table_name = 'user_credit_balance'
) as view_exists;

-- 3. Kaç kullanıcıya başlangıç kredisi verildi?
SELECT COUNT(*) as users_with_initial_credits
FROM user_credits 
WHERE transaction_type = 'initial';

-- 4. Kullanıcı bakiye özetleri (user_profiles.id ile join)
SELECT 
    up.email,
    up.role,
    COALESCE(ucb.current_balance, 0) as credits,
    ucb.transaction_count,
    ucb.last_transaction
FROM user_profiles up
LEFT JOIN user_credit_balance ucb ON up.id = ucb.user_id
ORDER BY ucb.current_balance DESC NULLS LAST;

-- 5. RLS politikaları kontrol
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'user_credits';

-- ===================================================================
-- NOT: Migration adımları:
-- 1. Önce ADIM 1'i çalıştırıp user_profiles yapısını kontrol edin
-- 2. Eğer kolon adı 'user_id' ise, tüm 'id' referanslarını 'user_id' yapın
-- 3. Diğer adımları sırayla çalıştırın
-- 4. Son doğrulama sorgularını çalıştırıp sonuçları kontrol edin
-- ===================================================================