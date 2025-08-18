-- ============================================================================
-- MevzuatGPT Minimal Safe Migration (NO CROSS-REFERENCES)
-- ============================================================================
-- Creating tables WITHOUT any foreign key cross-references to avoid dependency issues

-- ============================================================================
-- 1. SEARCH LOGS TABLE (Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
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
-- 2. USER CREDIT BALANCE TABLE (Independent) 
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credit_balance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    current_balance INTEGER DEFAULT 30,
    total_earned INTEGER DEFAULT 30,
    total_spent INTEGER DEFAULT 0,
    last_transaction_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. USER CREDITS TABLE (Independent - NO search_log_id reference)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    reference_id VARCHAR(255), -- Generic reference instead of search_log_id
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. USER FEEDBACK TABLE (Independent - NO search_log_id reference)
-- ============================================================================  
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    reference_id VARCHAR(255), -- Generic reference instead of search_log_id
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
-- 5. SUPPORT TICKETS TABLE (Independent)
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    ticket_number VARCHAR(20),
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    assigned_to UUID,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 6. SUPPORT MESSAGES TABLE (References support_tickets only)
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL,
    user_id UUID NOT NULL,
    message TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false,
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CREATE BASIC INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_search_logs_query_type ON search_logs(query_type);

CREATE INDEX IF NOT EXISTS idx_user_credit_balance_user_id ON user_credit_balance(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);

CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);

CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_id ON support_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_user_id ON support_messages(user_id);

-- ============================================================================
-- ADD SAFE CONSTRAINTS (No foreign keys initially)
-- ============================================================================
DO $$ 
BEGIN
    -- Add unique constraints safely
    BEGIN
        ALTER TABLE user_credit_balance ADD CONSTRAINT unique_user_credit_balance UNIQUE (user_id);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    -- Add basic check constraints
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
END $$;

-- ============================================================================
-- ADD ONLY AUTH.USERS FOREIGN KEYS (These exist for sure)
-- ============================================================================
DO $$ 
BEGIN
    -- Only add foreign keys to auth.users (guaranteed to exist)
    BEGIN
        ALTER TABLE search_logs ADD CONSTRAINT fk_search_logs_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credit_balance ADD CONSTRAINT fk_user_credit_balance_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credits ADD CONSTRAINT fk_user_credits_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_feedback ADD CONSTRAINT fk_user_feedback_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE support_tickets ADD CONSTRAINT fk_support_tickets_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE support_messages ADD CONSTRAINT fk_support_messages_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
    
    -- Only add support_messages -> support_tickets FK
    BEGIN
        ALTER TABLE support_messages ADD CONSTRAINT fk_support_messages_ticket_id FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object OR foreign_key_violation THEN NULL;
    END;
END $$;

-- ============================================================================
-- CREATE BASIC FUNCTIONS AND TRIGGERS
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_search_logs_updated_at ON search_logs;
CREATE TRIGGER update_search_logs_updated_at BEFORE UPDATE ON search_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_credit_balance_updated_at ON user_credit_balance;
CREATE TRIGGER update_user_credit_balance_updated_at BEFORE UPDATE ON user_credit_balance FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_feedback_updated_at ON user_feedback;
CREATE TRIGGER update_user_feedback_updated_at BEFORE UPDATE ON user_feedback FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_support_tickets_updated_at ON support_tickets;
CREATE TRIGGER update_support_tickets_updated_at BEFORE UPDATE ON support_tickets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_support_messages_updated_at ON support_messages;
CREATE TRIGGER update_support_messages_updated_at BEFORE UPDATE ON support_messages FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TICKET NUMBER GENERATION (Optional)
-- ============================================================================
CREATE OR REPLACE FUNCTION generate_ticket_number()
RETURNS TEXT AS $$
BEGIN
    RETURN 'TK-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD((RANDOM() * 99999)::INT::TEXT, 5, '0');
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

DROP TRIGGER IF EXISTS set_support_ticket_number ON support_tickets;
CREATE TRIGGER set_support_ticket_number BEFORE INSERT ON support_tickets FOR EACH ROW EXECUTE FUNCTION set_ticket_number();

-- ============================================================================
-- MIGRATION COMPLETE - NO CROSS-TABLE FOREIGN KEYS
-- ============================================================================