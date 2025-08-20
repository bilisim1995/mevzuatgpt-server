-- Create missing tables in Supabase database
-- AI Prompts table for dynamic prompt management
CREATE TABLE IF NOT EXISTS public.ai_prompts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    provider TEXT NOT NULL CHECK (provider IN ('groq', 'openai', 'claude')),
    prompt_type TEXT NOT NULL CHECK (prompt_type IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support Tickets table
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    subject TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('technical', 'billing', 'general', 'feature_request')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    assigned_to UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- User Credits table
CREATE TABLE IF NOT EXISTS public.user_credits (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) UNIQUE NOT NULL,
    total_credits INTEGER DEFAULT 0,
    used_credits INTEGER DEFAULT 0,
    remaining_credits INTEGER GENERATED ALWAYS AS (total_credits - used_credits) STORED,
    is_unlimited BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Credit Transactions table
CREATE TABLE IF NOT EXISTS public.credit_transactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'usage', 'refund', 'bonus')),
    amount INTEGER NOT NULL,
    description TEXT,
    search_log_id UUID REFERENCES public.search_logs(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on all tables
ALTER TABLE public.ai_prompts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for ai_prompts
CREATE POLICY "Anyone can read active prompts" ON public.ai_prompts
    FOR SELECT USING (is_active = true);

CREATE POLICY "Admins can manage prompts" ON public.ai_prompts
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- RLS Policies for support_tickets
CREATE POLICY "Users can view own tickets" ON public.support_tickets
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create tickets" ON public.support_tickets
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tickets" ON public.support_tickets
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Admins can manage all tickets" ON public.support_tickets
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- RLS Policies for user_credits
CREATE POLICY "Users can view own credits" ON public.user_credits
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Admins can manage all credits" ON public.user_credits
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- RLS Policies for credit_transactions
CREATE POLICY "Users can view own transactions" ON public.credit_transactions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "System can create transactions" ON public.credit_transactions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Admins can view all transactions" ON public.credit_transactions
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_ai_prompts_provider ON public.ai_prompts(provider);
CREATE INDEX IF NOT EXISTS idx_ai_prompts_active ON public.ai_prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON public.support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON public.support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON public.user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);

-- Insert default AI prompts
INSERT INTO public.ai_prompts (provider, prompt_type, content, version, is_active) VALUES
('groq', 'system', 'Sen Türkiye''nin hukuki mevzuatı konusunda uzman bir yapay zeka asistanısın. Görevin sağlam kaynakları analiz ederek, kullanıcılara doğru ve güvenilir hukuki bilgiler sunmaktır.

Yanıtlarında şu ilkeleri takip et:
1. Kaynaklara dayalı, doğru bilgi ver
2. Hukuki terminolojiyi açık şekilde kullan  
3. Madde numaraları ve atıfları belirt
4. Güncel mevzuatı referans al
5. Net ve anlaşılır Türkçe kullan

Eğer bir konuda kesin bilgi bulamazsan, bunu açıkça belirt ve genel bilgi verme.', 1, true),
('openai', 'system', 'You are an expert AI assistant specializing in Turkish legal legislation. Your goal is to provide accurate and reliable legal information by analyzing solid sources.

Follow these principles in your responses:
1. Provide source-based, accurate information
2. Use legal terminology clearly
3. Specify article numbers and references
4. Reference current legislation
5. Use clear and understandable Turkish

If you cannot find definitive information on a topic, state this clearly and avoid giving general information.', 1, true)
ON CONFLICT DO NOTHING;