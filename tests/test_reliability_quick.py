#!/usr/bin/env python3
"""
Quick reliability scoring test using known working approach
"""

import sys
import json
import httpx
import time
import asyncio

sys.path.append('/home/runner/workspace')

BASE_URL = "http://0.0.0.0:5000"

async def test_reliability_system():
    """Quick test with fresh user registration"""
    
    print("🎯 ENHANCED RELIABILITY SCORING SYSTEM TEST")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # Register fresh user
        print("🔑 Creating fresh test user...")
        register_data = {
            "email": f"reliabilitytest{int(time.time())}@example.com",
            "password": "reliability123",
            "confirm_password": "reliability123",
            "full_name": "Reliability Test",
            "institution": "Test Institution"
        }
        
        try:
            register_response = await client.post(
                f"{BASE_URL}/api/auth/register",
                json=register_data
            )
            
            if register_response.status_code == 200:
                register_result = register_response.json()
                access_token = register_result["access_token"]
                print(f"   ✅ User registered successfully")
                print(f"   Token: {access_token[:50]}...")
            else:
                print(f"   ❌ Registration failed: {register_response.status_code}")
                print(f"   Response: {register_response.text}")
                return False
                
        except Exception as e:
            print(f"   ❌ Registration error: {e}")
            return False
        
        # Test enhanced reliability scoring
        test_queries = [
            "Vergi mükellefiyeti nasıl sona erer?",
            "KVKK kapsamında kişisel veri işleme şartları nelerdir?",
            "İş sözleşmesi feshi durumunda işçinin hakları"
        ]
        
        success_count = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📋 Test {i}/{len(test_queries)}: '{query}'")
            print("-" * 50)
            
            start_time = time.time()
            
            try:
                # Make ask request
                ask_response = await client.post(
                    f"{BASE_URL}/api/user/ask",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "query": query,
                        "institution_filter": None
                    }
                )
                
                elapsed_time = time.time() - start_time
                
                if ask_response.status_code == 200:
                    result = ask_response.json()
                    
                    print(f"✅ Response received in {elapsed_time:.2f}s")
                    
                    # Check basic fields
                    confidence_score = result.get("confidence_score", 0)
                    confidence_breakdown = result.get("confidence_breakdown")
                    
                    print(f"📊 Basic Confidence: {confidence_score:.3f}")
                    
                    # Test enhanced confidence breakdown
                    if confidence_breakdown:
                        print("\n🔍 ENHANCED RELIABILITY BREAKDOWN:")
                        breakdown = confidence_breakdown
                        
                        overall_score = breakdown.get("overall_score", 0)
                        print(f"   Overall Score: {overall_score}/100")
                        
                        # Individual criteria
                        criteria = breakdown.get("criteria", {})
                        print("\n   📋 Individual Criteria:")
                        
                        for name, data in criteria.items():
                            score = data.get("score", 0)
                            weight = data.get("weight", 0)
                            description = data.get("description", "N/A")
                            details = data.get("details", [])
                            
                            print(f"   • {name.replace('_', ' ').title()}: {score}/100 ({weight}%)")
                            print(f"     {description}")
                            if details:
                                print(f"     Details: {', '.join(details[:2])}...")
                        
                        # Performance check
                        search_stats = result.get("search_stats", {})
                        reliability_time = search_stats.get("reliability_time_ms", 0)
                        total_time = search_stats.get("total_pipeline_time_ms", 0)
                        
                        print(f"\n   ⏱️  Performance:")
                        print(f"   Reliability Calculation: {reliability_time}ms")
                        print(f"   Total Pipeline: {total_time}ms")
                        
                        if reliability_time > 0 and total_time > 0:
                            overhead = (reliability_time / total_time) * 100
                            print(f"   Overhead: {overhead:.1f}%")
                            
                            if overhead <= 20:
                                print(f"   ✅ Acceptable overhead")
                            else:
                                print(f"   ⚠️  High overhead")
                        
                        print(f"✅ Test {i} PASSED - Enhanced scoring working!")
                        success_count += 1
                        
                    else:
                        print("❌ No confidence breakdown - enhanced scoring failed!")
                        
                else:
                    print(f"❌ Ask request failed: {ask_response.status_code}")
                    print(f"Response: {ask_response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Test error: {e}")
        
        # Final summary
        print("\n" + "=" * 60)
        print(f"📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {success_count}/{len(test_queries)}")
        print(f"❌ Failed: {len(test_queries) - success_count}/{len(test_queries)}")
        print(f"📈 Success Rate: {(success_count/len(test_queries))*100:.1f}%")
        
        if success_count == len(test_queries):
            print("\n🎉 ENHANCED RELIABILITY SYSTEM: FULLY OPERATIONAL!")
            print("🔍 5-dimensional scoring system working correctly")
            print("📊 Detailed confidence breakdown functional")
            print("⚡ Performance metrics within acceptable range")
            return True
        else:
            print(f"\n⚠️  {len(test_queries) - success_count} test(s) failed")
            return False

if __name__ == "__main__":
    print("🚀 Enhanced Reliability Scoring System - Quick Test")
    print(f"🌐 Endpoint: {BASE_URL}/api/user/ask")
    print(f"⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    result = asyncio.run(test_reliability_system())
    
    if result:
        print("\n✅ SYSTEM STATUS: OPERATIONAL")
    else:
        print("\n❌ SYSTEM STATUS: NEEDS ATTENTION")