#!/usr/bin/env python3
"""
FULL DOCUMENT TEST WITH ADMIN CREDENTIALS
Complete system test with document upload, processing, and AI responses
"""
import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FullSystemTest:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.admin_email = "admin@mevzuatgpt.com"
        self.admin_password = "AdminMevzuat2025!"
        self.access_token = None
        self.document_id = None
        
    async def run_complete_test(self):
        """Complete system test with admin credentials"""
        
        print("🚀 FULL SYSTEM TEST - ADMIN CREDENTIALS")
        print("=" * 41)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: System Health Check
                await self.check_system_health(session)
                
                # Step 2: Admin Login
                await self.admin_login(session)
                
                # Step 3: Upload Test Document
                await self.upload_legal_document(session)
                
                # Step 4: Monitor Processing
                await self.monitor_document_processing(session)
                
                # Step 5: Elasticsearch Verification
                await self.verify_elasticsearch_storage()
                
                # Step 6: Search Testing
                await self.test_semantic_search()
                
                # Step 7: AI Response Testing
                await self.test_ai_responses(session)
                
                # Step 8: Admin Endpoints Testing
                await self.test_admin_endpoints(session)
                
                print("\n🎯 COMPLETE SYSTEM TEST FINISHED!")
                print("=" * 35)
                
        except Exception as e:
            print(f"❌ System test error: {e}")
            import traceback
            traceback.print_exc()
    
    async def check_system_health(self, session):
        """Check system health"""
        print("\n1️⃣ SYSTEM HEALTH CHECK")
        
        async with session.get(f"{self.base_url}/health") as response:
            if response.status == 200:
                health_data = await response.json()
                print(f"✅ API Health: {health_data['data']['status']}")
                print(f"✅ Version: {health_data['data']['version']}")
            else:
                raise Exception(f"API not healthy: {response.status}")
    
    async def admin_login(self, session):
        """Admin login with provided credentials"""
        print("\n2️⃣ ADMIN LOGIN")
        
        login_data = {
            "email": self.admin_email,
            "password": self.admin_password
        }
        
        async with session.post(
            f"{self.base_url}/api/auth/login",
            json=login_data
        ) as response:
            if response.status == 200:
                auth_result = await response.json()
                self.access_token = auth_result.get("data", {}).get("access_token")
                user = auth_result.get("data", {}).get("user", {})
                
                print(f"✅ Login successful: {user.get('email')}")
                print(f"👤 Role: {user.get('role', 'user')}")
                print(f"🔑 Token received: {len(self.access_token) if self.access_token else 0} chars")
                
                if user.get('role') != 'admin':
                    print("⚠️ Warning: User is not admin role")
                    
            else:
                error_text = await response.text()
                raise Exception(f"Login failed: {response.status} - {error_text}")
    
    async def upload_legal_document(self, session):
        """Upload a comprehensive legal test document"""
        print("\n3️⃣ DOCUMENT UPLOAD")
        
        if not self.access_token:
            raise Exception("No access token for upload")
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Create realistic Turkish legal document
        pdf_content = self.create_comprehensive_legal_pdf()
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', pdf_content, 
                           filename='sosyal_guvenlik_kanunu_test.pdf',
                           content_type='application/pdf')
        form_data.add_field('title', 'Sosyal Güvenlik Kanunu - Elasticsearch Test Dokümanı')
        form_data.add_field('description', 'Kapsamlı sosyal güvenlik mevzuatı test dokümanı - sigortalılık, primler, emeklilik ve iş kazası hükümleri')
        form_data.add_field('category', 'SOSYAL_GUVENLIK')
        form_data.add_field('source_institution', 'SGK')
        form_data.add_field('keywords', 'sigortalılık,prim,emeklilik,iş kazası,sosyal güvenlik')
        
        async with session.post(
            f"{self.base_url}/api/admin/documents/upload",
            data=form_data,
            headers=headers
        ) as response:
            
            if response.status == 200:
                upload_result = await response.json()
                self.document_id = upload_result.get("data", {}).get("document_id")
                file_url = upload_result.get("data", {}).get("file_url", "N/A")
                
                print(f"✅ Document uploaded successfully")
                print(f"📄 Document ID: {self.document_id}")
                print(f"🔗 File URL: {file_url}")
                print(f"📊 File size: {len(pdf_content)} bytes")
                
            else:
                error_text = await response.text()
                raise Exception(f"Upload failed: {response.status} - {error_text}")
    
    async def monitor_document_processing(self, session):
        """Monitor background document processing"""
        print("\n4️⃣ DOCUMENT PROCESSING MONITORING")
        
        if not self.access_token or not self.document_id:
            raise Exception("Missing token or document ID")
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        max_attempts = 20
        attempt = 0
        
        while attempt < max_attempts:
            try:
                async with session.get(
                    f"{self.base_url}/api/admin/documents/{self.document_id}",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        doc_data = await response.json()
                        doc_info = doc_data.get("data", {})
                        status = doc_info.get("status", "unknown")
                        
                        print(f"   📊 Processing check {attempt + 1}: {status}")
                        
                        if status == "completed":
                            chunk_count = doc_info.get("total_chunks", 0)
                            processing_time = doc_info.get("processing_time", "N/A")
                            
                            print("✅ Document processing completed!")
                            print(f"📝 Total chunks: {chunk_count}")
                            print(f"⏱️ Processing time: {processing_time}")
                            return True
                            
                        elif status == "failed":
                            error_message = doc_info.get("error_message", "Unknown error")
                            print(f"❌ Document processing failed: {error_message}")
                            return False
                            
                        elif status in ["pending", "processing"]:
                            print(f"   ⏳ Processing... ({status})")
                            await asyncio.sleep(3)
                            
                        else:
                            print(f"   ❓ Unknown status: {status}")
                            await asyncio.sleep(2)
                    else:
                        print(f"❌ Status check failed: {response.status}")
                        break
                        
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                break
                
            attempt += 1
        
        print("⏰ Processing timeout - Check Celery Worker logs")
        return False
    
    async def verify_elasticsearch_storage(self):
        """Verify Elasticsearch storage"""
        print("\n5️⃣ ELASTICSEARCH VERIFICATION")
        
        try:
            from services.elasticsearch_service import ElasticsearchService
            from services.embedding_service import EmbeddingService
            
            # Elasticsearch health
            es_service = ElasticsearchService()
            health = await es_service.health_check()
            print(f"✅ Cluster status: {health['cluster_status']}")
            print(f"✅ Total documents: {health['document_count']}")
            print(f"✅ Vector dimensions: {health['vector_dimensions']}")
            
            # Embedding count verification
            embedding_service = EmbeddingService()
            total_count = await embedding_service.get_embeddings_count()
            print(f"✅ Total embeddings: {total_count}")
            
            if self.document_id:
                doc_count = await embedding_service.get_embeddings_count(self.document_id)
                print(f"✅ Test document embeddings: {doc_count}")
                
                if doc_count > 0:
                    print("✅ Document successfully vectorized and stored")
                else:
                    print("⚠️ No embeddings found for test document")
            
        except Exception as e:
            print(f"❌ Elasticsearch verification error: {e}")
    
    async def test_semantic_search(self):
        """Test semantic search capabilities"""
        print("\n6️⃣ SEMANTIC SEARCH TESTING")
        
        try:
            from services.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            
            # Comprehensive search queries
            test_queries = [
                {
                    "query": "sigortalılık şartları yaş limiti nedir",
                    "expected": "age related content"
                },
                {
                    "query": "prim ödeme yükümlülüğü gecikme faizi",
                    "expected": "premium payment delay"
                },
                {
                    "query": "emeklilik yaşı erkek kadın farkı",
                    "expected": "retirement age gender"
                },
                {
                    "query": "iş kazası geçici iş göremezlik ödeneği",
                    "expected": "work accident compensation"
                },
                {
                    "query": "sosyal güvenlik yabancı uyruklu çalışan",
                    "expected": "foreign worker coverage"
                }
            ]
            
            for test_case in test_queries:
                query = test_case["query"]
                print(f"\n🔍 Query: '{query}'")
                
                results = await embedding_service.similarity_search(
                    query_text=query,
                    k=3,
                    similarity_threshold=0.2
                )
                
                print(f"✅ Results found: {len(results)}")
                
                if results:
                    best_match = results[0]
                    print(f"   📊 Best similarity: {best_match['similarity']:.3f}")
                    print(f"   📄 Source: {best_match['source_document']}")
                    print(f"   📝 Content preview: {best_match['content'][:80]}...")
                    
                    # Quality check
                    if best_match['similarity'] > 0.4:
                        print("   ✅ High quality match")
                    elif best_match['similarity'] > 0.3:
                        print("   ⚠️ Medium quality match")
                    else:
                        print("   ❌ Low quality match")
        
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
    
    async def test_ai_responses(self, session):
        """Test AI response generation"""
        print("\n7️⃣ AI RESPONSE TESTING")
        
        if not self.access_token:
            print("❌ No access token for AI testing")
            return
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Comprehensive AI test questions
        test_questions = [
            {
                "question": "Sosyal güvenlik kapsamında sigortalılık şartları nelerdir?",
                "filter": "SGK",
                "expected_topics": ["sigortalılık", "şart", "yaş"]
            },
            {
                "question": "Prim ödeme yükümlülüğü kimde olup, gecikme halinde ne olur?",
                "filter": "SGK", 
                "expected_topics": ["prim", "yükümlülük", "gecikme"]
            },
            {
                "question": "Emeklilik için gerekli yaş ve prim gün şartları nelerdir?",
                "filter": "SGK",
                "expected_topics": ["emeklilik", "yaş", "prim", "gün"]
            },
            {
                "question": "İş kazası halinde hangi tazminatlar ödenir?",
                "filter": "SGK",
                "expected_topics": ["iş kazası", "tazminat", "ödenek"]
            }
        ]
        
        for test_case in test_questions:
            question = test_case["question"]
            print(f"\n💬 Question: {question}")
            
            query_data = {
                "query": question,
                "limit": 3,
                "institution_filter": test_case["filter"]
            }
            
            try:
                async with session.post(
                    f"{self.base_url}/api/user/ask",
                    json=query_data,
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        ai_result = await response.json()
                        data = ai_result.get("data", {})
                        
                        answer = data.get("answer", "")
                        sources = data.get("sources", [])
                        reliability_score = data.get("reliability_score", 0)
                        credits_used = data.get("credits_used", 0)
                        
                        print(f"✅ AI Response generated: {len(answer)} characters")
                        print(f"✅ Sources used: {len(sources)}")
                        print(f"📊 Reliability score: {reliability_score:.2f}")
                        print(f"💰 Credits used: {credits_used}")
                        print(f"📄 Answer preview: {answer[:100]}...")
                        
                        # Content quality check
                        answer_lower = answer.lower()
                        found_topics = [topic for topic in test_case["expected_topics"] 
                                      if topic.lower() in answer_lower]
                        
                        if found_topics:
                            print(f"✅ Answer contains expected topics: {found_topics}")
                        else:
                            print("⚠️ Answer may not contain expected topics")
                            
                    else:
                        error_text = await response.text()
                        print(f"❌ AI query failed: {response.status} - {error_text}")
                        
            except Exception as e:
                print(f"❌ AI query error: {e}")
    
    async def test_admin_endpoints(self, session):
        """Test admin-specific endpoints"""
        print("\n8️⃣ ADMIN ENDPOINTS TESTING")
        
        if not self.access_token:
            print("❌ No access token for admin testing")
            return
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # Test admin endpoints
        admin_endpoints = [
            {
                "name": "Elasticsearch Health",
                "url": "/api/admin/elasticsearch/health",
                "method": "GET"
            },
            {
                "name": "Embeddings Count",
                "url": "/api/admin/elasticsearch/embeddings/count",
                "method": "GET"
            },
            {
                "name": "Documents List",
                "url": "/api/admin/documents",
                "method": "GET"
            },
            {
                "name": "System Stats",
                "url": "/api/admin/system/stats",
                "method": "GET"
            }
        ]
        
        for endpoint in admin_endpoints:
            print(f"\n🔧 Testing: {endpoint['name']}")
            
            try:
                async with session.get(
                    f"{self.base_url}{endpoint['url']}",
                    headers=headers
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        print(f"✅ {endpoint['name']}: Success")
                        
                        # Show specific data based on endpoint
                        if "elasticsearch/health" in endpoint['url']:
                            health_data = result.get("data", {})
                            print(f"   Cluster: {health_data.get('cluster_status', 'unknown')}")
                            
                        elif "embeddings/count" in endpoint['url']:
                            count = result.get("data", {}).get("total_embeddings", 0)
                            print(f"   Total embeddings: {count}")
                            
                        elif "documents" in endpoint['url']:
                            docs = result.get("data", {}).get("documents", [])
                            print(f"   Documents found: {len(docs)}")
                            
                        elif "stats" in endpoint['url']:
                            stats = result.get("data", {})
                            print(f"   System stats: {len(stats)} metrics")
                            
                    elif response.status == 403:
                        print(f"❌ {endpoint['name']}: Access denied (insufficient permissions)")
                    elif response.status == 404:
                        print(f"⚠️ {endpoint['name']}: Endpoint not found")
                    else:
                        print(f"❌ {endpoint['name']}: Error {response.status}")
                        
            except Exception as e:
                print(f"❌ {endpoint['name']} error: {e}")
    
    def create_comprehensive_legal_pdf(self):
        """Create comprehensive legal PDF content"""
        
        # Simple ASCII-only PDF content
        pdf_text = """%PDF-1.4
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
/Length 1800
>>
stream
BT
/F1 12 Tf
50 750 Td
(SOSYAL GUVENLIK KURUMU MEVZUATI) Tj
0 -20 Td
(Kapsamli Test Dokumani - Elasticsearch Entegrasyonu) Tj
0 -30 Td
(BIRINCI BOLUM: SIGORTALILK SARTLARI) Tj
0 -20 Td
(Madde 1: Sigortalilk Kapsamina Girenler) Tj
0 -15 Td
(a) 18 yasini doldurmus Turkiye Cumhuriyeti vatandaslari) Tj
0 -15 Td
(b) Aylik geliri asgari ucretin yarisini gecen kisiler) Tj
0 -15 Td
(c) Calisma izni olan yabanci uyruklu kisiler) Tj
0 -20 Td
(Madde 2: Prim Odeme Yukumlulugu) Tj
0 -15 Td
(Sigortalinin ve isverenin prim odeme yukumlulugu vardir.) Tj
0 -15 Td
(Primler her ayin 23une kadar SGKya yatirilir.) Tj
0 -15 Td
(Geciken primler icin yasal faiz uygulanir.) Tj
0 -25 Td
(IKINCI BOLUM: EMEKLILIK SARTLARI) Tj
0 -20 Td
(Madde 3: Yas ve Prim Gun Sartlari) Tj
0 -15 Td
(Erkekler: 65 yas ve 7200 gun prim) Tj
0 -15 Td
(Kadinlar: 63 yas ve 6300 gun prim) Tj
0 -15 Td
(Erken emeklilik: 25 yil sigortalilk suresi) Tj
0 -25 Td
(UCUNCU BOLUM: IS KAZASI TAZMINATLARI) Tj
0 -20 Td
(Madde 4: Gecici is goremezlik odenegi) Tj
0 -15 Td
(Gunluk kazancin yuzde 66.6si odenir.) Tj
0 -15 Td
(Surekli is goremezlik durumunda aylik baglanir.) Tj
0 -15 Td
(Olum halinde dul ve yetim ayliklari verilir.) Tj
0 -25 Td
(DORDUNCU BOLUM: SAGLIK HIZMETLERI) Tj
0 -20 Td
(Madde 5: Saglik hizmetleri kapsami) Tj
0 -15 Td
(Ayakta tedavi, yatarak tedavi, ilac bedelleri) Tj
0 -15 Td
(Ameliyat masraflari ve protez giderleri) Tj
0 -15 Td
(Gecerli SGK sozlesmeli saglik kuruluslari) Tj
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
2057
%%EOF"""
        
        return pdf_text.encode('ascii')

if __name__ == "__main__":
    tester = FullSystemTest()
    asyncio.run(tester.run_complete_test())