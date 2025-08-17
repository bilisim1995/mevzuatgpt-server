#!/usr/bin/env python3
"""
Supabase Schema Cache Fix Script
Provides specific commands to fix PGRST002 schema cache issues
"""

import os
import asyncio

def print_fix_instructions():
    """Print step-by-step fix instructions for infrastructure team"""
    
    print("🔧 PostgREST Schema Cache Fix Instructions")
    print("=" * 60)
    print()
    
    print("📋 Problem: PGRST002 - Could not query the database for the schema cache")
    print("🎯 Solution: Restart services and refresh schema cache")
    print()
    
    print("🚀 Infrastructure Team Actions:")
    print("-" * 40)
    
    print("1️⃣ SSH to Supabase server:")
    print("   ssh user@supabase.mevzuatgpt.org")
    print()
    
    print("2️⃣ Check service status:")
    print("   sudo docker ps")
    print("   # Look for postgrest container")
    print()
    
    print("3️⃣ Restart PostgREST service:")
    print("   sudo docker restart supabase-postgrest")
    print("   # OR if using docker-compose:")
    print("   sudo docker-compose restart postgrest")
    print()
    
    print("4️⃣ Check PostgreSQL connection:")
    print("   sudo docker exec -it supabase-db psql -U postgres")
    print("   \\l  # List databases")
    print("   \\c postgres  # Connect to main database")
    print("   \\dt  # List tables")
    print("   \\q  # Exit")
    print()
    
    print("5️⃣ Force schema cache refresh:")
    print("   curl -X POST http://localhost:3000/rpc/reload_schema \\")
    print("        -H 'Content-Type: application/json'")
    print()
    
    print("6️⃣ Alternative - Full service restart:")
    print("   sudo docker-compose down")
    print("   sudo docker-compose up -d")
    print()
    
    print("7️⃣ Check PostgREST logs:")
    print("   sudo docker logs supabase-postgrest --tail 50")
    print()
    
    print("🔍 Common Causes & Solutions:")
    print("-" * 40)
    
    print("❓ RLS Policy Issues:")
    print("   - Check if Row Level Security policies are conflicting")
    print("   - Temporarily disable RLS: ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;")
    print()
    
    print("❓ Permission Issues:")
    print("   - Grant proper permissions to authenticator/anon roles")
    print("   - GRANT USAGE ON SCHEMA public TO anon, authenticated;")
    print()
    
    print("❓ Database Schema Issues:")
    print("   - Ensure tables exist and are properly created")
    print("   - Check for schema corruption")
    print()
    
    print("🧪 Test Commands After Fix:")
    print("-" * 40)
    
    db_url = os.getenv('DATABASE_URL', '')
    supabase_url = os.getenv('SUPABASE_URL', '')
    supabase_key = os.getenv('SUPABASE_KEY', '')
    
    if supabase_url and supabase_key:
        print("Test REST API:")
        print(f"curl -H 'apikey: {supabase_key[:20]}...' \\")
        print(f"     {supabase_url}/rest/v1/")
        print()
        
        print("Test table access:")
        print(f"curl -H 'apikey: {supabase_key[:20]}...' \\")
        print(f"     {supabase_url}/rest/v1/user_profiles?select=count")
        print()
    
    print("Re-run test script:")
    print("python test_supabase_connection.py")
    print()
    
    print("💡 Expected Result After Fix:")
    print("-" * 40)
    print("✅ Database: PASS")
    print("✅ REST API: PASS") 
    print("✅ Tables: PASS")
    print("🎯 All 6/6 tests should pass")

def generate_docker_compose_check():
    """Generate docker-compose.yml check commands"""
    print("\n🐳 Docker Compose Configuration Check:")
    print("-" * 50)
    
    print("Check if services are defined correctly:")
    print("cat docker-compose.yml | grep -A 10 postgrest")
    print()
    
    print("Typical PostgREST configuration should include:")
    print("""
postgrest:
  image: postgrest/postgrest:latest
  ports:
    - "3000:3000"
  environment:
    PGRST_DB_URI: postgresql://authenticator:your_password@db:5432/postgres
    PGRST_DB_SCHEMAS: public
    PGRST_DB_ANON_ROLE: anon
    PGRST_JWT_SECRET: your_jwt_secret
  depends_on:
    - db
""")

def create_health_check_script():
    """Create a health check script for regular monitoring"""
    
    script_content = '''#!/bin/bash
# Supabase Health Check Script - Run on server

echo "🏥 Supabase Health Check - $(date)"
echo "=================================="

# Check container status
echo "📦 Container Status:"
docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}" | grep supabase

echo ""

# Check PostgREST specifically
echo "🔌 PostgREST Health:"
POSTGREST_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/)
if [ "$POSTGREST_HEALTH" = "200" ]; then
    echo "✅ PostgREST responding (HTTP $POSTGREST_HEALTH)"
else
    echo "❌ PostgREST issues (HTTP $POSTGREST_HEALTH)"
fi

echo ""

# Check PostgreSQL
echo "🗄️ PostgreSQL Health:"
PG_HEALTH=$(docker exec supabase-db pg_isready -U postgres)
if [[ $PG_HEALTH == *"accepting connections"* ]]; then
    echo "✅ PostgreSQL accepting connections"
else
    echo "❌ PostgreSQL connection issues"
fi

echo ""

# Check auth service
echo "🔐 Auth Service Health:"
AUTH_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9999/health)
if [ "$AUTH_HEALTH" = "200" ]; then
    echo "✅ Auth service responding (HTTP $AUTH_HEALTH)"
else
    echo "❌ Auth service issues (HTTP $AUTH_HEALTH)"
fi

echo ""
echo "💡 If issues found, run: docker-compose restart"
'''
    
    with open('supabase_health_check.sh', 'w') as f:
        f.write(script_content)
    
    os.chmod('supabase_health_check.sh', 0o755)
    print("📝 Created: supabase_health_check.sh")
    print("Upload this to your server and run: ./supabase_health_check.sh")

async def main():
    """Main execution"""
    print_fix_instructions()
    generate_docker_compose_check()
    print()
    create_health_check_script()
    
    print("\n🎯 Summary for Infrastructure Team:")
    print("-" * 50)
    print("1. PostgREST schema cache needs refresh")
    print("2. DNS resolution is working ✅")
    print("3. Auth service is working ✅") 
    print("4. Database restart should fix the issue")
    print("5. All components are reachable")
    
    print("\n📞 Next Steps:")
    print("1. Share these instructions with infrastructure team")
    print("2. They restart PostgREST service")
    print("3. Re-run: python test_supabase_connection.py")
    print("4. Confirm all 6/6 tests pass")

if __name__ == "__main__":
    asyncio.run(main())