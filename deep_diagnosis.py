#!/usr/bin/env python3
"""
Deep Diagnosis of PostgREST Schema Cache Issue
Advanced troubleshooting for PGRST002 error
"""

import asyncio
import aiohttp
import asyncpg
import os
import urllib.parse

async def diagnose_postgrest_issue():
    """Advanced PostgREST diagnosis"""
    print("🔬 PostgREST Advanced Diagnosis")
    print("=" * 50)
    
    supabase_url = os.getenv('SUPABASE_URL', '')
    supabase_key = os.getenv('SUPABASE_KEY', '')
    
    # Test different endpoints
    endpoints_to_test = [
        {'path': '/', 'name': 'Root endpoint'},
        {'path': '/rest/v1/', 'name': 'REST API root'},
        {'path': '/rest/v1/rpc/version', 'name': 'Version RPC'},
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints_to_test:
            try:
                url = f"{supabase_url}{endpoint['path']}"
                headers = {'apikey': supabase_key, 'Content-Type': 'application/json'}
                
                async with session.get(url, headers=headers, timeout=10) as response:
                    status = response.status
                    text = await response.text()
                    
                    print(f"{endpoint['name']}: HTTP {status}")
                    
                    if status == 503 and 'PGRST002' in text:
                        print("  ❌ Schema cache issue confirmed")
                        # Extract more details
                        if 'Could not query the database' in text:
                            print("  💡 PostgREST cannot connect to database")
                    elif status == 200:
                        print("  ✅ Working!")
                        print(f"  Response: {text[:100]}...")
                    else:
                        print(f"  ⚠️  Status {status}: {text[:100]}...")
                        
            except Exception as e:
                print(f"{endpoint['name']}: ❌ Error: {e}")
            
            print()

async def test_database_permissions():
    """Test database permissions and roles"""
    print("🔐 Database Permissions Analysis")
    print("=" * 50)
    
    # Use the debug connection method we found working
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url:
        print("❌ No DATABASE_URL")
        return
        
    parsed = urllib.parse.urlparse(db_url)
    
    try:
        # Use URL-decoded password (we found this works)
        decoded_password = urllib.parse.unquote(parsed.password)
        
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:] if parsed.path else 'postgres',
            user=parsed.username,
            password=decoded_password
        )
        
        print("✅ Database connection successful with URL-decoded password")
        
        # Check roles that PostgREST needs
        roles_to_check = ['anon', 'authenticated', 'authenticator', 'service_role']
        
        print("\n🔍 Checking PostgREST roles:")
        for role in roles_to_check:
            try:
                role_exists = await conn.fetchval(
                    "SELECT 1 FROM pg_roles WHERE rolname = $1", role
                )
                if role_exists:
                    print(f"  ✅ Role '{role}' exists")
                else:
                    print(f"  ❌ Role '{role}' missing")
            except Exception as e:
                print(f"  ❌ Role check failed for '{role}': {e}")
        
        # Check schema permissions
        print("\n🔍 Schema permissions:")
        try:
            schemas = await conn.fetch("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name IN ('public', 'auth', 'storage')
            """)
            for schema in schemas:
                print(f"  ✅ Schema '{schema['schema_name']}' exists")
        except Exception as e:
            print(f"  ❌ Schema check failed: {e}")
        
        # Check if tables exist
        print("\n🔍 Application tables:")
        app_tables = ['user_profiles', 'documents', 'embeddings', 'search_history']
        for table in app_tables:
            try:
                table_exists = await conn.fetchval("""
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                """, table)
                if table_exists:
                    print(f"  ✅ Table '{table}' exists")
                else:
                    print(f"  ❌ Table '{table}' missing - migration needed")
            except Exception as e:
                print(f"  ❌ Table check failed for '{table}': {e}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        
        # Try with original encoded password
        try:
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:] if parsed.path else 'postgres',
                user=parsed.username,
                password=parsed.password
            )
            print("✅ Database connection successful with original encoded password")
            await conn.close()
        except Exception as e2:
            print(f"❌ Both password variants failed: {e2}")

def generate_fix_commands():
    """Generate specific fix commands for infrastructure team"""
    print("🔧 Infrastructure Team Fix Commands")
    print("=" * 50)
    
    commands = [
        {
            'title': 'PostgREST Container Logs',
            'command': 'docker logs supabase-rest --tail 50',
            'description': 'Check for specific error messages'
        },
        {
            'title': 'Database Password Fix',
            'command': 'docker exec -it supabase-db psql -U postgres -c "ALTER USER postgres PASSWORD \'ObMevzuat@2025Pas\';"',
            'description': 'Ensure password matches our expectation'
        },
        {
            'title': 'PostgREST Environment Check',
            'command': 'docker exec supabase-rest env | grep PGRST',
            'description': 'Check PostgREST environment variables'
        },
        {
            'title': 'PostgREST Configuration Test',
            'command': 'docker exec supabase-rest postgrest --help',
            'description': 'Test if PostgREST binary is working'
        },
        {
            'title': 'Database Connection from PostgREST Container',
            'command': 'docker exec supabase-rest pg_isready -h db.supabase.mevzuatgpt.org -p 5432 -U postgres',
            'description': 'Test DB connection from PostgREST container'
        },
        {
            'title': 'Recreate PostgREST Container',
            'command': 'docker-compose stop rest && docker-compose up -d rest',
            'description': 'Complete PostgREST container recreation'
        }
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"{i}️⃣ {cmd['title']}:")
        print(f"   {cmd['command']}")
        print(f"   💡 {cmd['description']}")
        print()

async def main():
    """Main diagnosis function"""
    print("🚀 Self-hosted Supabase Deep Diagnosis")
    print("=" * 60)
    print()
    
    await diagnose_postgrest_issue()
    print()
    await test_database_permissions()
    print()
    generate_fix_commands()
    
    print("🎯 Summary:")
    print("- PostgREST schema cache issue persists after restart")
    print("- Database connection works with URL-decoded password")
    print("- May need PostgREST configuration or role setup")
    print("- Infrastructure team should check PostgREST logs")

if __name__ == "__main__":
    asyncio.run(main())