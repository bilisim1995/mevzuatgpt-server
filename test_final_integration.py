#!/usr/bin/env python3
"""
Final Integration Test - Complete System Test
Tests: Authentication → Document Upload → Processing → Elasticsearch → Search
"""
import asyncio
import aiohttp
import json
from io import BytesIO

async def test_final_integration():
    """Complete system integration test"""
    
    print("🎯 FINAL INTEGRATION TEST")
    print("=" * 26)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: API Health
        print("\n1️⃣ API HEALTH CHECK")
        async with session.get('http://localhost:5000/health') as response:
            if response.status == 200:
                health = await response.json()
                print(f"✅ API Status: {health}")
            else:
                print(f"❌ API Health: {response.status}")
                return
        
        # Test 2: Admin Authentication  
        print("\n2️⃣ ADMIN AUTHENTICATION")
        
        # Try to get admin access (test multiple potential admin accounts)
        admin_credentials = [
            {"email": "admin@test.com", "password": "admin123"},
            {"email": "admin@mevzuatgpt.com", "password": "admin123"},
            {"email": "test@admin.com", "password": "admin123"}
        ]
        
        access_token = None
        for creds in admin_credentials:
            async with session.post(
                'http://localhost:5000/api/auth/login',
                json=creds
            ) as response:
                if response.status == 200:
                    auth_result = await response.json()
                    access_token = auth_result.get("data", {}).get("access_token")
                    if access_token:
                        print(f"✅ Admin login successful: {creds['email']}")
                        break
                else:
                    print(f"   Login failed for {creds['email']}: {response.status}")
        
        if not access_token:
            print("❌ No admin access - creating test authentication header")
            # For testing purposes, we'll test Elasticsearch directly
            await test_elasticsearch_direct()
            return
        
        # Test 3: Admin Endpoints with Authentication
        print("\n3️⃣ ADMIN ENDPOINTS WITH AUTH")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test Elasticsearch health
        async with session.get(
            'http://localhost:5000/api/admin/elasticsearch/health',
            headers=headers
        ) as response:
            if response.status == 200:
                es_health = await response.json()
                print(f"✅ Elasticsearch Health: {es_health}")
            else:
                print(f"❌ Elasticsearch Health: {response.status}")
        
        # Test embeddings count
        async with session.get(
            'http://localhost:5000/api/admin/embeddings/count',
            headers=headers
        ) as response:
            if response.status == 200:
                count_data = await response.json()
                print(f"✅ Embeddings Count: {count_data}")
            else:
                print(f"❌ Embeddings Count: {response.status}")
        
        # Test 4: Document Upload (if admin access available)
        print("\n4️⃣ DOCUMENT UPLOAD TEST")
        
        # Create test PDF
        test_pdf = create_test_pdf()
        
        form_data = aiohttp.FormData()
        form_data.add_field('file', test_pdf, 
                           filename='test_legal_doc.pdf',
                           content_type='application/pdf')
        form_data.add_field('title', 'Test Legal Document Integration')
        form_data.add_field('description', 'Elasticsearch integration test document')
        form_data.add_field('category', 'TEST')
        form_data.add_field('source_institution', 'TEST_INTEGRATION')
        
        async with session.post(
            'http://localhost:5000/api/admin/documents/upload',
            data=form_data,
            headers=headers
        ) as response:
            
            if response.status == 200:
                upload_result = await response.json()
                print(f"✅ Document Upload: {upload_result}")
                
                document_id = upload_result.get("data", {}).get("document_id")
                if document_id:
                    print(f"📄 Document ID: {document_id}")
                    print("⚠️  Document processing will happen in background via Celery")
                    print("   Check Celery Worker logs for processing status")
            else:
                error_text = await response.text()
                print(f"❌ Document Upload: {response.status}")
                print(f"   Error: {error_text}")

async def test_elasticsearch_direct():
    """Direct Elasticsearch testing without authentication"""
    
    print("\n🔄 DIRECT ELASTICSEARCH TEST")
    print("=" * 30)
    
    try:
        from services.embedding_service import EmbeddingService
        from services.elasticsearch_service import ElasticsearchService
        
        # Test Elasticsearch connection
        es_service = ElasticsearchService()
        health = await es_service.health_check()
        print(f"✅ Elasticsearch Direct: {health}")
        
        # Test embeddings service
        embedding_service = EmbeddingService()
        count = await embedding_service.get_embeddings_count()
        print(f"✅ Current Embeddings: {count}")
        
        # Test search with existing embeddings
        if count > 0:
            search_results = await embedding_service.similarity_search(
                "hukuki düzenlemeler",
                k=3,
                similarity_threshold=0.1
            )
            print(f"✅ Search Test: Found {len(search_results)} results")
            for i, result in enumerate(search_results[:2]):
                print(f"   {i+1}. Similarity: {result['similarity']:.3f}")
                print(f"      Content: {result['content'][:50]}...")
        
    except Exception as e:
        print(f"❌ Direct Elasticsearch test failed: {e}")

def create_test_pdf():
    """Create a test PDF for upload"""
    
    # Simple PDF content for testing
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
/Length 250
>>
stream
BT
/F1 12 Tf
100 700 Td
(ELASTICSEARCH INTEGRATION TEST DOCUMENT) Tj
0 -30 Td
(Bu belge Elasticsearch entegrasyonu test amaclidir) Tj
0 -25 Td
(Sosyal guvenlik sigortaliligi hakkinda bilgiler:) Tj
0 -20 Td
(1. Sigortalilk sartlari ve yukumlulukler) Tj
0 -20 Td
(2. Prim odeme usulleri) Tj
0 -20 Td
(3. Tazminat hakklari) Tj
0 -30 Td
(Is sagligi ve guvenlik mevzuati:) Tj
0 -20 Td
(- Isveren yukumlulukler) Tj
0 -20 Td
(- Isci haklari) Tj
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
507
%%EOF"""
    
    return pdf_content

if __name__ == "__main__":
    asyncio.run(test_final_integration())