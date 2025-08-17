-- ============================================================================
-- MevzuatGPT Elasticsearch-First Clean Database Schema
-- ============================================================================
-- Architecture:
-- - Supabase PostgreSQL: Auth, user profiles, document metadata, search history
-- - Elasticsearch (https://elastic.mevzuatgpt.org): Vector embeddings and similarity search
-- - No vector operations in PostgreSQL - pure metadata and relational data
-- ============================================================================

-- Enable required extensions (minimal set)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. USER PROFILES TABLE
-- ============================================================================
-- Manages user data, roles, credits, and subscription information
-- Integrated with Supabase Auth via auth.users foreign key
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('admin', 'user', 'premium')),
    organization VARCHAR(255),
    phone VARCHAR(20),
    credits INTEGER DEFAULT 100,
    total_queries INTEGER DEFAULT 0,
    subscription_plan VARCHAR(50) DEFAULT 'free' CHECK (subscription_plan IN ('free', 'basic', 'premium', 'enterprise')),
    subscription_expires_at TIMESTAMPTZ,
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_user_id UNIQUE (user_id),
    CONSTRAINT unique_email UNIQUE (email)
);

-- User profiles indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_role ON user_profiles(role);
CREATE INDEX IF NOT EXISTS idx_user_profiles_created_at ON user_profiles(created_at);
CREATE INDEX IF NOT EXISTS idx_user_profiles_subscription_plan ON user_profiles(subscription_plan);
CREATE INDEX IF NOT EXISTS idx_user_profiles_is_active ON user_profiles(is_active);

-- ============================================================================
-- 2. DOCUMENTS TABLE
-- ============================================================================
-- Document metadata and file information
-- Tracks Elasticsearch indexing status but does NOT store embeddings
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

-- Document indexes for metadata queries and filtering
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
CREATE INDEX IF NOT EXISTS idx_documents_elasticsearch_index_date ON documents(elasticsearch_index_date);

-- Turkish full-text search for document titles and summaries
CREATE INDEX IF NOT EXISTS idx_documents_fulltext ON documents USING GIN(
    to_tsvector('turkish', title || ' ' || COALESCE(summary, '') || ' ' || COALESCE(document_number, ''))
);

-- ============================================================================
-- 3. SEARCH HISTORY TABLE
-- ============================================================================
-- Tracks user queries and responses
-- References Elasticsearch queries but does NOT store embeddings
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

-- Search history indexes
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_session_id ON search_history(session_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);
CREATE INDEX IF NOT EXISTS idx_search_history_search_type ON search_history(search_type);
CREATE INDEX IF NOT EXISTS idx_search_history_filter_institution ON search_history(filter_institution);
CREATE INDEX IF NOT EXISTS idx_search_history_ai_provider ON search_history(ai_provider);
CREATE INDEX IF NOT EXISTS idx_search_history_query_text ON search_history USING GIN(to_tsvector('turkish', query_text));
CREATE INDEX IF NOT EXISTS idx_search_history_elasticsearch_hits ON search_history(elasticsearch_hits_count);

-- ============================================================================
-- 4. ELASTICSEARCH SYNC LOG TABLE
-- ============================================================================
-- Tracks document processing pipeline and Elasticsearch synchronization
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

-- Elasticsearch sync log indexes
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_document_id ON elasticsearch_sync_log(document_id);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_type ON elasticsearch_sync_log(sync_type);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_status ON elasticsearch_sync_log(status);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_started_at ON elasticsearch_sync_log(started_at);
CREATE INDEX IF NOT EXISTS idx_elasticsearch_sync_completed_at ON elasticsearch_sync_log(completed_at);

-- ============================================================================
-- 5. SUPPORT TICKETS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general' CHECK (category IN ('technical', 'billing', 'feature_request', 'bug_report', 'general')),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'waiting_response', 'resolved', 'closed')),
    assigned_to UUID REFERENCES auth.users(id),
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(20),
    attachments JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support tickets indexes
CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_tickets_priority ON support_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned_to ON support_tickets(assigned_to);
CREATE INDEX IF NOT EXISTS idx_support_tickets_created_at ON support_tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_support_tickets_contact_email ON support_tickets(contact_email);

-- ============================================================================
-- 6. SUPPORT MESSAGES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS support_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    sender_type VARCHAR(20) DEFAULT 'user' CHECK (sender_type IN ('user', 'admin', 'system')),
    message TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    is_internal BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Support messages indexes
