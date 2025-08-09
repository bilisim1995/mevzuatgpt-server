"""
Real search test with actual user authentication
"""
import asyncio
import requests
import json

BASE_URL = "http://localhost:5000"

def register_test_user():
    """Register a test user and get token"""
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", 
            json={
                "email": "user.test.2025@gmail.com", 
                "password": "TestPass123",
                "confirm_password": "TestPass123",
                "ad": "Test",
                "soyad": "User"
            }
        )
        if response.status_code == 201:
            return response.json().get("access_token")
        else:
            print(f"Registration failed: {response.text}")
            return None
    except Exception as e:
        print(f"Registration error: {e}")
        return None

def test_search_with_auth(token):
    """Test search with authentication"""
    if not token:
        print("❌ No token available")
        return
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test the exact query from user
    query_data = {
        "query": "Sigortalılık şartları nelerdir?",
        "limit": 5
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/user/ask", 
            json=query_data, 
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        result = response.json()
        
        if response.status_code == 200:
            print(f"✅ Search successful!")
            print(f"Query: {result.get('query')}")
            print(f"Answer: {result.get('answer')}")
            print(f"Sources found: {len(result.get('sources', []))}")
            print(f"Confidence: {result.get('confidence_score')}")
            
            if result.get('sources'):
                print("\n📄 Sources:")
                for i, source in enumerate(result['sources'][:2]):
                    print(f"  {i+1}. {source.get('document_title')}")
                    print(f"     Content: {source.get('content', '')[:100]}...")
            else:
                print("❌ No sources found - this is the problem!")
        else:
            print(f"❌ Search failed: {result}")
            
    except Exception as e:
        print(f"❌ Search request error: {e}")

if __name__ == "__main__":
    print("🧪 Testing real search with authentication...")
    
    # Register and get token
    token = register_test_user()
    
    # Test search
    test_search_with_auth(token)