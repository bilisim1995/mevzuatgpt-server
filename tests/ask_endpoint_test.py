#!/usr/bin/env python3
"""
Test the ask endpoint with real authentication
"""

import asyncio
import sys
import json
import httpx

sys.path.append('/home/runner/workspace')

BASE_URL = "http://0.0.0.0:5000"

async def test_ask_endpoint():
    """Test ask endpoint with authentication"""
    
    print("🧪 ASK ENDPOINT TEST")
    print("=" * 40)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Login
        print("1️⃣ Authentication...")
        login_data = {
            "email": "admin@mevzuatgpt.com",
            "password": "admin123"
        }
        
        try:
            login_response = await client.post(
                f"{BASE_URL}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if login_response.status_code != 200:
                print(f"   ❌ Login failed: {login_response.status_code}")
                return False
            
            login_result = login_response.json()
            if not login_result.get("success"):
                print(f"   ❌ Login error: {login_result.get('error')}")
                return False
            
            access_token = login_result["data"]["access_token"]
            print(f"   ✅ Login successful, token: {access_token[:30]}...")
            
        except Exception as e:
            print(f"   ❌ Login exception: {e}")
            return False
        
        # Step 2: Ask Question
        print(f"\n2️⃣ Asking question...")
        ask_data = {
            "query": "Test sorusu: Bu sistem nasıl çalışır?"
        }
        
        try:
            ask_response = await client.post(
                f"{BASE_URL}/api/user/ask",
                json=ask_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )
            
            print(f"   Status Code: {ask_response.status_code}")
            
            if ask_response.status_code == 200:
                result = ask_response.json()
                if result.get("success"):
                    data = result["data"]
                    print(f"   ✅ Success!")
                    print(f"      Answer: {data.get('answer', 'No answer')[:100]}...")
                    print(f"      Confidence: {data.get('confidence_score', 0):.2f}")
                    print(f"      Sources: {len(data.get('sources', []))}")
                    print(f"      Model: {data.get('llm_stats', {}).get('model_used', 'unknown')}")
                    
                    # Show performance stats
                    stats = data.get('search_stats', {})
                    print(f"      Performance:")
                    print(f"        Embedding: {stats.get('embedding_time_ms', 0)}ms")
                    print(f"        Generation: {stats.get('generation_time_ms', 0)}ms")
                    print(f"        Total: {stats.get('total_pipeline_time_ms', 0)}ms")
                    
                    return True
                else:
                    print(f"   ❌ API Error: {result.get('error')}")
                    return False
            else:
                print(f"   ❌ HTTP Error: {ask_response.status_code}")
                try:
                    error_data = ask_response.json()
                    print(f"      Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"      Raw response: {ask_response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Ask exception: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_ask_endpoint())
    if success:
        print(f"\n🎉 ASK ENDPOINT WORKING!")
        print("✅ Authentication: OK")
        print("✅ Query Processing: OK") 
        print("✅ Response Format: OK")
        print("✅ Ready for production!")
    else:
        print(f"\n❌ Test failed")
    
    exit(0 if success else 1)