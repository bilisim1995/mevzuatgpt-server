-- ============================================================================
-- MevzuatGPT Complete Schema Migration (Ignore All Dependencies)
-- ============================================================================
-- Creating all tables independently without any cross-references or foreign keys

-- ============================================================================
-- 1. SEARCH LOGS TABLE (Completely Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_uuid UUID NOT NULL, -- Changed from user_id to avoid conflicts
    session_id VARCHAR(255),
    query TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'search',
    institution_filter VARCHAR(255),
    limit_used INTEGER DEFAULT 5,
    similarity_threshold DECIMAL(3,2) DEFAULT 0.70,
    use_cache BOOLEAN DEFAULT true,
    results_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    reliability_score DECIMAL(3,2),
    confidence_score DECIMAL(3,2),
    credits_used INTEGER DEFAULT 0,
    top_sources JSONB DEFAULT '[]',
    search_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 2. USER CREDIT BALANCE TABLE (Completely Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credit_balance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_uuid UUID NOT NULL, -- Changed from user_id to avoid conflicts
    current_balance INTEGER DEFAULT 30,
    total_earned INTEGER DEFAULT 30,
    total_spent INTEGER DEFAULT 0,
    last_transaction_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. USER CREDITS TABLE (Completely Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_uuid UUID NOT NULL, -- Changed from user_id to avoid conflicts
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    reference_id VARCHAR(255), -- Generic reference
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. USER FEEDBACK TABLE (Completely Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_uuid UUID NOT NULL, -- Changed from user_id to avoid conflicts
    reference_id VARCHAR(255), -- Generic reference
    feedback_type VARCHAR(50) NOT NULL,
    rating INTEGER,
    comment TEXT,
    is_helpful BOOLEAN,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 5. SUPPORT TICKETS TABLE (Completely Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_uuid UUID NOT NULL, -- Changed from user_id to avoid conflicts
    ticket_number VARCHAR(20) UNIQUE,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    assigned_to_uuid UUID, -- Changed from assigned_to to avoid conflicts
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 6. SUPPORT MESSAGES TABLE (Completely Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_uuid UUID NOT NULL, -- Changed from ticket_id to avoid conflicts
    user_uuid UUID NOT NULL, -- Changed from user_id to avoid conflicts
    message TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false,
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CREATE ALL INDEXES (No Foreign Key Dependencies)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_search_logs_user_uuid ON search_logs(user_uuid);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_search_logs_query_type ON search_logs(query_type);
CREATE INDEX IF NOT EXISTS idx_search_logs_institution ON search_logs(institution_filter);
CREATE INDEX IF NOT EXISTS idx_search_logs_session ON search_logs(session_id);

CREATE INDEX IF NOT EXISTS idx_user_credit_balance_user_uuid ON user_credit_balance(user_uuid);
CREATE INDEX IF NOT EXISTS idx_user_credit_balance_updated_at ON user_credit_balance(updated_at);

CREATE INDEX IF NOT EXISTS idx_user_credits_user_uuid ON user_credits(user_uuid);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_uuid ON user_feedback(user_uuid);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_feedback_type ON user_feedback(feedback_type);

CREATE INDEX IF NOT EXISTS idx_support_tickets_user_uuid ON support_tickets(user_uuid);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_support_tickets_ticket_number ON support_tickets(ticket_number);

CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_uuid ON support_messages(ticket_uuid);
CREATE INDEX IF NOT EXISTS idx_support_messages_user_uuid ON support_messages(user_uuid);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON support_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_support_messages_is_internal ON support_messages(is_internal);

-- ============================================================================
-- ADD ONLY BASIC CONSTRAINTS (No Foreign Keys)
-- ============================================================================
DO $$ 
BEGIN
    -- Add basic constraints safely
    BEGIN
        ALTER TABLE user_credit_balance ADD CONSTRAINT unique_user_uuid_balance UNIQUE (user_uuid);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credit_balance ADD CONSTRAINT check_balance_positive CHECK (current_balance >= 0);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credits ADD CONSTRAINT check_amount_not_zero CHECK (amount != 0);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_feedback ADD CONSTRAINT check_rating_range CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
END $$;

-- ============================================================================
-- CREATE BASIC FUNCTIONS ONLY
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TEXT AS $$
BEGIN
    RETURN 'TK-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD((RANDOM() * 9999)::INT::TEXT, 4, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_ticket_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ticket_number IS NULL THEN
        NEW.ticket_number := generate_ticket_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CREATE TRIGGERS (Safe)
-- ============================================================================
DROP TRIGGER IF EXISTS update_search_logs_updated_at ON search_logs;
CREATE TRIGGER update_search_logs_updated_at 
    BEFORE UPDATE ON search_logs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_credit_balance_updated_at ON user_credit_balance;
CREATE TRIGGER update_user_credit_balance_updated_at 
    BEFORE UPDATE ON user_credit_balance 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_feedback_updated_at ON user_feedback;
CREATE TRIGGER update_user_feedback_updated_at 
    BEFORE UPDATE ON user_feedback 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_support_tickets_updated_at ON support_tickets;
CREATE TRIGGER update_support_tickets_updated_at 
    BEFORE UPDATE ON support_tickets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_support_messages_updated_at ON support_messages;
CREATE TRIGGER update_support_messages_updated_at 
    BEFORE UPDATE ON support_messages 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_support_ticket_number ON support_tickets;
CREATE TRIGGER set_support_ticket_number 
    BEFORE INSERT ON support_tickets 
    FOR EACH ROW EXECUTE FUNCTION set_ticket_number();

-- ============================================================================
-- SIMPLE VERIFICATION
-- ============================================================================
SELECT 'Tables created successfully' as status;

-- ============================================================================
-- MIGRATION COMPLETE - NO DEPENDENCIES, NO FOREIGN KEYS
-- ============================================================================