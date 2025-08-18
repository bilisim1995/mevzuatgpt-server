-- ============================================================================
-- MevzuatGPT Missing Tables Migration
-- ============================================================================
-- Adding missing tables from old database schema to ensure compatibility

-- ============================================================================
-- 1. SEARCH LOGS TABLE (replaces search_history for better compatibility)
-- ============================================================================
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    query TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'search' CHECK (query_type IN ('search', 'ask', 'browse')),
    
    -- Search parameters
    institution_filter VARCHAR(255),
    limit_used INTEGER DEFAULT 5,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.70,
    use_cache BOOLEAN DEFAULT true,
    
    -- Results and performance
    results_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    reliability_score DECIMAL(3,2),
    confidence_score DECIMAL(3,2),
    credits_used INTEGER DEFAULT 0,
    
    -- Search results metadata
    top_sources JSONB DEFAULT '[]',
    search_metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Search logs indexes
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_search_logs_query_type ON search_logs(query_type);
CREATE INDEX IF NOT EXISTS idx_search_logs_institution ON search_logs(institution_filter);
CREATE INDEX IF NOT EXISTS idx_search_logs_session ON search_logs(session_id);

-- Full-text search on queries
CREATE INDEX IF NOT EXISTS idx_search_logs_query_text ON search_logs USING GIN(to_tsvector('turkish', query));

-- ============================================================================
-- 2. USER CREDIT BALANCE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credit_balance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    current_balance INTEGER DEFAULT 30,
    total_earned INTEGER DEFAULT 30,
    total_spent INTEGER DEFAULT 0,
    last_transaction_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_user_credit_balance UNIQUE (user_id),
    CONSTRAINT check_balance_positive CHECK (current_balance >= 0)
);

-- User credit balance indexes
CREATE INDEX IF NOT EXISTS idx_user_credit_balance_user_id ON user_credit_balance(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credit_balance_updated_at ON user_credit_balance(updated_at);

-- ============================================================================
-- 3. USER CREDITS TRANSACTION LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('initial', 'deduction', 'refund', 'bonus', 'purchase')),
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    query_id UUID,
    reference_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_amount_not_zero CHECK (amount != 0)
);

-- User credits indexes
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);
CREATE INDEX IF NOT EXISTS idx_user_credits_query_id ON user_credits(query_id);

-- ============================================================================
-- 4. USER FEEDBACK TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    search_log_id UUID REFERENCES search_logs(id) ON DELETE SET NULL,
    feedback_type VARCHAR(50) NOT NULL CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'rating', 'comment', 'bug_report')),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_helpful BOOLEAN,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User feedback indexes
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_search_log_id ON user_feedback(search_log_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_rating ON user_feedback(rating);

-- ============================================================================
-- 5. SUPPORT TICKETS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general' CHECK (category IN ('general', 'technical', 'billing', 'feature_request', 'bug_report', 'account')),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'waiting_response', 'resolved', 'closed')),
    assigned_to UUID REFERENCES auth.users(id),
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support tickets indexes
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_ticket_number ON support_tickets(ticket_number);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned_to ON support_tickets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);

-- Full-text search on title and description
CREATE INDEX IF NOT EXISTS idx_support_tickets_search ON support_tickets USING GIN(to_tsvector('turkish', title || ' ' || description));

-- ============================================================================
-- 6. SUPPORT MESSAGES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false,
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support messages indexes
CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_id ON support_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_user_id ON support_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON support_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_support_messages_is_internal ON support_messages(is_internal);

-- Full-text search on message content
CREATE INDEX IF NOT EXISTS idx_support_messages_search ON support_messages USING GIN(to_tsvector('turkish', message));

-- ============================================================================
-- 7. AUTOMATIC TICKET NUMBER GENERATION FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TEXT AS $$
BEGIN
    RETURN 'TK-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(EXTRACT(DOY FROM NOW())::TEXT, 3, '0') || '-' || LPAD(FLOOR(EXTRACT(EPOCH FROM NOW()) % 86400)::TEXT, 5, '0');
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. TRIGGERS FOR AUTO-UPDATED TIMESTAMPS
-- ============================================================================

-- Update timestamps trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_search_logs_updated_at BEFORE UPDATE ON search_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_credit_balance_updated_at BEFORE UPDATE ON user_credit_balance FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_feedback_updated_at BEFORE UPDATE ON user_feedback FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_support_tickets_updated_at BEFORE UPDATE ON support_tickets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_support_messages_updated_at BEFORE UPDATE ON support_messages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-generate ticket number trigger
CREATE OR REPLACE FUNCTION set_ticket_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ticket_number IS NULL THEN
        NEW.ticket_number := generate_ticket_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_support_ticket_number BEFORE INSERT ON support_tickets FOR EACH ROW EXECUTE FUNCTION set_ticket_number();

-- ============================================================================
-- 9. INITIAL DATA SETUP
-- ============================================================================

-- Create initial credit balance for existing users (if any)
INSERT INTO user_credit_balance (user_id, current_balance, total_earned, created_at)
SELECT 
    up.user_id,
    COALESCE(up.credits, 30) as current_balance,
    COALESCE(up.credits, 30) as total_earned,
    NOW()
FROM user_profiles up
WHERE up.user_id NOT IN (SELECT user_id FROM user_credit_balance)
ON CONFLICT (user_id) DO NOTHING;

-- Create initial credit transaction records for existing balances
INSERT INTO user_credits (user_id, transaction_type, amount, balance_after, description, created_at)
SELECT 
    ucb.user_id,
    'initial' as transaction_type,
    ucb.current_balance as amount,
    ucb.current_balance as balance_after,
    'Initial credit allocation' as description,
    ucb.created_at
FROM user_credit_balance ucb
WHERE ucb.user_id NOT IN (
    SELECT DISTINCT user_id FROM user_credits WHERE transaction_type = 'initial'
);

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================

-- Verification queries (commented out for production)
-- SELECT 'search_logs' as table_name, count(*) as row_count FROM search_logs
-- UNION ALL SELECT 'user_credit_balance', count(*) FROM user_credit_balance
-- UNION ALL SELECT 'user_credits', count(*) FROM user_credits
-- UNION ALL SELECT 'user_feedback', count(*) FROM user_feedback
-- UNION ALL SELECT 'support_tickets', count(*) FROM support_tickets
-- UNION ALL SELECT 'support_messages', count(*) FROM support_messages;