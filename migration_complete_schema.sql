-- ============================================================================
-- MevzuatGPT Complete Migration Schema
-- ============================================================================
-- Elasticsearch-first architecture with backward compatibility
-- Includes existing tables + new optimized tables
-- https://elastic.mevzuatgpt.org for vector operations
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. USER PROFILES TABLE (EXISTS - UPDATE STRUCTURE)
-- ============================================================================
-- Update existing user_profiles table with new fields if needed
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50) DEFAULT 'free' CHECK (subscription_plan IN ('free', 'basic', 'premium', 'enterprise'));
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT false;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;

-- Create missing indexes on user_profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role);
CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at);
CREATE INDEX IF NOT EXISTS idx_user_profiles_is_active ON user_profiles(is_active);

-- ============================================================================
-- 2. DOCUMENTS TABLE (RENAME FROM mevzuat_documents)
-- ============================================================================
-- Create new optimized documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    file_size INTEGER,
    institution VARCHAR(255),
    document_type VARCHAR(100) DEFAULT 'kanun' CHECK (document_type IN ('kanun', 'tüzük', 'yönetmelik', 'genelge', 'karar', 'diğer')),
    category VARCHAR(100),
    publication_date DATE,
    effective_date DATE,
    document_number VARCHAR(100),
    keywords TEXT[],
    summary TEXT,
    page_count INTEGER,
    language VARCHAR(10) DEFAULT 'tr',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted', 'processing')),
    uploaded_by UUID REFERENCES auth.users(id),
    
    -- Processing status tracking
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,
    
    -- Elasticsearch integration tracking
    elasticsearch_indexed BOOLEAN DEFAULT false,
    elasticsearch_chunks_count INTEGER DEFAULT 0,
    elasticsearch_index_date TIMESTAMPTZ,
    elasticsearch_last_error TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_file_size CHECK (file_size > 0 AND file_size <= 100000000)
);

-- Migrate data from mevzuat_documents to documents if mevzuat_documents exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mevzuat_documents') THEN
        INSERT INTO documents (
            id, title, filename, file_url, file_size, institution, 
            document_type, category, publication_date, effective_date,
            document_number, keywords, summary, page_count, language,
            status, uploaded_by, metadata, created_at, updated_at
        )
        SELECT 
            COALESCE(id, uuid_generate_v4()),
            COALESCE(title, filename),
            COALESCE(filename, 'unknown.pdf'),
            COALESCE(file_url, ''),
            file_size,
            institution,
            COALESCE(document_type, 'kanun'),
            category,
            publication_date,
            effective_date,
            document_number,
            keywords,
            summary,
            page_count,
            COALESCE(language, 'tr'),
            COALESCE(status, 'active'),
            uploaded_by,
            COALESCE(metadata, '{}'),
            COALESCE(created_at, NOW()),
            COALESCE(updated_at, NOW())
        FROM mevzuat_documents
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE 'Migrated data from mevzuat_documents to documents table';
    END IF;
END $$;

-- Create document indexes
CREATE INDEX IF NOT EXISTS idx_documents_title ON documents USING GIN(to_tsvector('turkish', title));
CREATE INDEX IF NOT EXISTS idx_documents_institution ON documents(institution);
CREATE INDEX IF NOT EXISTS idx_documents_document_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_publication_date ON documents(publication_date);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_processing_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_keywords ON documents USING GIN(keywords);
CREATE INDEX IF NOT EXISTS idx_documents_elasticsearch_indexed ON documents(elasticsearch_indexed);

-- ============================================================================
-- 3. SEARCH HISTORY TABLE (RENAME FROM search_logs)
-- ============================================================================
-- Create new optimized search_history table
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    query_text TEXT NOT NULL,
    
    -- Elasticsearch query tracking
    elasticsearch_query_json JSONB,
    elasticsearch_response_time_ms INTEGER,
    elasticsearch_hits_count INTEGER DEFAULT 0,
    elasticsearch_max_score DECIMAL(5,4),
    
    -- AI response tracking
    response_text TEXT,
    response_tokens INTEGER,
    ai_provider VARCHAR(50) DEFAULT 'groq' CHECK (ai_provider IN ('groq', 'openai')),
    ai_model VARCHAR(100),
    
    -- Search metadata
    documents_found INTEGER DEFAULT 0,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    search_type VARCHAR(50) DEFAULT 'semantic' CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
    
    -- Filtering applied
    filter_institution VARCHAR(255),
    filter_document_type VARCHAR(100),
    filter_date_range JSONB,
    
    -- Performance and cost tracking
    total_processing_time_ms INTEGER,
    cost_credits INTEGER DEFAULT 1,
    
    -- Request metadata
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_response_tokens CHECK (response_tokens >= 0 AND response_tokens <= 8192),
    CONSTRAINT check_processing_time CHECK (total_processing_time_ms >= 0)
);

