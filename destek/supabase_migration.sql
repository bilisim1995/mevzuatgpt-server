-- ===================================================================
-- MEVZUATGPT DESTEK TICKET SİSTEMİ - SUPABASE MIGRATION
-- Bu SQL kodlarını Supabase SQL Editor'da çalıştırın
-- ===================================================================

-- 1. support_tickets tablosu oluştur
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number TEXT NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    subject TEXT NOT NULL CHECK (length(subject) <= 200),
    category TEXT NOT NULL CHECK (category IN (
        'teknik_sorun', 'hesap_sorunu', 'ozellik_talebi', 
        'guvenlik', 'faturalandirma', 'genel_soru', 'diger'
    )),
    priority TEXT NOT NULL DEFAULT 'orta' CHECK (priority IN ('dusuk', 'orta', 'yuksek', 'acil')),
    status TEXT NOT NULL DEFAULT 'acik' CHECK (status IN ('acik', 'cevaplandi', 'kapatildi')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. support_messages tablosu oluştur
CREATE TABLE IF NOT EXISTS public.support_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES public.support_tickets(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL,
    message TEXT NOT NULL CHECK (length(message) >= 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Ticket numarası oluşturma için sequence
CREATE SEQUENCE IF NOT EXISTS public.ticket_number_seq START 1;

-- 4. Ticket numarası otomatik oluşturma fonksiyonu
CREATE OR REPLACE FUNCTION public.generate_ticket_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ticket_number IS NULL OR NEW.ticket_number = '' THEN
        NEW.ticket_number = 'TK-' || LPAD(nextval('ticket_number_seq')::TEXT, 6, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. updated_at otomatik güncelleme fonksiyonu
CREATE OR REPLACE FUNCTION public.update_support_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Trigger'lar oluştur
-- Ticket numarası otomatik oluşturma
DROP TRIGGER IF EXISTS generate_ticket_number_trigger ON public.support_tickets;
CREATE TRIGGER generate_ticket_number_trigger
    BEFORE INSERT ON public.support_tickets
    FOR EACH ROW
    EXECUTE FUNCTION public.generate_ticket_number();

-- updated_at otomatik güncelleme
DROP TRIGGER IF EXISTS update_support_tickets_updated_at ON public.support_tickets;
CREATE TRIGGER update_support_tickets_updated_at
    BEFORE UPDATE ON public.support_tickets
    FOR EACH ROW
    EXECUTE FUNCTION public.update_support_updated_at();

-- 7. İndeksler oluştur (performans için)
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON public.support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON public.support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON public.support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON public.support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON public.support_tickets(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_tickets_ticket_number ON public.support_tickets(ticket_number);

CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_id ON public.support_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_sender_id ON public.support_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON public.support_messages(created_at DESC);

-- 8. RLS (Row Level Security) aktifleştir
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_messages ENABLE ROW LEVEL SECURITY;

-- 9. RLS Politikaları - support_tickets
-- Mevcut politikaları sil
DROP POLICY IF EXISTS "Users can view own tickets" ON public.support_tickets;
DROP POLICY IF EXISTS "Users can manage own tickets" ON public.support_tickets;
DROP POLICY IF EXISTS "Admins can view all tickets" ON public.support_tickets;
DROP POLICY IF EXISTS "Admins can manage all tickets" ON public.support_tickets;
DROP POLICY IF EXISTS "Service can manage all tickets" ON public.support_tickets;

-- Kullanıcılar sadece kendi ticket'larını görebilir
CREATE POLICY "Users can view own tickets" ON public.support_tickets
    FOR SELECT USING (auth.uid() = user_id);

-- Kullanıcılar kendi ticket'larını oluşturabilir ve güncelleyebilir
CREATE POLICY "Users can manage own tickets" ON public.support_tickets
    FOR ALL USING (auth.uid() = user_id);

-- Admin kullanıcılar tüm ticket'ları görebilir
CREATE POLICY "Admins can view all tickets" ON public.support_tickets
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Admin kullanıcılar tüm ticket'ları yönetebilir
CREATE POLICY "Admins can manage all tickets" ON public.support_tickets
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Service role için özel politika
CREATE POLICY "Service can manage all tickets" ON public.support_tickets
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- 10. RLS Politikaları - support_messages
DROP POLICY IF EXISTS "Users can view own messages" ON public.support_messages;
DROP POLICY IF EXISTS "Users can create own messages" ON public.support_messages;
DROP POLICY IF EXISTS "Admins can view all messages" ON public.support_messages;
DROP POLICY IF EXISTS "Admins can manage all messages" ON public.support_messages;
DROP POLICY IF EXISTS "Service can manage all messages" ON public.support_messages;

-- Kullanıcılar sadece kendi ticket'larının mesajlarını görebilir
CREATE POLICY "Users can view own messages" ON public.support_messages
    FOR SELECT USING (
        ticket_id IN (
            SELECT id FROM public.support_tickets 
            WHERE user_id = auth.uid()
        )
    );

-- Kullanıcılar kendi ticket'larına mesaj ekleyebilir
CREATE POLICY "Users can create own messages" ON public.support_messages
    FOR INSERT WITH CHECK (
        ticket_id IN (
            SELECT id FROM public.support_tickets 
            WHERE user_id = auth.uid()
        )
        AND sender_id = auth.uid()
    );

-- Admin kullanıcılar tüm mesajları görebilir
CREATE POLICY "Admins can view all messages" ON public.support_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Admin kullanıcılar tüm mesajlara erişebilir
CREATE POLICY "Admins can manage all messages" ON public.support_messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() 
            AND role = 'admin'
        )
    );

-- Service role için özel politika
CREATE POLICY "Service can manage all messages" ON public.support_messages
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- ===================================================================
-- DOĞRULAMA SORGULARI - Test için
-- ===================================================================

-- 1. Tablolar oluşturuldu mu?
SELECT 
    schemaname, tablename, 
    hasindexes, hasrules, hastriggers
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('support_tickets', 'support_messages');

-- 2. Kolonlar doğru mu?
SELECT table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('support_tickets', 'support_messages')
ORDER BY table_name, ordinal_position;

-- 3. İndeksler oluşturuldu mu?
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('support_tickets', 'support_messages')
ORDER BY tablename, indexname;

-- 4. RLS politikaları kontrol
SELECT schemaname, tablename, policyname, cmd, permissive, roles, qual
FROM pg_policies 
WHERE schemaname = 'public' 
AND tablename IN ('support_tickets', 'support_messages')
ORDER BY tablename, policyname;

-- 5. Trigger kontrol
SELECT trigger_name, event_object_table, event_manipulation, action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'public'
AND event_object_table IN ('support_tickets', 'support_messages')
ORDER BY event_object_table, trigger_name;

-- 6. Sequence kontrol
SELECT sequencename, start_value, increment_by, max_value, min_value, cache_value, cycle
FROM pg_sequences 
WHERE schemaname = 'public' 
AND sequencename = 'ticket_number_seq';

-- ===================================================================
-- TEST KAYITLARI (Manuel test için - opsiyonel)
-- ===================================================================

-- Test ticket oluştur (ticket numarası otomatik oluşacak)
-- INSERT INTO public.support_tickets (user_id, subject, category, priority)
-- VALUES (auth.uid(), 'Test ticket', 'teknik_sorun', 'orta');

-- Test mesaj ekle
-- INSERT INTO public.support_messages (ticket_id, sender_id, message)
-- VALUES ((SELECT id FROM support_tickets WHERE subject = 'Test ticket' LIMIT 1), auth.uid(), 'Test mesajı');

-- ===================================================================
-- NOT: Migration tamamlandıktan sonra ticket sistemi kullanıma hazır
-- ===================================================================