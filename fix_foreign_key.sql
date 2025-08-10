-- Foreign Key Fix for Support System
-- Run in Supabase SQL Editor

-- 1. Check current foreign key constraints
SELECT 
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name IN ('support_tickets', 'support_messages');

-- 2. Add missing foreign key constraint for support_tickets -> user_profiles
ALTER TABLE support_tickets 
ADD CONSTRAINT fk_support_tickets_user_id 
FOREIGN KEY (user_id) REFERENCES user_profiles(id);

-- 3. Add foreign key constraint for support_messages -> user_profiles (sender)
ALTER TABLE support_messages 
ADD CONSTRAINT fk_support_messages_sender_id 
FOREIGN KEY (sender_id) REFERENCES user_profiles(id);

-- 4. Add foreign key constraint for support_messages -> support_tickets
ALTER TABLE support_messages 
ADD CONSTRAINT fk_support_messages_ticket_id 
FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE;

-- 5. Verify the foreign keys are created
SELECT 
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name IN ('support_tickets', 'support_messages')
ORDER BY tc.table_name, tc.constraint_name;

-- 6. Test a simple join to verify relationships work
SELECT 
    st.ticket_number,
    st.subject,
    up.full_name,
    up.email
FROM support_tickets st
LEFT JOIN user_profiles up ON st.user_id = up.id
LIMIT 3;