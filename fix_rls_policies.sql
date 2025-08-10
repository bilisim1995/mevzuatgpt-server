-- =====================================================
-- RLS Policy Düzeltme SQL Komutları
-- Supabase SQL Editor'da çalıştırılacak
-- =====================================================

-- 1. Önce mevcut problemli policy'leri kaldır
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Admin can view all profiles" ON user_profiles;
DROP POLICY IF EXISTS "Service role can access all" ON user_profiles;

-- 2. Support tabloları için mevcut policy'leri temizle
DROP POLICY IF EXISTS "Users can view own tickets" ON support_tickets;
DROP POLICY IF EXISTS "Users can create tickets" ON support_tickets;
DROP POLICY IF EXISTS "Admin can view all tickets" ON support_tickets;
DROP POLICY IF EXISTS "Admin can update tickets" ON support_tickets;
DROP POLICY IF EXISTS "Users can view own messages" ON support_messages;
DROP POLICY IF EXISTS "Users can create messages" ON support_messages;
DROP POLICY IF EXISTS "Admin can view all messages" ON support_messages;
DROP POLICY IF EXISTS "Admin can create messages" ON support_messages;

-- 3. Basit user_profiles policy'leri oluştur (döngü olmadan)
CREATE POLICY "Enable read access for users"
ON user_profiles FOR SELECT
USING (auth.uid()::text = id::text);

CREATE POLICY "Enable update for users"
ON user_profiles FOR UPDATE
USING (auth.uid()::text = id::text);

CREATE POLICY "Enable admin access"
ON user_profiles FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM user_profiles up 
    WHERE up.id::text = auth.uid()::text 
    AND up.role = 'admin'
  )
);

-- 4. Support tickets policy'leri
CREATE POLICY "Users can view own tickets"
ON support_tickets FOR SELECT
USING (
  user_id::text = auth.uid()::text
  OR
  EXISTS (
    SELECT 1 FROM user_profiles up 
    WHERE up.id::text = auth.uid()::text 
    AND up.role = 'admin'
  )
);

CREATE POLICY "Users can create tickets"
ON support_tickets FOR INSERT
WITH CHECK (user_id::text = auth.uid()::text);

CREATE POLICY "Admin can update tickets"
ON support_tickets FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM user_profiles up 
    WHERE up.id::text = auth.uid()::text 
    AND up.role = 'admin'
  )
);

-- 5. Support messages policy'leri
CREATE POLICY "Users can view related messages"
ON support_messages FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM support_tickets st
    WHERE st.id = support_messages.ticket_id
    AND (
      st.user_id::text = auth.uid()::text
      OR
      EXISTS (
        SELECT 1 FROM user_profiles up 
        WHERE up.id::text = auth.uid()::text 
        AND up.role = 'admin'
      )
    )
  )
);

CREATE POLICY "Users can create messages"
ON support_messages FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM support_tickets st
    WHERE st.id = support_messages.ticket_id
    AND (
      st.user_id::text = auth.uid()::text
      OR
      EXISTS (
        SELECT 1 FROM user_profiles up 
        WHERE up.id::text = auth.uid()::text 
        AND up.role = 'admin'
      )
    )
  )
);

-- 6. Service role için özel erişim (API key ile çalışan istekler için)
-- Bu policy'ler service_role key kullanılırken RLS'yi bypass eder
ALTER TABLE user_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE support_tickets FORCE ROW LEVEL SECURITY;
ALTER TABLE support_messages FORCE ROW LEVEL SECURITY;

-- 7. Gerekirse service role için bypass policy'si
-- (Sadece gerekli olursa kullan)
-- CREATE POLICY "Service role bypass"
-- ON user_profiles FOR ALL
-- TO service_role
-- USING (true);

-- 8. Tablo izinlerini kontrol et
GRANT ALL ON user_profiles TO authenticated;
GRANT ALL ON user_profiles TO service_role;
GRANT ALL ON support_tickets TO authenticated;
GRANT ALL ON support_tickets TO service_role;
GRANT ALL ON support_messages TO authenticated;
GRANT ALL ON support_messages TO service_role;

-- 9. Sequence izinleri
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- =====================================================
-- Test komutları (isteğe bağlı)
-- =====================================================

-- Mevcut policy'leri kontrol et
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename IN ('user_profiles', 'support_tickets', 'support_messages')
ORDER BY tablename, policyname;

-- Tablo izinlerini kontrol et
SELECT grantee, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE table_name IN ('user_profiles', 'support_tickets', 'support_messages')
ORDER BY table_name, grantee;