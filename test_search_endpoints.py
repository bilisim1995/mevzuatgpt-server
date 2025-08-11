"""
Test script for search history endpoints
"""

import requests
import json
import sys


def test_search_endpoints():
    """Test search history endpoints with real authentication"""
    
    base_url = "http://localhost:5000"
    
    print("🔍 Testing Search History Endpoints")
    print("=" * 50)
    
    # Step 1: Login to get valid token
    print("1. Getting authentication token...")
    try:
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpass123"
            }
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            print("✓ Login successful")
        else:
            print(f"✗ Login failed: {login_response.status_code}")
            print(login_response.text)
            return
            
    except Exception as e:
        print(f"✗ Login request failed: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Test search history stats
    print("\n2. Testing GET /api/user/search-history/stats...")
    try:
        stats_response = requests.get(
            f"{base_url}/api/user/search-history/stats",
            headers=headers
        )
        
        print(f"Status: {stats_response.status_code}")
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print("✓ Stats retrieved successfully")
            print(f"Response: {json.dumps(stats_data, indent=2)}")
        else:
            print(f"✗ Stats failed: {stats_response.text}")
            
    except Exception as e:
        print(f"✗ Stats request failed: {e}")
    
    # Step 3: Test search history listing
    print("\n3. Testing GET /api/user/search-history...")
    try:
        history_response = requests.get(
            f"{base_url}/api/user/search-history?page=1&limit=5",
            headers=headers
        )
        
        print(f"Status: {history_response.status_code}")
        if history_response.status_code == 200:
            history_data = history_response.json()
            print("✓ Search history retrieved successfully")
            print(f"Total items: {history_data.get('data', {}).get('total_count', 0)}")
            
            items = history_data.get('data', {}).get('items', [])
            if items:
                print(f"First item query: '{items[0].get('query', 'N/A')}'")
            else:
                print("No search history items found")
                
        else:
            print(f"✗ History failed: {history_response.text}")
            
    except Exception as e:
        print(f"✗ History request failed: {e}")
    
    # Step 4: Test with filters
    print("\n4. Testing with filters...")
    try:
        filtered_response = requests.get(
            f"{base_url}/api/user/search-history?institution=SGK&limit=3",
            headers=headers
        )
        
        print(f"Status: {filtered_response.status_code}")
        if filtered_response.status_code == 200:
            filtered_data = filtered_response.json()
            print("✓ Filtered search successful")
            total = filtered_data.get('data', {}).get('total_count', 0)
            print(f"SGK filtered results: {total}")
        else:
            print(f"✗ Filtered search failed: {filtered_response.text}")
            
    except Exception as e:
        print(f"✗ Filtered request failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Endpoint Testing Complete")
    

if __name__ == "__main__":
    test_search_endpoints()