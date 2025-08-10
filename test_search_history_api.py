"""
Test script for search history API endpoint
"""

import requests
import json


def test_search_history_endpoint():
    """Test the search history endpoint without auth"""
    
    base_url = "http://localhost:5000"
    
    # Test basic endpoint access
    print("Testing GET /api/user/search-history endpoint...")
    print("=" * 60)
    
    # Test endpoint availability  
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✓ Server is running")
        else:
            print("✗ Server health check failed")
            return
    except Exception as e:
        print(f"✗ Server connection failed: {e}")
        return
    
    # Test search history endpoint structure
    try:
        response = requests.get(f"{base_url}/api/user/search-history")
        print(f"\nEndpoint Response Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
        
        if response.status_code == 401:
            print("✓ Authorization required (expected)")
            print(f"Response: {response.json()}")
            
        elif response.status_code == 200:
            print("✓ Endpoint accessible")
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
            
        else:
            print(f"✗ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Request failed: {e}")

    print("\n" + "=" * 60)
    print("API Endpoint Summary:")
    print("""
    GET /api/user/search-history
    
    Purpose: Retrieve user's search history with full details
    
    Features:
    - Pagination (page, limit parameters)
    - Filtering by institution, date range, reliability score
    - Search within user's queries
    - Returns query, AI response, sources, credits used
    
    Query Parameters:
    - page: Page number (default 1)
    - limit: Items per page (default 20, max 100)
    - institution: Filter by institution name
    - date_from: Filter from date (ISO format)
    - date_to: Filter to date (ISO format) 
    - min_reliability: Minimum reliability score (0.0-1.0)
    - search_query: Search within user's queries
    
    Response Format:
    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "uuid",
            "query": "User's search query",
            "response": "AI response text", 
            "sources": [...],
            "reliability_score": 0.85,
            "credits_used": 1,
            "institution_filter": "SGK",
            "results_count": 5,
            "execution_time": 2.3,
            "created_at": "2025-08-10T20:30:00Z"
          }
        ],
        "total_count": 25,
        "page": 1,
        "limit": 20,
        "has_more": true
      }
    }
    
    Additional Endpoints:
    GET /api/user/search-history/stats - Search statistics
    """)

if __name__ == "__main__":
    test_search_history_endpoint()