CREATE INDEX IF NOT EXISTS idx_support_messages_ticket_id ON support_messages(ticket_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_sender_id ON support_messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_sender_type ON support_messages(sender_type);
CREATE INDEX IF NOT EXISTS idx_support_messages_created_at ON support_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_support_messages_is_internal ON support_messages(is_internal);

-- ============================================================================
-- 7. MAINTENANCE MODE TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS maintenance_mode (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    is_enabled BOOLEAN DEFAULT false,
    title VARCHAR(255) DEFAULT 'Sistem Bakımda',
    message TEXT DEFAULT 'Sistem geçici olarak bakımdadır. Lütfen daha sonra tekrar deneyin.',
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    allowed_users UUID[],
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Maintenance mode indexes
CREATE INDEX IF NOT EXISTS idx_maintenance_mode_is_enabled ON maintenance_mode(is_enabled);
CREATE INDEX IF NOT EXISTS idx_maintenance_mode_start_time ON maintenance_mode(start_time);
CREATE INDEX IF NOT EXISTS idx_maintenance_mode_end_time ON maintenance_mode(end_time);

-- ============================================================================
-- 8. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE elasticsearch_sync_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_mode ENABLE ROW LEVEL SECURITY;

-- User Profiles RLS Policies
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all profiles" ON user_profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can update all profiles" ON user_profiles
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "System can insert profiles" ON user_profiles
    FOR INSERT WITH CHECK (true);

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

-- Support Tickets RLS Policies
CREATE POLICY "Users can view own support tickets" ON support_tickets
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can create support tickets" ON support_tickets
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own support tickets" ON support_tickets
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Admins can manage all support tickets" ON support_tickets
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Support Messages RLS Policies
CREATE POLICY "Users can view messages for their tickets" ON support_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM support_tickets 
            WHERE support_tickets.id = support_messages.ticket_id 
            AND support_tickets.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can send messages to their tickets" ON support_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM support_tickets 
            WHERE support_tickets.id = support_messages.ticket_id 
            AND support_tickets.user_id = auth.uid()
        )
    );

CREATE POLICY "Admins can manage all support messages" ON support_messages
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- Maintenance Mode RLS Policies
CREATE POLICY "All users can view maintenance mode" ON maintenance_mode
    FOR SELECT USING (true);

CREATE POLICY "Admins can manage maintenance mode" ON maintenance_mode
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

-- ============================================================================
-- 9. TRIGGERS AND FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON documents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_support_tickets_updated_at 
    BEFORE UPDATE ON support_tickets 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_maintenance_mode_updated_at 
    BEFORE UPDATE ON maintenance_mode 
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

-- Function to log Elasticsearch sync completion
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
-- 10. PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- Set optimal PostgreSQL parameters for this workload
-- (These should be set at database level, included here for reference)
-- shared_buffers = 256MB
-- work_mem = 64MB  
-- maintenance_work_mem = 256MB
-- effective_cache_size = 1GB

-- Analyze all tables for query planner
ANALYZE user_profiles;
ANALYZE documents;
ANALYZE search_history;
ANALYZE elasticsearch_sync_log;
ANALYZE support_tickets;
ANALYZE support_messages;
ANALYZE maintenance_mode;

-- ============================================================================
-- 11. INITIAL DATA AND CONFIGURATIONS
-- ============================================================================

-- Insert default maintenance mode entry (disabled)
INSERT INTO maintenance_mode (is_enabled, title, message) 
VALUES (false, 'Sistem Bakımda', 'Sistem geçici olarak bakımdadır. Lütfen daha sonra tekrar deneyin.')
ON CONFLICT DO NOTHING;

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant limited permissions to anonymous users
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON maintenance_mode TO anon;

-- ============================================================================
-- 12. VIEWS FOR COMMON QUERIES
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
    up.id as user_id,
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

COMMIT;

-- ============================================================================
-- SETUP COMPLETE - ELASTICSEARCH-FIRST ARCHITECTURE
-- ============================================================================
-- Successfully created clean database schema with:
-- 
-- PostgreSQL Tables (7):
-- ✅ user_profiles - User data and subscription management
-- ✅ documents - Document metadata (NO embeddings)
-- ✅ search_history - Query tracking with Elasticsearch metrics
-- ✅ elasticsearch_sync_log - Processing pipeline monitoring
-- ✅ support_tickets - Customer support system
-- ✅ support_messages - Support ticket conversations  
-- ✅ maintenance_mode - System maintenance control
--
-- Architecture Benefits:
-- ✅ No vector operations in PostgreSQL (faster, lighter)
-- ✅ Elasticsearch handles all vector similarity search
-- ✅ Clear separation of concerns
-- ✅ Optimized indexes for metadata queries only
-- ✅ Comprehensive RLS security policies
-- ✅ Turkish language optimization for text search
-- ✅ Automatic processing pipeline tracking
-- ✅ Performance views for monitoring
--
-- External Systems:
-- 🔗 Elasticsearch (https://elastic.mevzuatgpt.org): Vector storage & search
-- 🔗 Supabase Auth: Authentication and authorization  
-- 🔗 Bunny.net CDN: PDF file storage
-- 🔗 Redis Cloud: Caching and task queue
-- ============================================================================