#!/usr/bin/env python3
"""
Mevcut kullanıcı ile full test
Admin olmasına gerek yok, core functionality test etmeye odaklanacağız
"""
import asyncio
import aiohttp
import json
from io import BytesIO

async def test_with_user():
    """Mevcut kullanıcı ile test"""
    
    print("🔄 MEVCUT KULLANICI İLE FULL TEST")
    print("=" * 34)
    
    access_token = None
    
    async with aiohttp.ClientSession() as session:
        
        # Login
        print("\n1️⃣ KULLANICI LOGIN")
        login_data = {"email": "testadmin@gmail.com", "password": "testadmin123"}
        
        async with session.post(
            'http://localhost:5000/api/auth/login',
            json=login_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                access_token = result.get("data", {}).get("access_token")
                user = result.get("data", {}).get("user", {})
                print(f"✅ Login başarılı: {user.get('email')}")
                print(f"👤 Role: {user.get('role', 'user')}")
            else:
                print(f"❌ Login başarısız: {response.status}")
                return
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # User search endpoint test (admin gerekmez)
        print("\n2️⃣ USER SEARCH TEST")
        
        search_queries = [
            "sigortalılık şartları nelerdir",
            "prim ödeme süresi",
            "emeklilik yaşı"
        ]
        
        for query in search_queries:
            print(f"\n🔍 Arama: '{query}'")
            
            search_data = {
                "query": query,
                "limit": 3
            }
            
            async with session.post(
                'http://localhost:5000/api/user/ask',
                json=search_data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    search_result = await response.json()
                    answer = search_result.get("data", {}).get("answer", "")
                    sources = search_result.get("data", {}).get("sources", [])
                    
                    print(f"✅ AI Cevap alındı ({len(answer)} karakter)")
                    print(f"✅ Kaynak sayısı: {len(sources)}")
                    print(f"📄 Cevap önizleme: {answer[:80]}...")
                    
                    if sources:
                        print("📚 Kaynaklar:")
                        for i, source in enumerate(sources[:2]):
                            doc_name = source.get("source_document", "Bilinmiyor")
                            similarity = source.get("similarity", 0)
                            print(f"   {i+1}. {doc_name} (Benzerlik: {similarity:.3f})")
                
                elif response.status == 401:
                    print("❌ Yetki hatası - token geçersiz")
                    break
                elif response.status == 404:
                    print("❌ Search endpoint bulunamadı")
                else:
                    error_text = await response.text()
                    print(f"❌ Search hatası: {response.status}")
                    print(f"   Detay: {error_text}")
        
        # User profile test
        print("\n3️⃣ USER PROFILE TEST")
        
        async with session.get(
            'http://localhost:5000/api/user/profile',
            headers=headers
        ) as response:
            if response.status == 200:
                profile = await response.json()
                print(f"✅ Profil alındı: {profile}")
            else:
                print(f"❌ Profil hatası: {response.status}")
        
        # Search history test  
        print("\n4️⃣ SEARCH HISTORY TEST")
        
        async with session.get(
            'http://localhost:5000/api/user/search-history',
            headers=headers
        ) as response:
            if response.status == 200:
                history = await response.json()
                searches = history.get("data", {}).get("searches", [])
                print(f"✅ Arama geçmişi: {len(searches)} arama")
            else:
                print(f"❌ Geçmiş hatası: {response.status}")
        
        print("\n🎯 USER LEVEL TEST TAMAMLANDI!")

if __name__ == "__main__":
    asyncio.run(test_with_user())