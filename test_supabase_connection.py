#!/usr/bin/env python3
"""
Supabase Self-hosted Connection Test Script
Tests all components of self-hosted Supabase infrastructure
"""

import asyncio
import asyncpg
import aiohttp
import os
import sys
import urllib.parse
import json
from datetime import datetime
from typing import Dict, Any, Optional

class SupabaseConnectionTester:
    def __init__(self):
        """Initialize with environment variables or manual configuration"""
        # Get environment variables
        self.supabase_url = os.getenv('SUPABASE_URL', 'https://supabase.mevzuatgpt.org')
        self.supabase_key = os.getenv('SUPABASE_KEY', '')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY', '')
        self.database_url = os.getenv('DATABASE_URL', '')
        self.jwt_secret = os.getenv('JWT_SECRET_KEY', '')
        
        # Parse database URL
        self.db_config = self._parse_database_url()
        
        # Test results
        self.results = {}
        
    def _parse_database_url(self) -> Optional[Dict[str, Any]]:
        """Parse DATABASE_URL into components"""
        if not self.database_url:
            return None
            
        try:
            parsed = urllib.parse.urlparse(self.database_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:] if parsed.path else 'postgres',
                'user': parsed.username,
                'password': parsed.password
            }
        except Exception as e:
            print(f"❌ Database URL parsing failed: {e}")
            return None
    
    def print_configuration(self):
        """Print current configuration"""
        print("🔧 Current Configuration:")
        print("=" * 50)
        print(f"SUPABASE_URL: {self.supabase_url}")
        print(f"SUPABASE_KEY: {'Set' if self.supabase_key else 'Missing'} ({len(self.supabase_key)} chars)")
        print(f"SUPABASE_SERVICE_KEY: {'Set' if self.supabase_service_key else 'Missing'} ({len(self.supabase_service_key)} chars)")
        print(f"JWT_SECRET_KEY: {'Set' if self.jwt_secret else 'Missing'} ({len(self.jwt_secret)} chars)")
        print(f"DATABASE_URL: {'Set' if self.database_url else 'Missing'}")
        
        if self.db_config:
            print(f"  Host: {self.db_config['host']}")
            print(f"  Port: {self.db_config['port']}")
            print(f"  Database: {self.db_config['database']}")
            print(f"  User: {self.db_config['user']}")
            print(f"  Password: {'*' * len(self.db_config['password']) if self.db_config['password'] else 'None'}")
        print()
    
    async def test_dns_resolution(self) -> bool:
        """Test DNS resolution for Supabase domains"""
        print("🌐 Testing DNS Resolution...")
        
        domains_to_test = []
        
        # Extract domain from SUPABASE_URL
        if self.supabase_url:
            try:
                parsed = urllib.parse.urlparse(self.supabase_url)
                domains_to_test.append(parsed.hostname)
            except:
                pass
        
        # Extract database host
        if self.db_config and self.db_config['host']:
            domains_to_test.append(self.db_config['host'])
        
        all_resolved = True
        
        for domain in set(domains_to_test):  # Remove duplicates
            try:
                import socket
                result = socket.gethostbyname(domain)
                print(f"  ✅ {domain} → {result}")
                self.results[f'dns_{domain.replace(".", "_")}'] = True
            except Exception as e:
                print(f"  ❌ {domain} → Failed: {e}")
                self.results[f'dns_{domain.replace(".", "_")}'] = False
                all_resolved = False
        
        return all_resolved
    
    async def test_supabase_rest_api(self) -> bool:
        """Test Supabase REST API endpoint"""
        print("🔌 Testing Supabase REST API...")
        
        if not self.supabase_url or not self.supabase_key:
            print("  ❌ Missing SUPABASE_URL or SUPABASE_KEY")
            self.results['rest_api'] = False
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'apikey': self.supabase_key,
                    'Content-Type': 'application/json'
                }
                
                # Test root endpoint
                async with session.get(f"{self.supabase_url}/rest/v1/", headers=headers) as response:
                    if response.status == 200:
                        print(f"  ✅ REST API accessible (Status: {response.status})")
                        self.results['rest_api'] = True
                        return True
                    else:
                        text = await response.text()
                        print(f"  ⚠️  REST API responded with status {response.status}")
                        print(f"      Response: {text[:200]}...")
                        
                        # Check if it's a schema cache issue
                        if 'PGRST002' in text or 'schema cache' in text:
                            print("  ℹ️  This is a PostgREST schema cache issue - likely recoverable")
                            self.results['rest_api'] = 'cache_issue'
                            return False
                        else:
                            self.results['rest_api'] = False
                            return False
                            
        except Exception as e:
            print(f"  ❌ REST API test failed: {e}")
            self.results['rest_api'] = False
            return False
    
    async def test_database_connection(self) -> bool:
        """Test direct PostgreSQL database connection"""
        print("🗄️  Testing PostgreSQL Database...")
        
        if not self.db_config:
            print("  ❌ No database configuration available")
            self.results['database'] = False
            return False
        
        try:
            # Use URL-decoded password for actual connection (@ symbol issue)
            actual_password = urllib.parse.unquote(self.db_config['password'])
            conn = await asyncpg.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=actual_password
            )
            
            # Test basic query
            version = await conn.fetchval('SELECT version();')
            print(f"  ✅ Database connected successfully")
            print(f"      Version: {version[:50]}...")
            
            # Test if pgvector extension exists
            try:
                pgvector_check = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector');"
                )
                if pgvector_check:
                    print("  ✅ pgvector extension available")
                else:
                    print("  ⚠️  pgvector extension not found")
            except Exception as e:
                print(f"  ⚠️  pgvector check failed: {e}")
            
            # Test table access
            try:
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name
                    LIMIT 10
                """)
                print(f"  ✅ Found {len(tables)} tables in public schema")
                for table in tables[:5]:
                    print(f"      - {table['table_name']}")
                if len(tables) > 5:
                    print(f"      ... and {len(tables) - 5} more")
            except Exception as e:
                print(f"  ⚠️  Table listing failed: {e}")
            
            await conn.close()
            self.results['database'] = True
            return True
            
        except Exception as e:
            print(f"  ❌ Database connection failed: {e}")
            self.results['database'] = False
            return False
    
    async def test_supabase_auth(self) -> bool:
        """Test Supabase Auth service"""
        print("🔐 Testing Supabase Auth...")
        
        if not self.supabase_url or not self.supabase_key:
            print("  ❌ Missing SUPABASE_URL or SUPABASE_KEY")
            self.results['auth'] = False
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'apikey': self.supabase_key,
                    'Content-Type': 'application/json'
                }
                
                # Test auth endpoint
                async with session.get(f"{self.supabase_url}/auth/v1/user", headers=headers) as response:
                    if response.status in [200, 401]:  # 401 is expected without valid token
                        print(f"  ✅ Auth service accessible (Status: {response.status})")
                        self.results['auth'] = True
                        return True
                    else:
                        text = await response.text()
                        print(f"  ❌ Auth service failed (Status: {response.status})")
                        print(f"      Response: {text[:200]}...")
                        self.results['auth'] = False
                        return False
                        
        except Exception as e:
            print(f"  ❌ Auth test failed: {e}")
            self.results['auth'] = False
            return False
    
    async def test_table_access(self) -> bool:
        """Test access to specific application tables"""
        print("📋 Testing Application Tables...")
        
        if not self.supabase_url or not self.supabase_key:
            print("  ❌ Missing credentials")
            self.results['tables'] = False
            return False
        
        tables_to_test = [
            'user_profiles',
            'documents', 
            'embeddings',
            'search_history'
        ]
        
        accessible_tables = 0
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'apikey': self.supabase_key,
                    'Content-Type': 'application/json'
                }
                
                for table in tables_to_test:
                    try:
                        url = f"{self.supabase_url}/rest/v1/{table}?select=count&limit=1"
                        async with session.get(url, headers=headers) as response:
                            if response.status == 200:
                                print(f"  ✅ {table} table accessible")
                                accessible_tables += 1
                            else:
                                text = await response.text()
                                print(f"  ❌ {table} table failed (Status: {response.status})")
                                if 'does not exist' in text:
                                    print(f"      Table doesn't exist - may need migration")
                                elif 'PGRST002' in text:
                                    print(f"      Schema cache issue")
                                    
                    except Exception as e:
                        print(f"  ❌ {table} test failed: {e}")
                
                success = accessible_tables > 0
                self.results['tables'] = success
                return success
                
        except Exception as e:
            print(f"  ❌ Table access test failed: {e}")
            self.results['tables'] = False
            return False
    
    def print_summary(self):
        """Print test summary and recommendations"""
        print("\n📊 Test Summary:")
        print("=" * 50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result is True)
        
        for test_name, result in self.results.items():
            status = "✅ PASS" if result is True else "⚠️  ISSUE" if result == 'cache_issue' else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        # Recommendations
        print("\n💡 Recommendations:")
        print("-" * 50)
        
        if not self.results.get('database', False):
            print("🔧 Database Issues:")
            print("   - Check DNS resolution for database host")
            print("   - Verify PostgreSQL is running and accessible")
            print("   - Check firewall and network connectivity")
            print("   - Verify credentials and permissions")
        
        if self.results.get('rest_api') == 'cache_issue':
            print("🔧 PostgREST Schema Cache Issues:")
            print("   - Restart PostgREST service")
            print("   - Check database schema and migrations")
            print("   - Verify RLS policies are not causing conflicts")
        
        if not self.results.get('auth', False):
            print("🔧 Auth Service Issues:")
            print("   - Check if auth service is running")
            print("   - Verify JWT configuration")
            print("   - Check service dependencies")
        
        if not self.results.get('tables', False):
            print("🔧 Table Access Issues:")
            print("   - Run database migrations")
            print("   - Check RLS policies")
            print("   - Verify user permissions")
    
    async def run_all_tests(self):
        """Run all connectivity tests"""
        print(f"🚀 Starting Supabase Connection Tests - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        self.print_configuration()
        
        # Run tests in logical order
        await self.test_dns_resolution()
        print()
        
        await self.test_database_connection()
        print()
        
        await self.test_supabase_rest_api()
        print()
        
        await self.test_supabase_auth()
        print()
        
        await self.test_table_access()
        print()
        
        self.print_summary()

def manual_config_mode():
    """Allow manual configuration of connection parameters"""
    print("🔧 Manual Configuration Mode")
    print("Enter your Supabase configuration:")
    print()
    
    supabase_url = input("SUPABASE_URL (e.g., https://supabase.mevzuatgpt.org): ").strip()
    supabase_key = input("SUPABASE_KEY (anon key): ").strip()
    supabase_service_key = input("SUPABASE_SERVICE_KEY (service_role key): ").strip()
    database_url = input("DATABASE_URL (full PostgreSQL URL): ").strip()
    jwt_secret = input("JWT_SECRET_KEY: ").strip()
    
    # Set environment variables
    os.environ['SUPABASE_URL'] = supabase_url
    os.environ['SUPABASE_KEY'] = supabase_key
    os.environ['SUPABASE_SERVICE_KEY'] = supabase_service_key
    os.environ['DATABASE_URL'] = database_url
    os.environ['JWT_SECRET_KEY'] = jwt_secret
    
    print("\n✅ Configuration set! Running tests...\n")

async def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--manual':
        manual_config_mode()
    
    tester = SupabaseConnectionTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())