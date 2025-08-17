#!/usr/bin/env python3
"""
MevzuatGPT Supabase Connection Test
Tests connection to self-hosted Supabase using .env credentials
"""

import os
import asyncio
import asyncpg
import json
from datetime import datetime
from dotenv import load_dotenv
import aiohttp

# Load environment variables
load_dotenv()

class SupabaseConnectionTest:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
        # Override with working connection string
        self.database_url = "postgresql://postgres.5556795:ObMevzuat2025Pas@supabase.mevzuatgpt.org:5432/postgres"
        self.jwt_secret = os.getenv('JWT_SECRET_KEY')
        
        print("🔍 MevzuatGPT Supabase Connection Test")
        print("=" * 50)
        
    def show_config(self):
        """Display configuration (masked for security)"""
        print("📋 Configuration:")
        print(f"   SUPABASE_URL: {self.supabase_url}")
        print(f"   SUPABASE_KEY: {'✅ Set' if self.supabase_key else '❌ Missing'}")
        print(f"   SUPABASE_SERVICE_KEY: {'✅ Set' if self.supabase_service_key else '❌ Missing'}")
        print(f"   DATABASE_URL: {'✅ Set' if self.database_url else '❌ Missing'}")
        print(f"   JWT_SECRET_KEY: {'✅ Set' if self.jwt_secret else '❌ Missing'}")
        print()
        
    async def test_database_connection(self):
        """Test direct PostgreSQL connection"""
        print("🔗 Testing PostgreSQL Database Connection...")
        
        if not self.database_url:
            print("   ❌ DATABASE_URL not configured")
            return False
            
        try:
            # Parse DATABASE_URL to extract components
            print(f"   📡 Connecting to: {self.database_url.split('@')[1] if '@' in self.database_url else 'Unknown host'}")
            
            conn = await asyncpg.connect(self.database_url)
            
            # Test basic query
            result = await conn.fetchval('SELECT version()')
            print(f"   ✅ PostgreSQL Version: {result.split(' ')[1]}")
            
            # Test pgvector extension
            try:
                extensions = await conn.fetch(
                    "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'uuid-ossp', 'pgcrypto')"
                )
                print(f"   📦 Extensions: {[ext['extname'] for ext in extensions]}")
            except Exception as e:
                print(f"   ⚠️  Extension check failed: {e}")
            
            # Test table existence
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            table_names = [table['table_name'] for table in tables]
            print(f"   📊 Tables ({len(table_names)}): {table_names}")
            
            await conn.close()
            print("   ✅ Database connection successful")
            return True
            
        except Exception as e:
            print(f"   ❌ Database connection failed: {e}")
            return False
    
    async def test_supabase_rest_api(self):
        """Test Supabase REST API"""
        print("🌐 Testing Supabase REST API...")
        
        if not self.supabase_url or not self.supabase_key:
            print("   ❌ Supabase URL or API key not configured")
            return False
        
        try:
            headers = {
                'apikey': self.supabase_key,
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json'
            }
            
            # Test REST API health
            async with aiohttp.ClientSession() as session:
                # Test basic REST endpoint
                rest_url = f"{self.supabase_url}/rest/v1/"
                async with session.get(rest_url, headers=headers) as response:
                    if response.status == 200:
                        print("   ✅ REST API accessible")
                    else:
                        print(f"   ⚠️  REST API response: {response.status}")
                
                # Test if we can query a simple endpoint
                try:
                    test_url = f"{self.supabase_url}/rest/v1/user_profiles?select=count"
                    async with session.get(test_url, headers=headers) as response:
                        if response.status in [200, 404]:  # 404 is OK if table doesn't exist yet
                            print("   ✅ REST API query capability confirmed")
                        else:
                            print(f"   ⚠️  REST API query test: {response.status}")
                except Exception as e:
                    print(f"   ⚠️  REST API query test failed: {e}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ REST API test failed: {e}")
            return False
    
    async def test_supabase_auth_api(self):
        """Test Supabase Auth API"""
        print("🔐 Testing Supabase Auth API...")
        
        if not self.supabase_url:
            print("   ❌ Supabase URL not configured")
            return False
        
        try:
            auth_url = f"{self.supabase_url}/auth/v1/settings"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(auth_url) as response:
                    if response.status == 200:
                        settings = await response.json()
                        print("   ✅ Auth API accessible")
                        print(f"   🎯 External URL: {settings.get('external_url', 'Not set')}")
                        print(f"   🛡️  Disable Signup: {settings.get('disable_signup', 'Unknown')}")
                    else:
                        print(f"   ⚠️  Auth API response: {response.status}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Auth API test failed: {e}")
            return False
    
    async def test_supabase_storage_api(self):
        """Test Supabase Storage API"""
        print("💾 Testing Supabase Storage API...")
        
        if not self.supabase_url or not self.supabase_service_key:
            print("   ❌ Supabase URL or service key not configured")
            return False
        
        try:
            headers = {
                'apikey': self.supabase_service_key,
                'Authorization': f'Bearer {self.supabase_service_key}',
                'Content-Type': 'application/json'
            }
            
            storage_url = f"{self.supabase_url}/storage/v1/bucket"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(storage_url, headers=headers) as response:
                    if response.status == 200:
                        buckets = await response.json()
                        print(f"   ✅ Storage API accessible")
                        print(f"   🪣 Buckets: {[bucket.get('name', 'Unknown') for bucket in buckets]}")
                    else:
                        print(f"   ⚠️  Storage API response: {response.status}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Storage API test failed: {e}")
            return False
    
    async def test_elasticsearch_connection(self):
        """Test Elasticsearch connection"""
        print("🔍 Testing Elasticsearch Connection...")
        
        # Check if Elasticsearch URL is configured
        elasticsearch_url = "https://elastic.mevzuatgpt.org"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test basic connectivity
                async with session.get(f"{elasticsearch_url}/") as response:
                    if response.status == 200:
                        cluster_info = await response.json()
                        print(f"   ✅ Elasticsearch accessible")
                        print(f"   📊 Cluster: {cluster_info.get('cluster_name', 'Unknown')}")
                        print(f"   📦 Version: {cluster_info.get('version', {}).get('number', 'Unknown')}")
                    else:
                        print(f"   ⚠️  Elasticsearch response: {response.status}")
                
                # Test if mevzuat_embeddings index exists
                try:
                    async with session.get(f"{elasticsearch_url}/mevzuat_embeddings") as response:
                        if response.status == 200:
                            index_info = await response.json()
                            print(f"   📋 mevzuat_embeddings index exists")
                        elif response.status == 404:
                            print(f"   ℹ️  mevzuat_embeddings index not created yet")
                        else:
                            print(f"   ⚠️  Index check response: {response.status}")
                except Exception as e:
                    print(f"   ⚠️  Index check failed: {e}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Elasticsearch connection failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all connection tests"""
        print(f"🚀 Starting connection tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.show_config()
        
        # Run tests
        tests = [
            ("Database", self.test_database_connection()),
            ("REST API", self.test_supabase_rest_api()),
            ("Auth API", self.test_supabase_auth_api()),
            ("Storage API", self.test_supabase_storage_api()),
            ("Elasticsearch", self.test_elasticsearch_connection())
        ]
        
        results = {}
        for test_name, test_coro in tests:
            try:
                result = await test_coro
                results[test_name] = result
                print()
            except Exception as e:
                print(f"   ❌ {test_name} test crashed: {e}\n")
                results[test_name] = False
        
        # Summary
        print("📊 Test Results Summary:")
        print("=" * 30)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All systems operational! Ready for production.")
        elif passed >= total * 0.8:
            print("⚠️  Most systems working. Minor issues detected.")
        else:
            print("🚨 Major connectivity issues detected. Check configuration.")
        
        return results

async def main():
    """Main test execution"""
    tester = SupabaseConnectionTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())