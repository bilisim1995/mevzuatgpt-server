-- ============================================================================
-- MevzuatGPT Missing Tables Migration (PRODUCTION READY - Final Version)
-- ============================================================================

-- ============================================================================
-- STEP 1: CREATE ALL TABLES WITH BASIC STRUCTURE
-- ============================================================================

-- 1. SEARCH LOGS TABLE
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

-- 2. USER CREDIT BALANCE TABLE
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

-- 3. USER CREDITS TRANSACTION LOG
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    search_log_id UUID,
    reference_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. USER FEEDBACK TABLE
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    search_log_id UUID,
    feedback_type VARCHAR(50) NOT NULL,
    rating INTEGER,
    comment TEXT,
    is_helpful BOOLEAN,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. SUPPORT TICKETS TABLE
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

-- 6. SUPPORT MESSAGES TABLE
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
-- STEP 2: CREATE ALL INDEXES FIRST
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON search_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_search_logs_query_type ON search_logs(query_type);
CREATE INDEX IF NOT EXISTS idx_search_logs_institution ON search_logs(institution_filter);
CREATE INDEX IF NOT EXISTS idx_search_logs_session ON search_logs(session_id);

CREATE INDEX IF NOT EXISTS idx_user_credit_balance_user_id ON user_credit_balance(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credit_balance_updated_at ON user_credit_balance(updated_at);

CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at);
CREATE INDEX IF NOT EXISTS idx_user_credits_transaction_type ON user_credits(transaction_type);
CREATE INDEX IF NOT EXISTS idx_user_credits_search_log_id ON user_credits(search_log_id);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_search_log_id ON user_feedback(search_log_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_feedback_type ON user_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_rating ON user_feedback(rating);

CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned_to ON support_tickets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);

CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_id ON support_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_user_id ON support_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON support_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_support_messages_is_internal ON support_messages(is_internal);

-- ============================================================================
-- STEP 3: ADD CONSTRAINTS CAREFULLY WITH COLUMN CHECKS
-- ============================================================================

DO $$ 
BEGIN
    -- Check if column exists before adding unique constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'support_tickets' 
        AND column_name = 'ticket_number'
        AND table_schema = 'public'
    ) THEN
        BEGIN
            ALTER TABLE support_tickets ADD CONSTRAINT unique_ticket_number UNIQUE (ticket_number);
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
    END IF;
    
    -- Add user_credit_balance unique constraint
    BEGIN
        ALTER TABLE user_credit_balance ADD CONSTRAINT unique_user_credit_balance UNIQUE (user_id);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    -- Add check constraints
    BEGIN
        ALTER TABLE search_logs ADD CONSTRAINT check_query_type CHECK (query_type IN ('search', 'ask', 'browse'));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credit_balance ADD CONSTRAINT check_balance_positive CHECK (current_balance >= 0);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credits ADD CONSTRAINT check_transaction_type CHECK (transaction_type IN ('initial', 'deduction', 'refund', 'bonus', 'purchase'));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_credits ADD CONSTRAINT check_amount_not_zero CHECK (amount != 0);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_feedback ADD CONSTRAINT check_feedback_type CHECK (feedback_type IN ('thumbs_up', 'thumbs_down', 'rating', 'comment', 'bug_report'));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_feedback ADD CONSTRAINT check_rating_range CHECK (rating >= 1 AND rating <= 5);
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE support_tickets ADD CONSTRAINT check_category CHECK (category IN ('general', 'technical', 'billing', 'feature_request', 'bug_report', 'account'));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE support_tickets ADD CONSTRAINT check_priority CHECK (priority IN ('low', 'medium', 'high', 'urgent'));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE support_tickets ADD CONSTRAINT check_status CHECK (status IN ('open', 'in_progress', 'waiting_response', 'resolved', 'closed'));
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
END $$;

-- ============================================================================
-- STEP 4: ADD FOREIGN KEYS WITH TABLE EXISTENCE CHECKS
-- ============================================================================

DO $$ 
BEGIN
    -- Add foreign keys only if target tables exist
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users' AND table_schema = 'auth') THEN
        BEGIN
            ALTER TABLE search_logs ADD CONSTRAINT fk_search_logs_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TABLE user_credit_balance ADD CONSTRAINT fk_user_credit_balance_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TABLE user_credits ADD CONSTRAINT fk_user_credits_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TABLE user_feedback ADD CONSTRAINT fk_user_feedback_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TABLE support_tickets ADD CONSTRAINT fk_support_tickets_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TABLE support_tickets ADD CONSTRAINT fk_support_tickets_assigned_to FOREIGN KEY (assigned_to) REFERENCES auth.users(id);
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
        
        BEGIN
            ALTER TABLE support_messages ADD CONSTRAINT fk_support_messages_user_id FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END;
    END IF;
    
    -- Add inter-table foreign keys
    BEGIN
        ALTER TABLE user_credits ADD CONSTRAINT fk_user_credits_search_log_id FOREIGN KEY (search_log_id) REFERENCES search_logs(id) ON DELETE SET NULL;
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE user_feedback ADD CONSTRAINT fk_user_feedback_search_log_id FOREIGN KEY (search_log_id) REFERENCES search_logs(id) ON DELETE SET NULL;
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
    
    BEGIN
        ALTER TABLE support_messages ADD CONSTRAINT fk_support_messages_ticket_id FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE;
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END;
END $$;

-- ============================================================================
-- STEP 5: CREATE FUNCTIONS AND TRIGGERS
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
    RETURN 'TK-' || TO_CHAR(NOW(), 'YYYY') || '-' || LPAD(EXTRACT(DOY FROM NOW())::TEXT, 3, '0') || '-' || LPAD((RANDOM() * 99999)::INT::TEXT, 5, '0');
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

-- Create triggers
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

DROP TRIGGER IF EXISTS set_support_ticket_number ON support_tickets;
CREATE TRIGGER set_support_ticket_number BEFORE INSERT ON support_tickets FOR EACH ROW EXECUTE FUNCTION set_ticket_number();

-- ============================================================================
-- STEP 6: INITIAL DATA SETUP (Only if tables have data)
-- ============================================================================

DO $$
BEGIN
    -- Check if user_profiles table exists before migration
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_profiles' AND table_schema = 'public') THEN
        INSERT INTO user_credit_balance (user_id, current_balance, total_earned, created_at)
        SELECT 
            up.user_id,
            COALESCE(up.credits, 30) as current_balance,
            COALESCE(up.credits, 30) as total_earned,
            NOW()
        FROM user_profiles up
        WHERE up.user_id NOT IN (SELECT user_id FROM user_credit_balance WHERE user_id IS NOT NULL)
        ON CONFLICT (user_id) DO NOTHING;

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
            SELECT DISTINCT user_id FROM user_credits WHERE transaction_type = 'initial' AND user_id IS NOT NULL
        );
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION (Optional - comment out for production)
-- ============================================================================

-- SELECT 'search_logs' as table_name, count(*) as row_count FROM search_logs
-- UNION ALL SELECT 'user_credit_balance', count(*) FROM user_credit_balance  
-- UNION ALL SELECT 'user_credits', count(*) FROM user_credits
-- UNION ALL SELECT 'user_feedback', count(*) FROM user_feedback
-- UNION ALL SELECT 'support_tickets', count(*) FROM support_tickets
-- UNION ALL SELECT 'support_messages', count(*) FROM support_messages;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================