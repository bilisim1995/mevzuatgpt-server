#!/usr/bin/env python3
"""
Setup script to create missing tables in Supabase database
This script will check existing tables and create any missing ones
"""
import os
import logging
from models.supabase_client import supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_existing_tables():
    """Check which tables already exist in Supabase"""
    try:
        # Check if tables exist by trying to query them
        tables_to_check = [
            'user_profiles',
            'mevzuat_documents', 
            'mevzuat_embeddings',
            'search_logs',
            'ai_prompts',
            'support_tickets',
            'user_credits',
            'credit_transactions'
        ]
        
        existing_tables = []
        missing_tables = []
        
        for table in tables_to_check:
            try:
                # Try to query with limit 0 to check if table exists
                result = supabase_client.supabase.table(table).select("*").limit(0).execute()
                existing_tables.append(table)
                logger.info(f"✅ Table '{table}' exists")
            except Exception as e:
                missing_tables.append(table)
                logger.warning(f"❌ Table '{table}' missing: {str(e)}")
        
        return existing_tables, missing_tables
        
    except Exception as e:
        logger.error(f"Failed to check tables: {e}")
        return [], []

def create_missing_tables():
    """Create missing tables using Supabase SQL execution"""
    logger.info("🔧 Creating missing tables in Supabase...")
    
    # AI Prompts table
    ai_prompts_sql = """
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
    
    ALTER TABLE public.ai_prompts ENABLE ROW LEVEL SECURITY;
    
    CREATE POLICY "Anyone can read active prompts" ON public.ai_prompts
        FOR SELECT USING (is_active = true);
    
    CREATE POLICY "Admins can manage prompts" ON public.ai_prompts
        FOR ALL USING (
            EXISTS (
                SELECT 1 FROM public.user_profiles 
                WHERE id = auth.uid() AND role = 'admin'
            )
        );
    
    CREATE INDEX IF NOT EXISTS idx_ai_prompts_provider ON public.ai_prompts(provider);
    CREATE INDEX IF NOT EXISTS idx_ai_prompts_active ON public.ai_prompts(is_active);
    """
    
    # Support Tickets table
    support_tickets_sql = """
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
    
    ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;
    
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
    
    CREATE INDEX IF NOT EXISTS idx_support_tickets_user_id ON public.support_tickets(user_id);
    CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON public.support_tickets(status);
    """
    
    # User Credits table
    user_credits_sql = """
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
    
    ALTER TABLE public.user_credits ENABLE ROW LEVEL SECURITY;
    
    CREATE POLICY "Users can view own credits" ON public.user_credits
        FOR SELECT USING (auth.uid() = user_id);
    
    CREATE POLICY "Admins can manage all credits" ON public.user_credits
        FOR ALL USING (
            EXISTS (
                SELECT 1 FROM public.user_profiles 
                WHERE id = auth.uid() AND role = 'admin'
            )
        );
    
    CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON public.user_credits(user_id);
    """
    
    # Credit Transactions table
    credit_transactions_sql = """
    CREATE TABLE IF NOT EXISTS public.credit_transactions (
        id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
        user_id UUID REFERENCES auth.users(id) NOT NULL,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('purchase', 'usage', 'refund', 'bonus')),
        amount INTEGER NOT NULL,
        description TEXT,
        search_log_id UUID REFERENCES public.search_logs(id),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    
    ALTER TABLE public.credit_transactions ENABLE ROW LEVEL SECURITY;
    
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
    
    CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON public.credit_transactions(user_id);
    """
    
    try:
        # Execute each table creation
        logger.info("Creating ai_prompts table...")
        supabase_client.supabase.rpc('exec_sql', {'sql': ai_prompts_sql}).execute()
        
        logger.info("Creating support_tickets table...")  
        supabase_client.supabase.rpc('exec_sql', {'sql': support_tickets_sql}).execute()
        
        logger.info("Creating user_credits table...")
        supabase_client.supabase.rpc('exec_sql', {'sql': user_credits_sql}).execute()
        
        logger.info("Creating credit_transactions table...")
        supabase_client.supabase.rpc('exec_sql', {'sql': credit_transactions_sql}).execute()
        
        logger.info("✅ All missing tables created successfully!")
        
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        # Alternative: Use raw SQL execution
        logger.info("Trying alternative SQL execution method...")
        try:
            # Try executing via direct SQL
            import asyncpg
            import asyncio
            
            async def execute_sql():
                # Use DATABASE_URL from environment
                database_url = os.getenv('DATABASE_URL')  
                if not database_url:
                    logger.error("DATABASE_URL not found")
                    return
                    
                conn = await asyncpg.connect(database_url)
                
                try:
                    await conn.execute(ai_prompts_sql)
                    logger.info("✅ ai_prompts table created")
                    
                    await conn.execute(support_tickets_sql) 
                    logger.info("✅ support_tickets table created")
                    
                    await conn.execute(user_credits_sql)
                    logger.info("✅ user_credits table created")
                    
                    await conn.execute(credit_transactions_sql)
                    logger.info("✅ credit_transactions table created")
                    
                finally:
                    await conn.close()
            
            asyncio.run(execute_sql())
            logger.info("✅ Alternative method succeeded!")
            
        except Exception as e2:
            logger.error(f"Alternative method also failed: {e2}")