-- Migrate data from search_logs to search_history if search_logs exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'search_logs') THEN
        INSERT INTO search_history (
            id, user_id, session_id, query_text, response_text,
            documents_found, cost_credits, ip_address, user_agent,
            metadata, created_at
        )
        SELECT 
            COALESCE(id, uuid_generate_v4()),
            user_id,
            session_id,
            COALESCE(query_text, query),
            response_text,
            COALESCE(documents_found, 0),
            COALESCE(cost_credits, 1),
            ip_address,
            user_agent,
            COALESCE(metadata, '{}'),
            COALESCE(created_at, NOW())
        FROM search_logs
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE 'Migrated data from search_logs to search_history table';
    END IF;
END $$;

-- Create search history indexes
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_session_id ON search_history(session_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);
CREATE INDEX IF NOT EXISTS idx_search_history_search_type ON search_history(search_type);
CREATE INDEX IF NOT EXISTS idx_search_history_filter_institution ON search_history(filter_institution);
CREATE INDEX IF NOT EXISTS idx_search_history_query_text ON search_history USING GIN(to_tsvector('turkish', query_text));

-- ============================================================================
-- 4. ELASTICSEARCH SYNC LOG TABLE (NEW)
-- ============================================================================
CREATE TABLE IF NOT EXISTS elasticsearch_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL CHECK (sync_type IN ('index', 'update', 'delete', 'reindex')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    
    -- Elasticsearch operation details
    elasticsearch_index VARCHAR(100) DEFAULT 'mevzuat_embeddings',
    chunks_processed INTEGER DEFAULT 0,
    chunks_total INTEGER DEFAULT 0,
    
    -- Processing details
    processing_details JSONB DEFAULT '{}',
    error_message TEXT,
    error_details JSONB,
    
    -- Performance tracking
    processing_time_ms INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT check_chunks CHECK (chunks_processed >= 0 AND chunks_total >= 0),
    CONSTRAINT check_processing_time_sync CHECK (processing_time_ms >= 0)
);

-- Create elasticsearch sync log indexes
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_document_id ON elasticsearch_sync_log(document_id);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_type ON elasticsearch_sync_log(sync_type);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_status ON elasticsearch_sync_log(status);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_started_at ON elasticsearch_sync_log(started_at);

-- ============================================================================
-- 5. KEEP EXISTING SUPPORT TABLES (maintenance_mode, support_tickets, support_messages)
-- ============================================================================
-- These tables already exist, just ensure indexes

-- Support tickets indexes
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);

-- Support messages indexes
CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_id ON support_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_sender_id ON support_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON support_messages(created_at);

-- Maintenance mode indexes
CREATE INDEX IF NOT EXISTS idx_maintenance_mode_is_enabled ON maintenance_mode(is_enabled);

-- ============================================================================
-- 6. KEEP EXISTING CREDIT TABLES (user_credits, user_credit_balance, user_feedback)
-- ============================================================================
-- These tables will remain for backward compatibility

-- User credits indexes
CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_credits_created_at ON user_credits(created_at);

-- User credit balance indexes  
CREATE INDEX IF NOT EXISTS idx_user_credit_balance_user_id ON user_credit_balance(user_id);

-- User feedback indexes
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON user_feedback(created_at);

-- ============================================================================
-- 7. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on new tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE elasticsearch_sync_log ENABLE ROW LEVEL SECURITY;

-- Documents RLS Policies
CREATE POLICY "All users can view active documents" ON documents
    FOR SELECT USING (status = 'active');

CREATE POLICY "Admins can manage all documents" ON documents
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Uploaders can view their documents" ON documents
    FOR SELECT USING (uploaded_by = auth.uid());

-- Search History RLS Policies
CREATE POLICY "Users can view own search history" ON search_history
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert own search history" ON search_history
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Admins can view all search history" ON search_history
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Elasticsearch Sync Log RLS Policies
CREATE POLICY "Admins can view elasticsearch sync logs" ON elasticsearch_sync_log
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "System can manage elasticsearch sync logs" ON elasticsearch_sync_log
    FOR ALL WITH CHECK (true);

