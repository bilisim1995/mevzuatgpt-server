#!/usr/bin/env python3
"""
Feedback API Test Script
Feedback endpoint'lerini test eder
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_feedback_endpoints():
    """Feedback endpoint'lerini test et"""
    
    # Test verileri
    test_data = {
        "search_log_id": "c454ecf9-341c-4707-a626-cd8d1acd58e4",
        "feedback_type": "positive", 
        "feedback_comment": "API test feedback - çok yararlı!"
    }
    
    # Test kullanıcısı için token (normalde login'den alınır)
    # Bu token'ı gerçek bir login'den almanız gerekir
    token = "test-token-here"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    print("🧪 Feedback API Test Başlıyor...")
    print("=" * 50)
    
    # Test 1: Feedback gönderme
    print("\n1️⃣ Feedback Gönderme Testi")
    print(f"POST {BASE_URL}/api/user/feedback/")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/user/feedback/",
            headers=headers,
            json=test_data,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    # Test 2: Feedback geçmişi
    print("\n2️⃣ Feedback Geçmişi Testi")
    print(f"GET {BASE_URL}/api/user/feedback/my?page=1&limit=10")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/user/feedback/my?page=1&limit=10",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Toplam feedback: {data.get('total_count', 0)}")
            print(f"Bu sayfada: {len(data.get('feedback_list', []))}")
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    # Test 3: Belirli sorgu feedback kontrolü
    print("\n3️⃣ Belirli Sorgu Feedback Kontrolü")
    search_id = test_data["search_log_id"]
    print(f"GET {BASE_URL}/api/user/feedback/search/{search_id}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/user/feedback/search/{search_id}",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"Feedback var: {data.get('feedback_type')}")
                print(f"Yorum: {data.get('feedback_comment')}")
            else:
                print("Bu sorgu için feedback yok")
        else:
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test Tamamlandı")

if __name__ == "__main__":
    test_feedback_endpoints()