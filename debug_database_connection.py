#!/usr/bin/env python3
"""
Debug Database Connection Issues
Test different URL encodings and connection methods
"""

import asyncio
import asyncpg
import os
import urllib.parse

async def test_connection_variations():
    """Test different connection string variations"""
    
    original_url = os.getenv('DATABASE_URL', '')
    
    if not original_url:
        print("❌ No DATABASE_URL found")
        return
    
    print("🔍 Testing Database Connection Variations")
    print("=" * 50)
    
    # Parse original URL
    parsed = urllib.parse.urlparse(original_url)
    
    print(f"Original URL: {original_url}")
    print(f"Host: {parsed.hostname}")
    print(f"Port: {parsed.port}")
    print(f"Database: {parsed.path[1:] if parsed.path else ''}")
    print(f"User: {parsed.username}")
    print(f"Password: {'*' * len(parsed.password) if parsed.password else 'None'}")
    print()
    
    # Test variations
    variations = []
    
    if parsed.password:
        # Original encoded password
        variations.append({
            'name': 'Original (current)',
            'password': parsed.password
        })
        
        # URL decoded password
        decoded_password = urllib.parse.unquote(parsed.password)
        variations.append({
            'name': 'URL-decoded password',
            'password': decoded_password
        })
        
        # Manual encoding fixes for common issues
        if '@' in decoded_password:
            manually_encoded = decoded_password.replace('@', '%40')
            variations.append({
                'name': 'Manual @ encoding',
                'password': manually_encoded
            })
        
        # Test with different encoding
        double_encoded = urllib.parse.quote(parsed.password, safe='')
        variations.append({
            'name': 'Double encoded',
            'password': double_encoded
        })
    
    # Test each variation
    for i, variation in enumerate(variations, 1):
        print(f"🧪 Test {i}: {variation['name']}")
        
        try:
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:] if parsed.path else 'postgres',
                user=parsed.username,
                password=variation['password']
            )
            
            # Test basic query
            version = await conn.fetchval('SELECT version();')
            print(f"  ✅ SUCCESS! Connected with password: {variation['password'][:10]}...")
            print(f"      PostgreSQL version: {version[:50]}...")
            
            await conn.close()
            
            # If successful, show the corrected URL
            corrected_url = f"postgresql://{parsed.username}:{urllib.parse.quote(variation['password'], safe='')}@{parsed.hostname}:{parsed.port or 5432}/{parsed.path[1:] if parsed.path else 'postgres'}"
            print(f"  ✅ Working DATABASE_URL:")
            print(f"      {corrected_url}")
            break
            
        except Exception as e:
            print(f"  ❌ FAILED: {str(e)}")
        
        print()

async def test_infrastructure_status():
    """Test if infrastructure team made any changes"""
    print("🏗️ Infrastructure Status Check")
    print("=" * 50)
    
    import aiohttp
    
    # Test PostgREST status
    supabase_url = os.getenv('SUPABASE_URL', '')
    supabase_key = os.getenv('SUPABASE_KEY', '')
    
    if supabase_url and supabase_key:
        try:
            async with aiohttp.ClientSession() as session:
                headers = {'apikey': supabase_key}
                
                async with session.get(f"{supabase_url}/rest/v1/", headers=headers) as response:
                    status = response.status
                    text = await response.text()
                    
                    print(f"PostgREST Status: {status}")
                    
                    if status == 503 and 'PGRST002' in text:
                        print("❌ PostgREST schema cache issue still exists")
                        print("💡 Infrastructure team needs to restart PostgREST")
                    elif status == 200:
                        print("✅ PostgREST is working!")
                        print("🎉 Infrastructure team fixed the issue!")
                    else:
                        print(f"⚠️  Unexpected status: {text[:100]}...")
                        
        except Exception as e:
            print(f"❌ Infrastructure test failed: {e}")

async def suggest_password_fix():
    """Suggest password encoding fix"""
    print("🔧 Password Encoding Fix Suggestion")
    print("=" * 50)
    
    db_url = os.getenv('DATABASE_URL', '')
    
    if '@' in db_url:
        # Find the password part and suggest fix
        parsed = urllib.parse.urlparse(db_url)
        if parsed.password and '@' in urllib.parse.unquote(parsed.password):
            decoded_password = urllib.parse.unquote(parsed.password)
            correct_password = urllib.parse.quote(decoded_password, safe='')
            
            correct_url = f"postgresql://{parsed.username}:{correct_password}@{parsed.hostname}:{parsed.port or 5432}/{parsed.path[1:] if parsed.path else 'postgres'}"
            
            print("❗ Password contains @ symbol - needs proper encoding")
            print("Current password issue detected")
            print()
            print("🔧 Suggested fix:")
            print(f"Original password (decoded): {decoded_password}")
            print(f"Properly encoded password: {correct_password}")
            print()
            print("📝 Corrected DATABASE_URL:")
            print(f"{correct_url}")
            print()
            print("💡 Update your .env file with the corrected URL above")

async def main():
    """Main function"""
    await test_infrastructure_status()
    print()
    await suggest_password_fix()
    print()
    await test_connection_variations()

if __name__ == "__main__":
    asyncio.run(main())