#!/usr/bin/env python3
"""
Türkçe Karakter Desteği Test
Test the Turkish character encoding support in the system
"""
import asyncio
import aiohttp
import json
import tempfile
import os

class TurkishEncodingTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        
    async def test_turkish_support(self):
        """Test Turkish character support end-to-end"""
        
        print("🇹🇷 TÜRKÇE KARAKTER DESTEĞİ TESTİ")
        print("=" * 38)
        
        # Test 1: API Login with Turkish characters
        await self.test_api_login()
        
        # Test 2: Text processing functions
        await self.test_text_processing()
        
        # Test 3: Embedding generation
        await self.test_embedding_generation() 
        
        # Test 4: Search with Turkish queries
        await self.test_turkish_search()
        
        print("\n✅ TÜRKÇE KARAKTER DESTEĞİ TESTİ TAMAMLANDI")
        
    async def test_api_login(self):
        """Test API login functionality"""
        print("\n1️⃣ API LOGIN TEST")
        
        try:
            async with aiohttp.ClientSession() as session:
                login_data = {
                    "email": "admin@mevzuatgpt.com",
                    "password": "AdminMevzuat2025!"
                }
                
                async with session.post(
                    f"{self.base_url}/api/auth/login",
                    json=login_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        print("✅ Login başarılı")
                        return result.get("access_token")
                    else:
                        print(f"❌ Login failed: {response.status}")
                        
        except Exception as e:
            print(f"❌ Login error: {e}")
            
        return None
        
    async def test_text_processing(self):
        """Test text processing functions with Turkish characters"""
        print("\n2️⃣ TEXT PROCESSING TEST")
        
        try:
            # Import text processing functions
            from tasks.document_processor import _clean_extracted_text
            from services.pdf_source_parser import PDFSourceParser
            
            # Test texts with Turkish characters
            test_texts = [
                "Sosyal güvenlik sigortalılık şartları ve yükümlülükleri",
                "İş kazası geçici iş göremezlik ödeneği hesaplama usulü",
                "Emeklilik yaşı erkek ve kadın için farklı düzenlemeler",
                "Prim ödeme yükümlülüğü gecikme halinde faiz uygulaması",
                "Türkiye Cumhuriyeti vatandaşları için özel şartlar"
            ]
            
            for i, text in enumerate(test_texts, 1):
                try:
                    # Test text cleaning
                    cleaned = _clean_extracted_text(text)
                    print(f"✅ Test {i}: '{text[:30]}...' -> Cleaned successfully")
                    
                    # Verify Turkish characters preserved
                    turkish_chars = ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü', 'İ']
                    has_turkish = any(char in cleaned for char in turkish_chars)
                    
                    if has_turkish:
                        print(f"   ✅ Turkish characters preserved")
                    else:
                        print(f"   ⚠️ No Turkish characters detected")
                        
                except Exception as e:
                    print(f"❌ Test {i} failed: {e}")
                    
        except Exception as e:
            print(f"❌ Text processing test error: {e}")
            
    async def test_embedding_generation(self):
        """Test embedding generation with Turkish text"""
        print("\n3️⃣ EMBEDDING GENERATION TEST")
        
        try:
            from services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            
            turkish_text = "Sosyal güvenlik kapsamında sigortalılık şartları nelerdir?"
            
            print(f"📝 Test text: '{turkish_text}'")
            
            # Generate embedding
            embedding = await embedding_service.generate_embedding(turkish_text)
            
            print(f"✅ Embedding generated successfully")
            print(f"📊 Dimensions: {len(embedding)}")
            print(f"📈 Sample values: {embedding[:5]}")
            
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            
    async def test_turkish_search(self):
        """Test search functionality with Turkish queries"""
        print("\n4️⃣ TURKISH SEARCH TEST")
        
        try:
            from services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            
            # Turkish search queries
            test_queries = [
                "sigortalılık şartları",
                "prim ödeme yükümlülüğü", 
                "emeklilik yaşı koşulları",
                "iş kazası tazminatı",
                "sosyal güvenlik kapsamı"
            ]
            
            for query in test_queries:
                try:
                    print(f"\n🔍 Query: '{query}'")
                    
                    results = await embedding_service.similarity_search(
                        query_text=query,
                        k=3,
                        similarity_threshold=0.2
                    )
                    
                    print(f"✅ Results: {len(results)} matches found")
                    
                    if results:
                        best_result = results[0]
                        print(f"   📊 Best similarity: {best_result['similarity']:.3f}")
                        print(f"   📄 Source: {best_result['source_document']}")
                        
                except Exception as e:
                    print(f"❌ Search failed for '{query}': {e}")
                    
        except Exception as e:
            print(f"❌ Search test error: {e}")

if __name__ == "__main__":
    tester = TurkishEncodingTest()
    asyncio.run(tester.test_turkish_support())