-- ============================================================================
-- MevzuatGPT Optimized Clean Database Setup for Self-hosted Supabase
-- ============================================================================
-- Elasticsearch-first architecture - No PostgreSQL embeddings table needed
-- Vectors stored in Elasticsearch at https://elastic.mevzuatgpt.org
-- PostgreSQL only for metadata, user data, and relational information
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- Note: vector extension not needed since Elasticsearch handles vectors

-- ============================================================================
-- 1. USER PROFILES TABLE
-- ============================================================================
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

-- ============================================================================
-- 2. DOCUMENTS TABLE (Enhanced for Elasticsearch integration)
-- ============================================================================
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
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_error TEXT,
    
    -- Elasticsearch integration fields
    elasticsearch_indexed BOOLEAN DEFAULT false,
    elasticsearch_document_count INTEGER DEFAULT 0,
    last_indexed_at TIMESTAMPTZ,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_file_size CHECK (file_size > 0 AND file_size <= 100000000) -- Max 100MB
);

-- Documents indexes (optimized for Elasticsearch workflow)
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
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);

-- Elasticsearch integration indexes
CREATE INDEX IF NOT EXISTS idx_documents_elasticsearch_indexed ON documents(elasticsearch_indexed);
CREATE INDEX IF NOT EXISTS idx_documents_last_indexed_at ON documents(last_indexed_at);

-- Full-text search index for Turkish content
CREATE INDEX IF NOT EXISTS idx_documents_fulltext ON documents USING GIN(
    to_tsvector('turkish', title || ' ' || COALESCE(summary, '') || ' ' || COALESCE(document_number, ''))
);

-- ============================================================================
-- 3. SEARCH HISTORY TABLE (Updated for Elasticsearch queries)
-- ============================================================================
CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id VARCHAR(255),
    query_text TEXT NOT NULL,
    
    -- Elasticsearch query details
    elasticsearch_query JSONB, -- Store the actual ES query for debugging
    elasticsearch_response_time_ms INTEGER,
    
    response_text TEXT,
    response_tokens INTEGER,
    documents_found INTEGER DEFAULT 0,
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    search_type VARCHAR(50) DEFAULT 'semantic' CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
    
    -- Document filtering
    filter_institution VARCHAR(255),
    filter_document_type VARCHAR(100),
    filter_date_range JSONB,
    
    processing_time_ms INTEGER,
    cost_credits INTEGER DEFAULT 1,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_response_tokens CHECK (response_tokens >= 0 AND response_tokens <= 8192),
    CONSTRAINT check_processing_time CHECK (processing_time_ms >= 0)
);

-- Search history indexes
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_session_id ON search_history(session_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);
CREATE INDEX IF NOT EXISTS idx_search_history_search_type ON search_history(search_type);
CREATE INDEX IF NOT EXISTS idx_search_history_filter_institution ON search_history(filter_institution);
CREATE INDEX IF NOT EXISTS idx_search_history_query_text ON search_history USING GIN(to_tsvector('turkish', query_text));
CREATE INDEX IF NOT EXISTS idx_search_history_elasticsearch_query ON search_history USING GIN(elasticsearch_query);

-- ============================================================================
-- 4. SUPPORT TICKETS TABLE
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
-- 5. SUPPORT MESSAGES TABLE
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
-- 6. MAINTENANCE MODE TABLE
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
-- 7. DOCUMENT PROCESSING LOG TABLE (New - for Elasticsearch sync tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_processing_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    processing_step VARCHAR(50) NOT NULL CHECK (processing_step IN ('upload', 'text_extraction', 'chunking', 'embedding', 'elasticsearch_index', 'completed', 'failed')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    details JSONB DEFAULT '{}',
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT check_processing_time_log CHECK (processing_time_ms >= 0)
);

-- Processing log indexes
CREATE INDEX IF NOT EXISTS idx_processing_log_document_id ON document_processing_log(document_id);
CREATE INDEX IF NOT EXISTS idx_processing_log_step ON document_processing_log(processing_step);
CREATE INDEX IF NOT EXISTS idx_processing_log_status ON document_processing_log(status);
CREATE INDEX IF NOT EXISTS idx_processing_log_created_at ON document_processing_log(created_at);

-- ============================================================================
-- 8. ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_mode ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_processing_log ENABLE ROW LEVEL SECURITY;

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

-- Processing Log RLS Policies
CREATE POLICY "Admins can view all processing logs" ON document_processing_log
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "System can insert processing logs" ON document_processing_log
    FOR INSERT WITH CHECK (true);

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
-- 9. TRIGGERS FOR UPDATED_AT TIMESTAMPS
-- ============================================================================

-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to relevant tables
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

-- ============================================================================
-- 10. ELASTICSEARCH INTEGRATION FUNCTIONS
-- ============================================================================

-- Function to mark document as ready for Elasticsearch indexing
CREATE OR REPLACE FUNCTION mark_document_for_indexing()
RETURNS TRIGGER AS $$
BEGIN
    -- When document processing is completed, mark for Elasticsearch indexing
    IF NEW.processing_status = 'completed' AND OLD.processing_status != 'completed' THEN
        NEW.elasticsearch_indexed = false;
        NEW.last_indexed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to documents table
CREATE TRIGGER trigger_mark_document_for_indexing
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION mark_document_for_indexing();

-- ============================================================================
-- 11. PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- Analyze tables for query planner
ANALYZE user_profiles;
ANALYZE documents;
ANALYZE search_history;
ANALYZE support_tickets;
ANALYZE support_messages;
ANALYZE maintenance_mode;
ANALYZE document_processing_log;

-- ============================================================================
-- 12. INITIAL DATA AND CONFIGURATIONS
-- ============================================================================

-- Insert default maintenance mode entry (disabled)
INSERT INTO maintenance_mode (is_enabled, title, message) 
VALUES (false, 'Sistem Bakımda', 'Sistem geçici olarak bakımdadır. Lütfen daha sonra tekrar deneyin.')
ON CONFLICT DO NOTHING;

-- Grant permissions to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant permissions to anon users (limited)
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON maintenance_mode TO anon;

COMMIT;

-- ============================================================================
-- SETUP COMPLETE - ELASTICSEARCH-OPTIMIZED SCHEMA
-- ============================================================================
-- Schema created successfully with:
-- - 6 production-ready tables (NO embeddings table - Elasticsearch handles vectors)
-- - Enhanced documents table with Elasticsearch tracking fields
-- - New document_processing_log table for processing pipeline monitoring
-- - Search history optimized for Elasticsearch queries
-- - Turkish language optimization for metadata search
-- - Comprehensive RLS policies
-- - Performance indexes for relational data only
-- - Automatic triggers for Elasticsearch workflow integration
-- - Security constraints and validations
-- 
-- Vector Storage Architecture:
-- - Elasticsearch (https://elastic.mevzuatgpt.org): Primary vector storage and similarity search
-- - PostgreSQL: Document metadata, user data, search history, and relational information
-- ============================================================================