#!/usr/bin/env python3
"""
MevzuatGPT Clean Database Setup Script
Creates production-ready schema for self-hosted Supabase
"""
import asyncio
import asyncpg
import os
import sys
from datetime import datetime

class DatabaseSetup:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Parse DATABASE_URL to get connection parameters
        import urllib.parse
        parsed = urllib.parse.urlparse(self.db_url)
        self.connection_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path else 'postgres',
            'user': parsed.username,
            'password': urllib.parse.unquote(parsed.password)
        }
        
    async def run_setup(self):
        """Run the complete database setup"""
        print(f"🚀 Starting MevzuatGPT Clean Database Setup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        try:
            conn = await asyncpg.connect(**self.connection_params)
            print(f"✅ Connected to PostgreSQL at {self.connection_params['host']}")
            
            # Check database version and extensions
            await self.check_database_info(conn)
            
            # Create extensions
            await self.create_extensions(conn)
            
            # Create tables
            await self.create_tables(conn)
            
            # Create indexes
            await self.create_indexes(conn)
            
            # Setup RLS policies
            await self.setup_rls_policies(conn)
            
            # Create triggers
            await self.create_triggers(conn)
            
            # Insert initial data
            await self.insert_initial_data(conn)
            
            # Performance optimizations
            await self.optimize_performance(conn)
            
            await conn.close()
            print("\n🎉 Database setup completed successfully!")
            print("="*80)
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            sys.exit(1)
    
    async def check_database_info(self, conn):
        """Check database version and capabilities"""
        print("\n🔍 Checking Database Information...")
        
        # Get PostgreSQL version
        version = await conn.fetchval("SELECT version()")
        print(f"   PostgreSQL Version: {version[:50]}...")
        
        # Check if extensions exist
        extensions = await conn.fetch("""
            SELECT extname FROM pg_extension 
            WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector')
        """)
        
        existing_extensions = [ext['extname'] for ext in extensions]
        print(f"   Existing Extensions: {existing_extensions}")
        
        # Check existing tables
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        
        if tables:
            table_names = [table['table_name'] for table in tables]
            print(f"   Existing Tables: {table_names}")
        else:
            print("   Existing Tables: None")
    
    async def create_extensions(self, conn):
        """Create required PostgreSQL extensions"""
        print("\n🔧 Creating PostgreSQL Extensions...")
        
        extensions = [
            ('uuid-ossp', 'UUID generation functions'),
            ('pgcrypto', 'Cryptographic functions'),
            ('vector', 'Vector similarity search')
        ]
        
        for ext_name, description in extensions:
            try:
                await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext_name}"')
                print(f"   ✅ {ext_name}: {description}")
            except Exception as e:
                print(f"   ❌ {ext_name}: {e}")
    
    async def create_tables(self, conn):
        """Create all application tables"""
        print("\n📋 Creating Database Tables...")
        
        # 1. User Profiles Table
        await self.create_user_profiles_table(conn)
        
        # 2. Documents Table  
        await self.create_documents_table(conn)
        
        # 3. Embeddings Table
        await self.create_embeddings_table(conn)
        
        # 4. Search History Table
        await self.create_search_history_table(conn)
        
        # 5. Support Tickets Table
        await self.create_support_tickets_table(conn)
        
        # 6. Support Messages Table
        await self.create_support_messages_table(conn)
        
        # 7. Maintenance Mode Table
        await self.create_maintenance_mode_table(conn)
    
    async def create_user_profiles_table(self, conn):
        """Create user_profiles table"""
        sql = """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL,
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
        )
        """
        await conn.execute(sql)
        print("   ✅ user_profiles table created")
    
    async def create_documents_table(self, conn):
        """Create documents table"""
        sql = """
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
            uploaded_by UUID,
            processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
            processing_error TEXT,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            CONSTRAINT check_file_size CHECK (file_size > 0 AND file_size <= 100000000)
        )
        """
        await conn.execute(sql)
        print("   ✅ documents table created")
    
    async def create_embeddings_table(self, conn):
        """Create embeddings table with 2048-dimensional vectors"""
        sql = """
        CREATE TABLE IF NOT EXISTS embeddings (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            embedding vector(2048) NOT NULL,
            token_count INTEGER,
            chunk_type VARCHAR(50) DEFAULT 'text' CHECK (chunk_type IN ('text', 'header', 'table', 'list')),
            page_number INTEGER,
            section_title VARCHAR(255),
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            
            CONSTRAINT unique_document_chunk UNIQUE (document_id, chunk_index),
            CONSTRAINT unique_content_hash UNIQUE (content_hash),
            CONSTRAINT check_chunk_index CHECK (chunk_index >= 0),
            CONSTRAINT check_token_count CHECK (token_count > 0 AND token_count <= 8192)
        )
        """
        await conn.execute(sql)
        print("   ✅ embeddings table created (2048-dimensional vectors)")
    
    async def create_search_history_table(self, conn):
        """Create search_history table"""
        sql = """
        CREATE TABLE IF NOT EXISTS search_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID,
            session_id VARCHAR(255),
            query_text TEXT NOT NULL,
            query_embedding vector(2048),
            response_text TEXT,
            response_tokens INTEGER,
            documents_found INTEGER DEFAULT 0,
            confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
            search_type VARCHAR(50) DEFAULT 'semantic' CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
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
        )
        """
        await conn.execute(sql)
        print("   ✅ search_history table created")
    
    async def create_support_tickets_table(self, conn):
        """Create support_tickets table"""
        sql = """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID,
            title VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(100) DEFAULT 'general' CHECK (category IN ('technical', 'billing', 'feature_request', 'bug_report', 'general')),
            priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
            status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'waiting_response', 'resolved', 'closed')),
            assigned_to UUID,
            contact_email VARCHAR(255) NOT NULL,
            contact_phone VARCHAR(20),
            attachments JSONB DEFAULT '[]',
            metadata JSONB DEFAULT '{}',
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
        await conn.execute(sql)
        print("   ✅ support_tickets table created")
    
    async def create_support_messages_table(self, conn):
        """Create support_messages table"""
        sql = """
        CREATE TABLE IF NOT EXISTS support_messages (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
            sender_id UUID,
            sender_type VARCHAR(20) DEFAULT 'user' CHECK (sender_type IN ('user', 'admin', 'system')),
            message TEXT NOT NULL,
            attachments JSONB DEFAULT '[]',
            is_internal BOOLEAN DEFAULT false,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
        await conn.execute(sql)
        print("   ✅ support_messages table created")
    
    async def create_maintenance_mode_table(self, conn):
        """Create maintenance_mode table"""
        sql = """
        CREATE TABLE IF NOT EXISTS maintenance_mode (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            is_enabled BOOLEAN DEFAULT false,
            title VARCHAR(255) DEFAULT 'Sistem Bakımda',
            message TEXT DEFAULT 'Sistem geçici olarak bakımdadır. Lütfen daha sonra tekrar deneyin.',
            start_time TIMESTAMPTZ,
            end_time TIMESTAMPTZ,
            allowed_users UUID[],
            created_by UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """
        await conn.execute(sql)
        print("   ✅ maintenance_mode table created")
    
    async def create_indexes(self, conn):
        """Create performance indexes"""
        print("\n📊 Creating Performance Indexes...")
        
        indexes = [
            # User profiles indexes
            ("idx_user_profiles_user_id", "user_profiles", "(user_id)"),
            ("idx_user_profiles_email", "user_profiles", "(email)"),
            ("idx_user_profiles_role", "user_profiles", "(role)"),
            ("idx_user_profiles_created_at", "user_profiles", "(created_at)"),
            
            # Documents indexes
            ("idx_documents_institution", "documents", "(institution)"),
            ("idx_documents_document_type", "documents", "(document_type)"),
            ("idx_documents_status", "documents", "(status)"),
            ("idx_documents_processing_status", "documents", "(processing_status)"),
            ("idx_documents_created_at", "documents", "(created_at)"),
            
            # Embeddings indexes
            ("idx_embeddings_document_id", "embeddings", "(document_id)"),
            ("idx_embeddings_chunk_index", "embeddings", "(chunk_index)"),
            ("idx_embeddings_content_hash", "embeddings", "(content_hash)"),
            ("idx_embeddings_created_at", "embeddings", "(created_at)"),
            
            # Search history indexes
            ("idx_search_history_user_id", "search_history", "(user_id)"),
            ("idx_search_history_session_id", "search_history", "(session_id)"),
            ("idx_search_history_created_at", "search_history", "(created_at)"),
            ("idx_search_history_search_type", "search_history", "(search_type)"),
            
            # Support indexes
            ("idx_support_tickets_user_id", "support_tickets", "(user_id)"),
            ("idx_support_tickets_status", "support_tickets", "(status)"),
            ("idx_support_tickets_category", "support_tickets", "(category)"),
            ("idx_support_messages_ticket_id", "support_messages", "(ticket_id)"),
            
            # Maintenance indexes
            ("idx_maintenance_mode_is_enabled", "maintenance_mode", "(is_enabled)"),
        ]
        
        for index_name, table_name, columns in indexes:
            try:
                await conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}")
                print(f"   ✅ {index_name}")
            except Exception as e:
                print(f"   ❌ {index_name}: {e}")
        
        # Special indexes for vector search
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_vector_hnsw ON embeddings 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """)
            print("   ✅ idx_embeddings_vector_hnsw (HNSW for vector similarity)")
        except Exception as e:
            print(f"   ❌ HNSW vector index: {e}")
        
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_history_query_embedding ON search_history 
                USING hnsw (query_embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """)
            print("   ✅ idx_search_history_query_embedding (HNSW for query similarity)")
        except Exception as e:
            print(f"   ❌ Query embedding index: {e}")
        
        # Turkish full-text search indexes
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_title ON documents 
                USING GIN(to_tsvector('turkish', title))
            """)
            print("   ✅ idx_documents_title (Turkish full-text search)")
        except Exception as e:
            print(f"   ❌ Turkish title index: {e}")
        
        try:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_content_search ON embeddings 
                USING GIN(to_tsvector('turkish', content))
            """)
            print("   ✅ idx_embeddings_content_search (Turkish content search)")
        except Exception as e:
            print(f"   ❌ Turkish content index: {e}")
    
    async def setup_rls_policies(self, conn):
        """Setup Row Level Security policies"""
        print("\n🔒 Setting up Row Level Security (RLS)...")
        
        # For self-hosted Supabase without auth.users table, we'll skip RLS for now
        # RLS can be configured later when auth system is properly integrated
        print("   ⚠️  Skipping RLS setup - requires auth.users table integration")
        print("   💡 RLS policies can be added later when Supabase Auth is fully configured")
    
    async def create_triggers(self, conn):
        """Create database triggers"""
        print("\n⚡ Creating Database Triggers...")
        
        # Create timestamp update function
        await conn.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        print("   ✅ update_updated_at_column() function created")
        
        # Apply triggers to tables with updated_at columns
        triggers = [
            ("update_user_profiles_updated_at", "user_profiles"),
            ("update_documents_updated_at", "documents"),
            ("update_support_tickets_updated_at", "support_tickets"),
            ("update_maintenance_mode_updated_at", "maintenance_mode"),
        ]
        
        for trigger_name, table_name in triggers:
            try:
                await conn.execute(f"""
                    CREATE TRIGGER {trigger_name} 
                    BEFORE UPDATE ON {table_name} 
                    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()
                """)
                print(f"   ✅ {trigger_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"   ⚠️  {trigger_name} (already exists)")
                else:
                    print(f"   ❌ {trigger_name}: {e}")
    
    async def insert_initial_data(self, conn):
        """Insert initial configuration data"""
        print("\n📝 Inserting Initial Data...")
        
        # Insert default maintenance mode entry (disabled)
        try:
            await conn.execute("""
                INSERT INTO maintenance_mode (is_enabled, title, message) 
                VALUES (false, 'Sistem Bakımda', 'Sistem geçici olarak bakımdadır. Lütfen daha sonra tekrar deneyin.')
                ON CONFLICT DO NOTHING
            """)
            print("   ✅ Default maintenance mode entry created")
        except Exception as e:
            print(f"   ❌ Maintenance mode entry: {e}")
    
    async def optimize_performance(self, conn):
        """Run performance optimizations"""
        print("\n🚀 Running Performance Optimizations...")
        
        # Analyze tables for query planner
        tables = [
            'user_profiles', 'documents', 'embeddings', 
            'search_history', 'support_tickets', 'support_messages', 
            'maintenance_mode'
        ]
        
        for table in tables:
            try:
                await conn.execute(f"ANALYZE {table}")
                print(f"   ✅ Analyzed {table}")
            except Exception as e:
                print(f"   ❌ Analyze {table}: {e}")
        
        print("   💡 Performance optimization recommendations:")
        print("      - Set work_mem = '256MB' for vector operations")
        print("      - Monitor vector index performance with EXPLAIN ANALYZE")
        print("      - Consider increasing shared_buffers for large datasets")

if __name__ == "__main__":
    setup = DatabaseSetup()
    asyncio.run(setup.run_setup())