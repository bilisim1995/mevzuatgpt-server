#!/usr/bin/env python3
"""
Admin endpoint'lerini test et
"""
import requests
import json

BASE_URL = "http://0.0.0.0:5000"

def test_admin_endpoints_without_auth():
    """Admin endpoint'lerini authentication olmadan test et - security kontrolü"""
    
    print("🔐 AUTHENTICATION OLMADAN ENDPOINT TESTİ:")
    print("=" * 50)
    
    # Test endpoints
    endpoints = [
        "/api/admin/documents",
        "/api/admin/elasticsearch/health", 
        "/api/admin/embeddings/count"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            print(f"📋 {endpoint}")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:100]}...")
            print()
            
        except Exception as e:
            print(f"❌ Error testing {endpoint}: {e}")
            print()

def show_admin_endpoints_documentation():
    """Admin panel endpoint dokümantasyonu"""
    print("📚 ADMIN PANEL API ENDPOINT'LERİ:")
    print("=" * 50)
    print("""
🔑 Authentication Required:
Authorization: Bearer <token>

📋 Document Management:
GET  /api/admin/documents                    # List all documents
GET  /api/admin/documents/{document_id}      # Get document details  
POST /api/admin/upload-document              # Upload new PDF
DELETE /api/admin/documents/{document_id}    # Complete deletion

📊 System Monitoring:
GET  /api/admin/elasticsearch/health         # ES cluster health
GET  /api/admin/embeddings/count             # Total embeddings

🎯 Admin Features:
- Bunny.net URL generation (3-tier fallback)
- Elasticsearch embedding counts
- File size calculations  
- Complete deletion (DB + Bunny.net + ES)
- Error handling and detailed responses
""")

if __name__ == "__main__":
    # Test without auth to verify security
    test_admin_endpoints_without_auth()
    
    # Show documentation
    show_admin_endpoints_documentation()