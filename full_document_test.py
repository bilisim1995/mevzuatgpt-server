#!/usr/bin/env python3
"""
FULL DOCUMENT TEST - Kapsamlı Sistem Testi
1. Admin kullanıcısı oluştur
2. Gerçek PDF dokümanı yükle
3. Background processing izle
4. Elasticsearch'te embedding kontrolü
5. Semantic search test
6. AI response test
"""
import asyncio
import aiohttp
import json
import time
from io import BytesIO
import logging

# Test için log ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FullDocumentTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.access_token = None
        self.document_id = None
        
    async def run_complete_test(self):
        """Tam sistem testini çalıştır"""
        
        print("🚀 FULL DOCUMENT TEST BAŞLIYOR")
        print("=" * 33)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Aşama 1: Sistem sağlık kontrolü
                await self.check_system_health(session)
                
                # Aşama 2: Admin kullanıcısı oluştur/giriş yap
                await self.setup_admin_user(session)
                
                # Aşama 3: Test dokümanı hazırla
                test_pdf = self.create_legal_test_document()
                
                # Aşama 4: Doküman yükle
                await self.upload_document(session, test_pdf)
                
                # Aşama 5: Processing durumunu izle
                await self.monitor_processing(session)
                
                # Aşama 6: Elasticsearch kontrolü
                await self.check_elasticsearch_storage()
                
                # Aşama 7: Semantic search test
                await self.test_semantic_search()
                
                # Aşama 8: AI response test  
                await self.test_ai_responses(session)
                
                print("\n🎯 FULL TEST TAMAMLANDI!")
                print("=" * 24)
                
        except Exception as e:
            print(f"❌ Test hatası: {e}")
            import traceback
            traceback.print_exc()
    
    async def check_system_health(self, session):
        """Sistem sağlığını kontrol et"""
        print("\n1️⃣ SİSTEM SAĞLIK KONTROLÜ")
        
        async with session.get(f"{self.base_url}/health") as response:
            if response.status == 200:
                health_data = await response.json()
                print(f"✅ API Sağlık: {health_data}")
            else:
                raise Exception(f"API çalışmıyor: {response.status}")
    
    async def setup_admin_user(self, session):
        """Admin kullanıcısı oluştur veya giriş yap"""
        print("\n2️⃣ ADMIN KULLANICI KURULUMU")
        
        # Önce mevcut admin ile giriş dene
        admin_credentials = [
            {"email": "admin@test.com", "password": "admin123"},
            {"email": "test@mevzuat.com", "password": "test123"},
            {"email": "admin@mevzuat.com", "password": "admin123"}
        ]
        
        for creds in admin_credentials:
            async with session.post(
                f"{self.base_url}/api/auth/login",
                json=creds
            ) as response:
                if response.status == 200:
                    auth_result = await response.json()
                    self.access_token = auth_result.get("data", {}).get("access_token")
                    if self.access_token:
                        print(f"✅ Admin giriş başarılı: {creds['email']}")
                        return
                        
        # Admin kullanıcısı yoksa oluştur
        print("⚠️ Admin kullanıcısı bulunamadı, yeni kullanıcı oluşturuluyor...")
        await self.create_admin_user(session)
    
    async def create_admin_user(self, session):
        """Yeni admin kullanıcısı oluştur"""
        
        # Önce normal kayıt ol
        register_data = {
            "email": "admin@test.com",
            "password": "admin123",
            "confirm_password": "admin123",
            "ad": "Test",
            "soyad": "Admin",
            "meslek": "Sistem Yöneticisi",
            "calistigi_yer": "Test Ortamı"
        }
        
        async with session.post(
            f"{self.base_url}/api/auth/register",
            json=register_data
        ) as response:
            if response.status in [200, 201]:
                print("✅ Kullanıcı kaydı oluşturuldu")
                
                # Şimdi giriş yap
                login_data = {
                    "email": "admin@test.com", 
                    "password": "admin123"
                }
                
                async with session.post(
                    f"{self.base_url}/api/auth/login",
                    json=login_data
                ) as login_response:
                    if login_response.status == 200:
                        auth_result = await login_response.json()
                        self.access_token = auth_result.get("data", {}).get("access_token")
                        print("✅ Yeni admin ile giriş başarılı")
                    else:
                        raise Exception("Admin giriş başarısız")
            else:
                error_text = await response.text()
                print(f"⚠️ Kayıt hatası: {response.status} - {error_text}")
                print("Not: Manuel admin kullanıcısı gerekebilir")
    
    async def upload_document(self, session, pdf_content):
        """Test dokümanını yükle"""
        print("\n3️⃣ DOKÜMAN YÜKLEME")
        
        if not self.access_token:
            print("❌ Admin token yok, doküman yüklenemiyor")
            return
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', pdf_content, 
                           filename='test_sosyal_guvenlik.pdf',
                           content_type='application/pdf')
        form_data.add_field('title', 'Sosyal Güvenlik Mevzuatı Test Dokümanı')
        form_data.add_field('description', 'Elasticsearch entegrasyon testi için sosyal güvenlik mevzuatı')
        form_data.add_field('category', 'SOSYAL_GUVENLIK')
        form_data.add_field('source_institution', 'SGK')
        
        async with session.post(
            f"{self.base_url}/api/admin/documents/upload",
            data=form_data,
            headers=headers
        ) as response:
            
            if response.status == 200:
                upload_result = await response.json()
                self.document_id = upload_result.get("data", {}).get("document_id")
                print(f"✅ Doküman yüklendi: {self.document_id}")
                print(f"📄 Dosya URL: {upload_result.get('data', {}).get('file_url', 'N/A')}")
            else:
                error_text = await response.text()
                print(f"❌ Yükleme hatası: {response.status}")
                print(f"   Hata detayı: {error_text}")
    
    async def monitor_processing(self, session):
        """Background processing durumunu izle"""
        print("\n4️⃣ BACKGROUND PROCESSING İZLEME")
        
        if not self.access_token or not self.document_id:
            print("❌ Token veya document_id eksik")
            return
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        max_attempts = 15
        attempt = 0
        
        while attempt < max_attempts:
            try:
                async with session.get(
                    f"{self.base_url}/api/admin/documents/{self.document_id}",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        doc_data = await response.json()
                        status = doc_data.get("data", {}).get("status", "unknown")
                        print(f"   📊 Durum kontrol {attempt + 1}: {status}")
                        
                        if status == "completed":
                            print("✅ Doküman işleme tamamlandı!")
                            return True
                        elif status == "failed":
                            print("❌ Doküman işleme başarısız")
                            return False
                        elif status in ["pending", "processing"]:
                            print(f"   ⏳ İşleniyor... ({status})")
                            await asyncio.sleep(3)
                        else:
                            print(f"   ❓ Bilinmeyen durum: {status}")
                            await asyncio.sleep(2)
                    else:
                        print(f"❌ Durum kontrol hatası: {response.status}")
                        break
                        
            except Exception as e:
                print(f"❌ İzleme hatası: {e}")
                break
                
            attempt += 1
        
        print("⏰ Processing timeout - Celery Worker loglarını kontrol edin")
        return False
    
    async def check_elasticsearch_storage(self):
        """Elasticsearch'te embeddings kontrolü"""
        print("\n5️⃣ ELASTICSEARCH KONTROL")
        
        try:
            from services.embedding_service import EmbeddingService
            from services.elasticsearch_service import ElasticsearchService
            
            # Elasticsearch sağlık
            es_service = ElasticsearchService()
            health = await es_service.health_check()
            print(f"✅ Elasticsearch sağlık: {health}")
            
            # Embedding sayısı
            embedding_service = EmbeddingService()
            total_count = await embedding_service.get_embeddings_count()
            print(f"✅ Toplam embeddings: {total_count}")
            
            if self.document_id:
                doc_count = await embedding_service.get_embeddings_count(self.document_id)
                print(f"✅ Test dokümanı embeddings: {doc_count}")
            
        except Exception as e:
            print(f"❌ Elasticsearch kontrol hatası: {e}")
    
    async def test_semantic_search(self):
        """Semantic search testleri"""
        print("\n6️⃣ SEMANTIC SEARCH TEST")
        
        try:
            from services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            
            test_queries = [
                "sigortalılık şartları nelerdir",
                "prim ödeme yükümlülüğü",
                "emeklilik yaşı koşulları",
                "iş kazası tazminatı"
            ]
            
            for query in test_queries:
                print(f"\n🔍 Sorgu: '{query}'")
                
                results = await embedding_service.similarity_search(
                    query_text=query,
                    k=3,
                    similarity_threshold=0.2
                )
                
                print(f"✅ {len(results)} sonuç bulundu")
                for i, result in enumerate(results[:2]):
                    print(f"   {i+1}. Benzerlik: {result['similarity']:.3f}")
                    print(f"      İçerik: {result['content'][:60]}...")
                    print(f"      Kaynak: {result['source_document']}")
        
        except Exception as e:
            print(f"❌ Search test hatası: {e}")
    
    async def test_ai_responses(self, session):
        """AI response testleri"""
        print("\n7️⃣ AI RESPONSE TEST")
        
        if not self.access_token:
            print("❌ Token yok, AI test atlanıyor")
            return
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        test_questions = [
            "Sosyal güvenlik kapsamında sigortalılık şartları nelerdir?",
            "İş kazası halinde hangi tazminatlar ödenir?",
            "Emeklilik için gerekli prim ödeme süresi nedir?"
        ]
        
        for question in test_questions:
            print(f"\n💬 Soru: {question}")
            
            query_data = {
                "query": question,
                "limit": 3,
                "institution_filter": "SGK"
            }
            
            try:
                async with session.post(
                    f"{self.base_url}/api/user/ask",
                    json=query_data,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        ai_result = await response.json()
                        answer = ai_result.get("data", {}).get("answer", "Cevap bulunamadı")
                        sources = ai_result.get("data", {}).get("sources", [])
                        
                        print(f"✅ AI Cevap: {answer[:100]}...")
                        print(f"✅ Kaynak sayısı: {len(sources)}")
                    else:
                        error_text = await response.text()
                        print(f"❌ AI test hatası: {response.status} - {error_text}")
                        
            except Exception as e:
                print(f"❌ AI sorgu hatası: {e}")
    
    def create_legal_test_document(self):
        """Gerçek hukuki içerikli test PDF oluştur"""
        
        # Detaylı Türkçe hukuki içerik
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 1250
>>
stream
BT
/F1 12 Tf
50 750 Td
(SOSYAL GUVENLIK KURUMU MEVZUATI) Tj
0 -25 Td
(Test Dokumani - Elasticsearch Entegrasyonu) Tj
0 -35 Td
(BIRINCI BOLUM: SIGORTALILK SARTLARI) Tj
0 -20 Td
(Madde 1: Sigortalilk kapsamina girenler) Tj
0 -15 Td
(a) 18 yas ustu Turkiye Cumhuriyeti vatandaslari) Tj
0 -15 Td
(b) Calisma izni olan yabanci uyruklu kisisl) Tj
0 -15 Td
(c) Aylik geliri asgari ucretin yarisini gecenler) Tj
0 -25 Td
(Madde 2: Prim odeme yukumlulugu) Tj
0 -15 Td
(Sigortalinin ve isverenin prim odeme yukumlulugu vardir.) Tj
0 -15 Td
(Primler her ayin 23'une kadar SGK'ya yatirilir.) Tj
0 -15 Td
(Geciken primler icin yasal faiz uygulanir.) Tj
0 -25 Td
(IKINCI BOLUM: EMEKLILIK SARTLARI) Tj
0 -20 Td
(Madde 3: Yas ve prim gun sartlari) Tj
0 -15 Td
(Erkekler: 65 yas ve 7200 gun prim) Tj
0 -15 Td
(Kadinlar: 63 yas ve 6300 gun prim) Tj
0 -15 Td
(Erken emeklilik: 25 yil sigortalilk suresi) Tj
0 -25 Td
(UCUNCU BOLUM: IS KAZASI TAZMINATLARI) Tj
0 -20 Td
(Madde 4: Gecici is goremezlik odeneigi) Tj
0 -15 Td
(Gunluk kazancin %66.6'si odenir.) Tj
0 -15 Td
(Surekli is goremezlik durumunda aylik bagli.) Tj
0 -15 Td
(Olum halinde dul ve yetim ayllari verilir.) Tj
0 -25 Td
(DORDUNCU BOLUM: SAGLIK HIZSMETLERI) Tj
0 -20 Td
(Madde 5: Saglik hizmetleri kapsaml) Tj
0 -15 Td
(Ayakta tedavi, yatarak tedavi, ilac bedelleri) Tj
0 -15 Td
(Ameliyat masraflari ve protez giderleri) Tj
0 -15 Td
(Gecerli SGK sozlesmeli saglk kuruluslari) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
1507
%%EOF"""
        
        return pdf_content

if __name__ == "__main__":
    tester = FullDocumentTest()
    asyncio.run(tester.run_complete_test())