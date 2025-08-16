#!/usr/bin/env python3
"""
Test Full Document Upload Pipeline
Tests complete workflow: PDF upload → Processing → Elasticsearch → Search
"""
import asyncio
import aiohttp
import aiofiles
import json
import time
from io import BytesIO
from pathlib import Path

async def test_full_document_upload():
    """Test complete document upload and processing workflow"""
    
    print("🚀 FULL DOCUMENT UPLOAD TEST")
    print("=" * 30)
    
    try:
        # Create a simple test PDF content
        print("\n1️⃣ CREATING TEST PDF")
        test_pdf_content = create_simple_pdf()
        print(f"✅ Test PDF created ({len(test_pdf_content)} bytes)")
        
        # Test API health first
        print("\n2️⃣ API HEALTH CHECK")
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:5000/health') as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ API Health: {health}")
                else:
                    print(f"❌ API Health: {response.status}")
                    return
            
            # Test authentication (we need admin token for upload)
            print("\n3️⃣ AUTHENTICATION TEST")
            
            # Test with admin login
            login_data = {
                "email": "admin@test.com",
                "password": "admin123"
            }
            
            async with session.post(
                'http://localhost:5000/api/auth/login',
                json=login_data
            ) as response:
                if response.status == 200:
                    auth_result = await response.json()
                    access_token = auth_result.get("data", {}).get("access_token")
                    if access_token:
                        print("✅ Admin authentication successful")
                        
                        # Test document upload
                        await test_document_upload_with_token(session, access_token, test_pdf_content)
                    else:
                        print("❌ No access token received")
                elif response.status == 401:
                    print("❌ Authentication failed - admin user may not exist")
                    print("   Note: Need to create admin user first")
                else:
                    print(f"❌ Authentication error: {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_document_upload_with_token(session, access_token, pdf_content):
    """Test document upload with authentication token"""
    
    print("\n4️⃣ DOCUMENT UPLOAD TEST")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Prepare multipart form data
        form_data = aiohttp.FormData()
        form_data.add_field('file', pdf_content, 
                           filename='test_legal_doc.pdf',
                           content_type='application/pdf')
        form_data.add_field('title', 'Test Legal Document')
        form_data.add_field('description', 'Test document for Elasticsearch integration')
        form_data.add_field('category', 'TEST')
        form_data.add_field('source_institution', 'TEST_INSTITUTION')
        
        async with session.post(
            'http://localhost:5000/api/admin/documents/upload',
            data=form_data,
            headers=headers
        ) as response:
            
            if response.status == 200:
                upload_result = await response.json()
                print(f"✅ Document uploaded: {upload_result}")
                
                document_id = upload_result.get("data", {}).get("document_id")
                if document_id:
                    await test_processing_status(session, headers, document_id)
                
            else:
                error_text = await response.text()
                print(f"❌ Upload failed: {response.status}")
                print(f"   Error: {error_text}")
    
    except Exception as e:
        print(f"❌ Upload test failed: {e}")

async def test_processing_status(session, headers, document_id):
    """Monitor document processing status"""
    
    print(f"\n5️⃣ PROCESSING STATUS MONITOR")
    print(f"Document ID: {document_id}")
    
    max_attempts = 10
    attempt = 0
    
    while attempt < max_attempts:
        try:
            async with session.get(
                f'http://localhost:5000/api/admin/documents/{document_id}',
                headers=headers
            ) as response:
                
                if response.status == 200:
                    doc_data = await response.json()
                    status = doc_data.get("data", {}).get("status", "unknown")
                    print(f"   Attempt {attempt + 1}: Status = {status}")
                    
                    if status == "completed":
                        print("✅ Document processing completed!")
                        await test_search_functionality(session, headers)
                        break
                    elif status == "failed":
                        print("❌ Document processing failed")
                        break
                    else:
                        print(f"   Status: {status}, waiting...")
                        await asyncio.sleep(5)
                
                else:
                    print(f"❌ Status check failed: {response.status}")
                    break
        
        except Exception as e:
            print(f"❌ Status check error: {e}")
            break
        
        attempt += 1
    
    if attempt >= max_attempts:
        print("⏰ Processing timeout - check Celery worker logs")

async def test_search_functionality(session, headers):
    """Test search functionality after processing"""
    
    print("\n6️⃣ SEARCH FUNCTIONALITY TEST")
    
    try:
        # Test Elasticsearch health via API
        async with session.get(
            'http://localhost:5000/api/admin/elasticsearch/health',
            headers=headers
        ) as response:
            
            if response.status == 200:
                es_health = await response.json()
                print(f"✅ Elasticsearch Health: {es_health}")
            else:
                print(f"❌ Elasticsearch health check: {response.status}")
        
        # Test embeddings count
        async with session.get(
            'http://localhost:5000/api/admin/embeddings/count',
            headers=headers
        ) as response:
            
            if response.status == 200:
                count_data = await response.json()
                print(f"✅ Embeddings Count: {count_data}")
            else:
                print(f"❌ Embeddings count check: {response.status}")
        
        # Test user search (if search endpoint exists)
        search_query = {
            "query": "test legal document",
            "limit": 5
        }
        
        async with session.post(
            'http://localhost:5000/api/user/search',
            json=search_query,
            headers=headers
        ) as response:
            
            if response.status == 200:
                search_results = await response.json()
                print(f"✅ Search Test: {search_results}")
            else:
                print(f"❌ Search test: {response.status}")
                error_text = await response.text()
                print(f"   Error: {error_text}")
    
    except Exception as e:
        print(f"❌ Search test failed: {e}")

def create_simple_pdf():
    """Create a simple PDF for testing"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Add some Turkish legal text
        text_lines = [
            "TEST HUKUKI BELGE",
            "",
            "Sosyal Güvenlik Kapsamı:",
            "1. Sigortalılık şartları ve yükümlülükleri",
            "2. Prim ödeme usul ve esasları",
            "3. Sigorta tazminatları ve haklar",
            "",
            "İş Sağlığı ve Güvenliği:",
            "- İşveren yükümlülükleri",
            "- İşçi hakları ve sorumlulukları",
            "- Risk değerlendirmesi gereklilikleri",
            "",
            "Vergi Düzenlemeleri:",
            "- Gelir vergisi muafiyetleri",
            "- KDV istisnaları",
            "- Stopaj uygulamaları"
        ]
        
        y = 750
        for line in text_lines:
            p.drawString(100, y, line)
            y -= 25
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError:
        # Fallback: create a minimal PDF manually
        return create_minimal_pdf()

def create_minimal_pdf():
    """Create minimal PDF using raw PDF format"""
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
/Length 109
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Legal Document) Tj
0 -20 Td
(Sosyal Guvenlik Sigortalilk Sartlari) Tj
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
365
%%EOF"""
    return pdf_content

if __name__ == "__main__":
    asyncio.run(test_full_document_upload())