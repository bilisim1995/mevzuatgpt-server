#!/usr/bin/env python3
"""
Create missing tables using direct database connection
"""
import os
import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_missing_tables():
    """Create missing tables via direct PostgreSQL connection"""
    try:
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment variable not found")
            return False
            
        logger.info(f"Connecting to database: {database_url[:50]}...")
        
        # Connect to database
        conn = await asyncpg.connect(database_url)
        
        try:
            # Check current database
            db_name = await conn.fetchval("SELECT current_database();")
            logger.info(f"Connected to database: {db_name}")
            
            # Read SQL file
            with open('create_missing_tables.sql', 'r', encoding='utf-8') as f:
                sql_commands = f.read()
            
            # Execute SQL commands
            logger.info("Executing table creation SQL...")
            await conn.execute(sql_commands)
            
            logger.info("✅ All tables created successfully!")
            
            # Verify tables were created
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                    AND table_name IN ('ai_prompts', 'support_tickets', 'user_credits', 'credit_transactions')
                ORDER BY table_name;
            """)
            
            if tables:
                logger.info(f"✅ Verified tables created: {[t['table_name'] for t in tables]}")
            else:
                logger.warning("⚠️ No tables found after creation")
                
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False

async def main():
    """Main function"""
    logger.info("🚀 Creating missing Supabase tables...")
    success = await create_missing_tables()
    
    if success:
        logger.info("🎉 Database setup completed successfully!")
    else:
        logger.error("❌ Database setup failed!")

if __name__ == "__main__":
    asyncio.run(main())