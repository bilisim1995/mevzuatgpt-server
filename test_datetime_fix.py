"""
Test datetime serialization fix
"""

import requests
import json


def test_search_history_with_real_token():
    """Test with browser token from logs"""
    
    base_url = "http://localhost:5000"
    
    # Use token from browser logs (expires soon but good for testing)
    token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjdjOWJlODE1LWE2ZGMtNGJiMi1hZjU5LTFkNzY5NTRmMjcyMyIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzM2NjEzMzI3LCJpYXQiOjE3MzY2MDk3MjcsImlzcyI6Imh0dHBzOi8vb211YmxxZGVlcmJzemtudXZvaW0uc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6IjBkZWE0MTUxLTlhYjktNDUzZS04ZWY5LTJiYjk0NjQ5Y2MxNiIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IjBkZWE0MTUxLTlhYjktNDUzZS04ZWY5LTJiYjk0NjQ5Y2MxNiJ9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzM2NjA5NzI3fV0sInNlc3Npb25faWQiOiI3NGRjMmI0OS1iNmUzLTQwYzEtOWQ4MC1lNzhmYzZjOWNkZmYiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.REDACTED"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print("Testing Search History Endpoints After DateTime Fix")
    print("=" * 60)
    
    # Test 1: Search History Stats
    print("1. Testing /api/user/search-history/stats...")
    try:
        stats_response = requests.get(f"{base_url}/api/user/search-history/stats", headers=headers)
        print(f"   Status: {stats_response.status_code}")
        
        if stats_response.status_code == 200:
            print("   ✓ Stats endpoint working")
            stats_data = stats_response.json()
            print(f"   Total searches: {stats_data.get('data', {}).get('total_searches', 0)}")
        else:
            print(f"   ✗ Stats failed: {stats_response.text}")
    except Exception as e:
        print(f"   ✗ Request error: {e}")
    
    # Test 2: Search History Listing (main test for datetime fix)
    print("\n2. Testing /api/user/search-history (datetime serialization)...")
    try:
        history_response = requests.get(f"{base_url}/api/user/search-history?page=1&limit=3", headers=headers)
        print(f"   Status: {history_response.status_code}")
        
        if history_response.status_code == 200:
            print("   ✓ Search history endpoint working!")
            history_data = history_response.json()
            
            total = history_data.get('data', {}).get('total_count', 0)
            items = history_data.get('data', {}).get('items', [])
            
            print(f"   Total items: {total}")
            print(f"   Retrieved items: {len(items)}")
            
            if items:
                first_item = items[0]
                print(f"   First query: '{first_item.get('query', 'N/A')}'")
                print(f"   Created at: {first_item.get('created_at', 'N/A')}")
                print("   ✓ Datetime serialization working!")
            else:
                print("   No items in history")
                
        else:
            print(f"   ✗ History failed: {history_response.text}")
            
    except Exception as e:
        print(f"   ✗ Request error: {e}")
    
    # Test 3: With filters
    print("\n3. Testing with filters...")
    try:
        filtered_response = requests.get(
            f"{base_url}/api/user/search-history?institution=SGK&limit=2", 
            headers=headers
        )
        print(f"   Status: {filtered_response.status_code}")
        
        if filtered_response.status_code == 200:
            print("   ✓ Filtered search working")
            filtered_data = filtered_response.json()
            total = filtered_data.get('data', {}).get('total_count', 0)
            print(f"   SGK filtered results: {total}")
        else:
            print(f"   ✗ Filtered search failed: {filtered_response.text}")
    except Exception as e:
        print(f"   ✗ Request error: {e}")
    
    print("\n" + "=" * 60)
    print("DateTime Serialization Fix Test Complete")


if __name__ == "__main__":
    test_search_history_with_real_token()