def seed_default_data():
    """Seed some default data for testing"""
    try:
        logger.info("🌱 Seeding default AI prompts...")
        
        # Default Groq system prompt
        default_prompts = [
            {
                "provider": "groq",
                "prompt_type": "system", 
                "content": """Sen Türkiye'nin hukuki mevzuatı konusunda uzman bir yapay zeka asistanısın. Görürverin sağlam kaynakları analiz ederek, kullanıcılara doğru ve güvenilir hukuki bilgiler sunmaktır.

Yanıtlarında şu ilkeleri takip et:
1. Kaynaklara dayalı, doğru bilgi ver
2. Hukuki terminolojiyi açık şekilde kullan  
3. Madde numaraları ve atıfları belirt
4. Güncel mevzuatı referans al
5. Net ve anlaşılır Türkçe kullan

Eğer bir konuda kesin bilgi bulamazsan, bunu açıkça belirt ve genel bilgi verme.""",
                "version": 1,
                "is_active": True
            },
            {
                "provider": "openai",
                "prompt_type": "system",
                "content": """You are an expert AI assistant specializing in Turkish legal legislation. Your goal is to provide accurate and reliable legal information by analyzing solid sources.

Follow these principles in your responses:
1. Provide source-based, accurate information
2. Use legal terminology clearly
3. Specify article numbers and references
4. Reference current legislation
5. Use clear and understandable Turkish

If you cannot find definitive information on a topic, state this clearly and avoid giving general information.""",
                "version": 1,
                "is_active": True
            }
        ]
        
        for prompt in default_prompts:
            try:
                result = supabase_client.supabase.table('ai_prompts').insert(prompt).execute()
                logger.info(f"✅ Seeded {prompt['provider']} prompt")
            except Exception as e:
                logger.warning(f"Failed to seed prompt for {prompt['provider']}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to seed default data: {e}")

def main():
    """Main function to check and setup database tables"""
    logger.info("🚀 Starting Supabase database table setup...")
    
    # Check existing tables
    existing, missing = check_existing_tables()
    
    logger.info(f"📊 Database status:")
    logger.info(f"  Existing tables: {len(existing)}")
    logger.info(f"  Missing tables: {len(missing)}")
    
    if missing:
        logger.info(f"Missing tables: {missing}")
        create_missing_tables()
    else:
        logger.info("✅ All required tables exist!")
    
    # Seed default data
    seed_default_data()
    
    # Final verification
    logger.info("🔍 Final verification...")
    existing, missing = check_existing_tables()
    
    if not missing:
        logger.info("🎉 Database setup complete! All tables are ready.")
    else:
        logger.warning(f"⚠️  Some tables still missing: {missing}")

if __name__ == "__main__":
    main()