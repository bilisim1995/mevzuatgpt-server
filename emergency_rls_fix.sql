-- Emergency RLS Fix - Complete Bypass for Service Role
-- Run this in Supabase SQL Editor

-- 1. Disable RLS on all support tables temporarily
ALTER TABLE user_profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets DISABLE ROW LEVEL SECURITY; 
ALTER TABLE support_messages DISABLE ROW LEVEL SECURITY;

-- 2. Grant full access to service_role
GRANT ALL ON user_profiles TO service_role;
GRANT ALL ON support_tickets TO service_role;  
GRANT ALL ON support_messages TO service_role;
GRANT ALL ON support_ticket_number_seq TO service_role;

-- 3. Enable RLS but with bypass for service_role
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_messages ENABLE ROW LEVEL SECURITY;

-- 4. Create simple bypass policies for service_role
CREATE POLICY "service_role_bypass_user_profiles" ON user_profiles FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_bypass_support_tickets" ON support_tickets FOR ALL TO service_role USING (true);
CREATE POLICY "service_role_bypass_support_messages" ON support_messages FOR ALL TO service_role USING (true);

-- 5. Create basic authenticated user policies
CREATE POLICY "users_own_tickets" ON support_tickets FOR SELECT TO authenticated USING (user_id::text = auth.uid()::text);
CREATE POLICY "users_create_tickets" ON support_tickets FOR INSERT TO authenticated WITH CHECK (user_id::text = auth.uid()::text);

-- 6. Test the tables
SELECT 'user_profiles' as table_name, count(*) as row_count FROM user_profiles
UNION ALL  
SELECT 'support_tickets' as table_name, count(*) as row_count FROM support_tickets
UNION ALL
SELECT 'support_messages' as table_name, count(*) as row_count FROM support_messages;
