#!/usr/bin/env python3
"""
OpenAI API Bağlantı Testi
.env dosyasından API key'i alarak OpenAI bağlantısını test eder
"""

import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

class OpenAITester:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
        self.chat_model = os.getenv('OPENAI_MODEL', 'gpt-4o')
        
        if not self.api_key:
            print("❌ OPENAI_API_KEY bulunamadı!")
            sys.exit(1)
        
        # Mask API key for display
        self.masked_key = f"{self.api_key[:8]}...{self.api_key[-8:]}"
        
        # Initialize client
        self.client = OpenAI(api_key=self.api_key)
    
    def test_api_key_format(self):
        """API key formatını kontrol et"""
        print("🔑 API Key Format Kontrolü...")
        
        # OpenAI API key format: sk-proj-... (yeni format) veya sk-... (eski format)
        if self.api_key.startswith('sk-proj-'):
            print(f"   ✅ Yeni format API key tespit edildi")
            print(f"   📝 Key: {self.masked_key}")
            return True
        elif self.api_key.startswith('sk-'):
            print(f"   ✅ Klasik format API key tespit edildi")
            print(f"   📝 Key: {self.masked_key}")
            return True
        else:
            print(f"   ❌ Geçersiz API key formatı: {self.masked_key}")
            return False
    
    def test_embeddings_api(self):
        """Embeddings API'yi test et"""
        print(f"🔍 Embeddings API Testi ({self.embedding_model})...")
        
        try:
            # Test text
            test_text = "Bu bir test metnidir."
            
            # Create embedding
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=test_text
            )
            
            # Check response
            if response.data and len(response.data) > 0:
                embedding = response.data[0].embedding
                print(f"   ✅ Embedding oluşturuldu")
                print(f"   📊 Model: {response.model}")
                print(f"   📐 Dimension: {len(embedding)}")
                print(f"   💰 Token usage: {response.usage.total_tokens}")
                return True
            else:
                print("   ❌ Boş embedding response")
                return False
                
        except Exception as e:
            print(f"   ❌ Embeddings API hatası: {str(e)}")
            return False
    
    def test_chat_api(self):
        """Chat API'yi test et"""
        print(f"💬 Chat API Testi ({self.chat_model})...")
        
        try:
            # Test chat completion
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "user", "content": "Merhaba! Bu bir API test mesajıdır. Kısa bir yanıt ver."}
                ],
                max_tokens=50
            )
            
            # Check response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                print(f"   ✅ Chat response alındı")
                print(f"   📊 Model: {response.model}")
                print(f"   💰 Token usage: {response.usage.total_tokens}")
                print(f"   💬 Response: {content[:100]}...")
                return True
            else:
                print("   ❌ Boş chat response")
                return False
                
        except Exception as e:
            print(f"   ❌ Chat API hatası: {str(e)}")
            return False
    
    def test_models_list(self):
        """Mevcut modelleri listele"""
        print("📋 Kullanılabilir Modeller...")
        
        try:
            models = self.client.models.list()
            
            # Filter relevant models
            embedding_models = []
            chat_models = []
            
            for model in models.data:
                model_id = model.id
                if 'embedding' in model_id:
                    embedding_models.append(model_id)
                elif any(x in model_id for x in ['gpt-3.5', 'gpt-4', 'gpt-4o']):
                    chat_models.append(model_id)
            
            print(f"   🔍 Embedding modelleri: {len(embedding_models)}")
            for model in sorted(embedding_models)[:3]:  # Show first 3
                print(f"      • {model}")
            
            print(f"   💬 Chat modelleri: {len(chat_models)}")
            for model in sorted(chat_models)[:5]:  # Show first 5
                print(f"      • {model}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Model listesi alınamadı: {str(e)}")
            return False
    
    def run_comprehensive_test(self):
        """Kapsamlı test suite"""
        print("=" * 60)
        print("🔬 OpenAI API Kapsamlı Test")
        print("=" * 60)
        print(f"🕐 Test zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        tests = [
            ("API Key Format", self.test_api_key_format),
            ("Embeddings API", self.test_embeddings_api),
            ("Chat API", self.test_chat_api),
            ("Models List", self.test_models_list),
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            print(f"🧪 {test_name}")
            print("-" * 40)
            
            try:
                success = test_func()
                if success:
                    passed_tests += 1
                    print("✅ Test başarılı!")
                else:
                    print("❌ Test başarısız!")
            except Exception as e:
                print(f"💥 Test hatası: {str(e)}")
            
            print()
        
        # Final report
        print("=" * 60)
        print(f"📊 Test Sonuçları: {passed_tests}/{total_tests} başarılı")
        
        if passed_tests == total_tests:
            print("🎉 TÜM TESTLER BAŞARILI!")
            print("✅ OpenAI API tamamen çalışıyor")
            print("✅ Embeddings sistemi hazır")
            print("✅ Chat sistemi hazır")
            success_rate = 100.0
        else:
            success_rate = (passed_tests / total_tests) * 100
            print(f"⚠️ {total_tests - passed_tests} TEST BAŞARISIZ!")
            print("❌ OpenAI API'de problemler var")
        
        print(f"📈 Başarı oranı: {success_rate:.1f}%")
        print("=" * 60)
        
        return passed_tests == total_tests

def main():
    """Ana test fonksiyonu"""
    try:
        tester = OpenAITester()
        success = tester.run_comprehensive_test()
        
        if success:
            print("\n🎯 Sonuç: OpenAI API tamamen çalışıyor!")
            print("💡 MevzuatGPT sistemi embedding ve chat için hazır.")
            sys.exit(0)
        else:
            print("\n⚠️ Sonuç: OpenAI API'de problemler tespit edildi.")
            print("🔧 API key'i kontrol edin veya OpenAI dashboard'unu kontrol edin.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Test kullanıcı tarafından iptal edildi.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Beklenmeyen hata: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()