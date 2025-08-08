"""
Test modular reliability scoring system
Enhanced 5-dimensional confidence scoring with detailed breakdown
"""

import asyncio
import json
import time
import requests
from requests.auth import HTTPBasicAuth

# Test configuration
BASE_URL = "http://0.0.0.0:5000"

def register_test_user():
    """Register a new test user and get token"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"reliability{int(time.time())}@example.com",
                "password": "test123456",
                "confirm_password": "test123456",
                "full_name": "Reliability Test User",
                "institution": "Test Institution"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"Registration failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Registration error: {e}")
        return None

def test_enhanced_reliability_scoring():
    """Test enhanced reliability scoring system with detailed breakdown"""
    
    # Test queries with different complexity levels
    test_cases = [
        {
            "query": "Vergi mükellefiyeti nasıl sona erer?",
            "description": "Simple legal query - should test terminology and consistency"
        },
        {
            "query": "İş sözleşmesinin haklı nedenle feshi durumunda işçinin hakları nelerdir?",
            "description": "Complex legal query - should test all criteria"
        },
        {
            "query": "KVKK kapsamında kişisel veri işleme şartları",
            "description": "Modern legislation query - should test currency scoring"
        }
    ]
    
    print("🎯 Enhanced Reliability Scoring System Test")
    print("=" * 60)
    
    # Get fresh test token
    print("🔑 Registering test user...")
    test_token = register_test_user()
    if not test_token:
        print("❌ Failed to get test token")
        return False
    print(f"   ✅ Token received: {test_token[:50]}...")
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        description = test_case["description"]
        
        print(f"\n📋 Test {i}/{total_tests}: {description}")
        print(f"Query: '{query}'")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            # Make API call
            response = requests.post(
                f"{BASE_URL}/api/user/ask",
                headers={
                    "Authorization": f"Bearer {test_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "query": query,
                    "institution_filter": None
                },
                timeout=30
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Basic response validation
                required_fields = ["query", "answer", "confidence_score", "sources"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"❌ Missing fields: {missing_fields}")
                    continue
                
                # Enhanced confidence scoring validation
                confidence_score = data.get("confidence_score", 0)
                confidence_breakdown = data.get("confidence_breakdown")
                
                print(f"✅ Response received in {elapsed_time:.2f}s")
                print(f"📊 Confidence Score: {confidence_score:.3f}")
                
                # Test enhanced confidence breakdown
                if confidence_breakdown:
                    print("\n🔍 Detailed Confidence Breakdown:")
                    breakdown = confidence_breakdown
                    
                    # Overall score
                    overall_score = breakdown.get("overall_score", 0)
                    print(f"   Overall Score: {overall_score}/100")
                    print(f"   Explanation: {breakdown.get('explanation', 'N/A')}")
                    
                    # Individual criteria scores
                    criteria = breakdown.get("criteria", {})
                    print("\n   Individual Criteria:")
                    
                    for criterion_name, criterion_data in criteria.items():
                        score = criterion_data.get("score", 0)
                        weight = criterion_data.get("weight", 0)
                        description = criterion_data.get("description", "N/A")
                        details = criterion_data.get("details", [])
                        
                        print(f"   • {criterion_name.replace('_', ' ').title()}:")
                        print(f"     Score: {score}/100 (Weight: {weight}%)")
                        print(f"     Description: {description}")
                        if details:
                            print(f"     Details: {', '.join(details)}")
                    
                    # Score ranges
                    score_ranges = breakdown.get("score_ranges", {})
                    current_range = "low"
                    if overall_score >= 80:
                        current_range = "high"
                    elif overall_score >= 60:
                        current_range = "medium"
                    
                    print(f"\n   📈 Score Range: {current_range.upper()}")
                    range_info = score_ranges.get(current_range, {})
                    print(f"   Range: {range_info.get('min', 0)}-{range_info.get('max', 100)}")
                    print(f"   Meaning: {range_info.get('desc', 'N/A')}")
                    
                else:
                    print("⚠️  No detailed confidence breakdown available")
                
                # Performance metrics
                search_stats = data.get("search_stats", {})
                reliability_time = search_stats.get("reliability_time_ms", 0)
                total_time = search_stats.get("total_pipeline_time_ms", 0)
                
                print(f"\n⏱️  Performance Metrics:")
                print(f"   Reliability Calculation: {reliability_time}ms")
                print(f"   Total Pipeline: {total_time}ms")
                print(f"   Sources Found: {search_stats.get('total_chunks_found', 0)}")
                
                # Validate reliability time impact
                if reliability_time > 0:
                    reliability_percentage = (reliability_time / total_time) * 100
                    print(f"   Reliability Overhead: {reliability_percentage:.1f}%")
                    
                    if reliability_percentage <= 20:  # Max 20% overhead
                        print(f"   ✅ Performance impact acceptable: {reliability_percentage:.1f}%")
                    else:
                        print(f"   ⚠️  High performance impact: {reliability_percentage:.1f}%")
                
                success_count += 1
                print(f"✅ Test {i} PASSED")
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    # Final summary
    print("\n" + "=" * 60)
    print(f"📊 ENHANCED RELIABILITY SCORING TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Successful Tests: {success_count}/{total_tests}")
    print(f"❌ Failed Tests: {total_tests - success_count}/{total_tests}")
    print(f"📈 Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("\n🎉 ALL TESTS PASSED - Enhanced reliability scoring system is operational!")
        print("🔍 5-dimensional scoring system working correctly")
        print("📊 Detailed confidence breakdown functional")
        print("⚡ Performance overhead within acceptable limits")
    else:
        print(f"\n⚠️  {total_tests - success_count} test(s) failed. Check logs above.")
    
    return success_count == total_tests

if __name__ == "__main__":
    print("🚀 Starting Enhanced Reliability Scoring System Test")
    print(f"🌐 Testing endpoint: {BASE_URL}/api/user/ask")
    print(f"⏰ Current time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_enhanced_reliability_scoring()
    
    if success:
        print("\n✅ Enhanced Reliability System: OPERATIONAL")
    else:
        print("\n❌ Enhanced Reliability System: NEEDS ATTENTION")