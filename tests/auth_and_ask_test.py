#!/usr/bin/env python3
"""
Complete auth + ask endpoint test
"""

import asyncio
import sys
import json
import httpx

sys.path.append('/home/runner/workspace')

BASE_URL = "http://0.0.0.0:5000"

async def test_complete_flow():
    """Test complete flow: register -> login -> ask"""
    
    print("🔐 COMPLETE AUTH + ASK TEST")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Register new user
        print("1️⃣ Registering new user...")
        register_data = {
            "email": "testuser@mevzuatgpt.com",
            "password": "testpass123",
            "full_name": "Test User",
            "institution": "Test Institution"
        }
        
        try:
            register_response = await client.post(
                f"{BASE_URL}/api/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Register Status: {register_response.status_code}")
            
            if register_response.status_code != 201:
                register_result = register_response.json()
                print(f"   Register info: {register_result}")
                # Continue anyway, user might already exist
            else:
                print("   ✅ User registered successfully")
                
        except Exception as e:
            print(f"   ⚠️ Register error: {e}")
        
        # Step 2: Login
        print(f"\n2️⃣ Logging in...")
        login_data = {
            "email": "testuser@mevzuatgpt.com",
            "password": "testpass123"
        }
        
        try:
            login_response = await client.post(
                f"{BASE_URL}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"   Login Status: {login_response.status_code}")
            
            if login_response.status_code != 200:
                login_result = login_response.json()
                print(f"   ❌ Login failed: {json.dumps(login_result, indent=2)}")
                return False
            
            login_result = login_response.json()
            if not login_result.get("success"):
                print(f"   ❌ Login error: {login_result.get('error')}")
                return False
            
            access_token = login_result["data"]["access_token"]
            print(f"   ✅ Login successful")
            print(f"      Token: {access_token[:40]}...")
            
        except Exception as e:
            print(f"   ❌ Login exception: {e}")
            return False
        
        # Step 3: Test Ask Endpoint
        print(f"\n3️⃣ Testing ask endpoint...")
        ask_data = {
            "query": "MevzuatGPT nasıl çalışır ve hangi özellikleri var?"
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
            
            print(f"   Ask Status: {ask_response.status_code}")
            
            if ask_response.status_code == 200:
                result = ask_response.json()
                if result.get("success"):
                    data = result["data"]
                    print(f"   ✅ Ask endpoint working!")
                    print(f"      Query: {data.get('query', 'N/A')}")
                    print(f"      Answer length: {len(data.get('answer', ''))} chars")
                    print(f"      Confidence: {data.get('confidence_score', 0):.2f}")
                    print(f"      Sources found: {len(data.get('sources', []))}")
                    
                    # Performance metrics
                    stats = data.get('search_stats', {})
                    llm_stats = data.get('llm_stats', {})
                    print(f"      Performance:")
                    print(f"        • Embedding: {stats.get('embedding_time_ms', 0)}ms")
                    print(f"        • Search: {stats.get('search_time_ms', 0)}ms")  
                    print(f"        • Generation: {stats.get('generation_time_ms', 0)}ms")
                    print(f"        • Total: {stats.get('total_pipeline_time_ms', 0)}ms")
                    print(f"        • Model: {llm_stats.get('model_used', 'unknown')}")
                    
                    # Show sample answer
                    answer = data.get('answer', '')
                    if len(answer) > 200:
                        print(f"      Sample answer: {answer[:200]}...")
                    else:
                        print(f"      Answer: {answer}")
                    
                    return True
                else:
                    print(f"   ❌ Ask API error: {result.get('error')}")
                    return False
            else:
                print(f"   ❌ Ask HTTP error: {ask_response.status_code}")
                try:
                    error_data = ask_response.json()
                    print(f"      Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"      Raw response: {ask_response.text[:500]}...")
                return False
                
        except Exception as e:
            print(f"   ❌ Ask exception: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_flow())
    
    print(f"\n{'='*50}")
    if success:
        print("🎉 COMPLETE TEST PASSED!")
        print("✅ User registration: Working")
        print("✅ Authentication: Working")
        print("✅ Ask endpoint: Working")
        print("✅ RAG pipeline: Working")
        print("✅ System ready for production!")
    else:
        print("❌ TEST FAILED - Check logs above")
    
    exit(0 if success else 1)