-- ===================================================================
-- MEVZUATGPT KREDİ SİSTEMİ - DATABASE MIGRATION
-- Bu SQL kodlarını Supabase SQL Editor'da çalıştırın
-- ===================================================================

-- 1. Kredi transaction tablosu oluştur
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

-- 2. Performans için indeksler oluştur
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);
CREATE INDEX IF NOT EXISTS idx_user_credits_user_created ON user_credits(user_id, created_at DESC);

-- 3. Kullanıcı bakiye hesaplama view'i oluştur
CREATE OR REPLACE VIEW user_credit_balance AS 
SELECT 
    user_id, 
    COALESCE(SUM(amount), 0) as current_balance,
    COUNT(*) as transaction_count,
    MAX(created_at) as last_transaction
FROM user_credits 
GROUP BY user_id;

-- 4. RLS (Row Level Security) politikaları
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

-- Kullanıcılar sadece kendi kredilerini görebilir
CREATE POLICY "Users can view own credits" ON user_credits
    FOR SELECT USING (auth.uid() = user_id);

-- Admin kullanıcılar tüm kredileri görebilir  
CREATE POLICY "Admins can view all credits" ON user_credits
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Sadece sistem servisi kredi işlemi yapabilir (INSERT için service key gerekli)
CREATE POLICY "Service can manage credits" ON user_credits
    FOR ALL USING (true);

-- 5. Mevcut tüm kullanıcılara başlangıç kredisi ver (30 kredi)
INSERT INTO user_credits (user_id, transaction_type, amount, balance_after, description)
SELECT 
    user_id,
    'initial',
    30,
    30,
    'Sistem geçiş kredisi - Kredi sistemi aktivasyonu'
FROM user_profiles
WHERE user_id NOT IN (
    SELECT DISTINCT user_id FROM user_credits WHERE transaction_type = 'initial'
);

-- 6. Helpful functions (opsiyonel)

-- Kullanıcı bakiye getirme fonksiyonu
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

-- Kredi transaction ekleme fonksiyonu
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
-- DOĞRULAMA SORGULARI (Migration sonrası test için)
-- ===================================================================

-- Tablo oluşturuldu mu kontrol et
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'user_credits'
) as table_exists;

-- View oluşturuldu mu kontrol et  
SELECT EXISTS (
    SELECT FROM information_schema.views 
    WHERE table_schema = 'public' 
    AND table_name = 'user_credit_balance'
) as view_exists;

-- Kaç kullanıcıya başlangıç kredisi verildi
SELECT COUNT(*) as users_with_initial_credits
FROM user_credits 
WHERE transaction_type = 'initial';

-- Kullanıcı bakiye özetleri
SELECT 
    up.email,
    up.role,
    COALESCE(ucb.current_balance, 0) as credits,
    ucb.transaction_count,
    ucb.last_transaction
FROM user_profiles up
LEFT JOIN user_credit_balance ucb ON up.user_id = ucb.user_id
ORDER BY ucb.current_balance DESC NULLS LAST;

-- ===================================================================
-- NOT: Bu migration'ı çalıştırdıktan sonra, aşağıdaki kontrolleri yapın:
-- 1. user_credits tablosu oluşturuldu mu?
-- 2. user_credit_balance view'i çalışıyor mu? 
-- 3. Mevcut kullanıcılar 30 kredi aldı mı?
-- 4. RLS politikaları aktif mi?
-- ===================================================================