-- ============================================================================
-- 8. TRIGGERS AND FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at trigger to documents
CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to handle document processing status changes
CREATE OR REPLACE FUNCTION handle_document_processing_status()
RETURNS TRIGGER AS $$
BEGIN
    -- When document processing is completed, reset Elasticsearch indexing flags
    IF NEW.processing_status = 'completed' AND OLD.processing_status != 'completed' THEN
        NEW.elasticsearch_indexed = false;
        NEW.elasticsearch_chunks_count = 0;
        NEW.elasticsearch_index_date = NULL;
        NEW.elasticsearch_last_error = NULL;
    END IF;
    
    -- When document is marked for deletion, log it
    IF NEW.status = 'deleted' AND OLD.status != 'deleted' THEN
        INSERT INTO elasticsearch_sync_log (document_id, sync_type, status, processing_details)
        VALUES (NEW.id, 'delete', 'started', '{"reason": "document_deleted"}');
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply document processing trigger
CREATE TRIGGER trigger_handle_document_processing_status
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION handle_document_processing_status();

-- Function to complete Elasticsearch sync
CREATE OR REPLACE FUNCTION complete_elasticsearch_sync()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = NOW();
        NEW.processing_time_ms = EXTRACT(EPOCH FROM (NOW() - NEW.started_at)) * 1000;
        
        -- Update document table with sync results
        IF NEW.sync_type = 'index' THEN
            UPDATE documents 
            SET 
                elasticsearch_indexed = true,
                elasticsearch_chunks_count = NEW.chunks_processed,
                elasticsearch_index_date = NOW()
            WHERE id = NEW.document_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply Elasticsearch sync completion trigger
CREATE TRIGGER trigger_complete_elasticsearch_sync
    BEFORE UPDATE ON elasticsearch_sync_log
    FOR EACH ROW EXECUTE FUNCTION complete_elasticsearch_sync();

-- ============================================================================
-- 9. PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- Analyze all tables for query planner
ANALYZE user_profiles;
ANALYZE documents;
ANALYZE search_history;
ANALYZE elasticsearch_sync_log;
ANALYZE support_tickets;
ANALYZE support_messages;
ANALYZE maintenance_mode;
ANALYZE user_credits;
ANALYZE user_credit_balance;
ANALYZE user_feedback;

-- ============================================================================
-- 10. USEFUL VIEWS FOR MONITORING
-- ============================================================================

-- View for document statistics with Elasticsearch sync status
CREATE OR REPLACE VIEW document_stats AS
SELECT 
    d.id,
    d.title,
    d.institution,
    d.document_type,
    d.status,
    d.processing_status,
    d.elasticsearch_indexed,
    d.elasticsearch_chunks_count,
    d.elasticsearch_index_date,
    COUNT(esl.id) as sync_attempts,
    MAX(esl.completed_at) as last_sync_attempt
FROM documents d
LEFT JOIN elasticsearch_sync_log esl ON d.id = esl.document_id
GROUP BY d.id, d.title, d.institution, d.document_type, d.status, 
         d.processing_status, d.elasticsearch_indexed, 
         d.elasticsearch_chunks_count, d.elasticsearch_index_date;

-- View for user search analytics
CREATE OR REPLACE VIEW user_search_analytics AS
SELECT 
    up.id as user_profile_id,
    up.email,
    up.role,
    COUNT(sh.id) as total_searches,
    AVG(sh.elasticsearch_response_time_ms) as avg_search_time_ms,
    AVG(sh.elasticsearch_hits_count) as avg_results_count,
    SUM(sh.cost_credits) as total_credits_used,
    MAX(sh.created_at) as last_search_date
FROM user_profiles up
LEFT JOIN search_history sh ON up.user_id = sh.user_id
GROUP BY up.id, up.email, up.role;

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant limited permissions to anonymous users
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON maintenance_mode TO anon;

COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- Successfully created/updated database schema with:
-- 
-- ✅ Kept all existing tables (backward compatibility)
-- ✅ Created new optimized documents table (migrated from mevzuat_documents)
-- ✅ Created new search_history table (migrated from search_logs)  
-- ✅ Added new elasticsearch_sync_log table for monitoring
-- ✅ Enhanced user_profiles with subscription fields
-- ✅ All Elasticsearch integration tracking in place
-- ✅ Comprehensive indexes for performance
-- ✅ RLS security policies
-- ✅ Automatic triggers for processing pipeline
-- ✅ Monitoring views for admin dashboard
-- 
-- Architecture:
-- 🔗 PostgreSQL: Metadata, users, search history, support system
-- 🔗 Elasticsearch (https://elastic.mevzuatgpt.org): Vector embeddings & search
-- 🔗 Backward compatibility: All existing tables preserved
-- ============================================================================