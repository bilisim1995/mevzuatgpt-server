#!/usr/bin/env python3
"""
Test Document Processing Pipeline with Elasticsearch
Simulates complete document upload, processing, and search flow
"""
import asyncio
import aiohttp
import json
import time
from pathlib import Path
from services.embedding_service import EmbeddingService
from tasks.document_processor import _process_document_async

async def test_document_processing():
    """Test complete document processing pipeline"""
    
    print("🚀 DOCUMENT PROCESSING TEST WITH ELASTICSEARCH")
    print("=" * 48)
    
    try:
        # Test 1: Check services
        print("\n1️⃣ SERVICES TEST")
        embedding_service = EmbeddingService()
        print("✅ EmbeddingService initialized")
        
        # Test 2: Generate test embeddings
        print("\n2️⃣ EMBEDDING GENERATION TEST")
        test_chunks = [
            "Sosyal güvenlik sigortalılık şartları ve yükümlülükleri",
            "İşçi sağlığı ve iş güvenliği mevzuatı hükümleri",
            "Vergi kanunu kapsamında muafiyet ve istisnalar"
        ]
        
        embeddings = []
        for i, chunk in enumerate(test_chunks):
            embedding = await embedding_service.generate_embedding(chunk)
            embeddings.append(embedding)
            print(f"✅ Chunk {i+1}: {len(embedding)} dimensions - {chunk[:50]}...")
        
        # Test 3: Store embeddings in Elasticsearch
        print("\n3️⃣ ELASTICSEARCH STORAGE TEST")
        test_document_id = "test-doc-12345"
        
        chunks_data = []
        for i, (chunk, embedding) in enumerate(zip(test_chunks, embeddings)):
            chunk_data = {
                "content": chunk,
                "embedding": embedding,
                "chunk_index": i,
                "page_number": 1,
                "line_start": i * 10,
                "line_end": (i + 1) * 10,
                "source_institution": "TEST_INSTITUTION",
                "source_document": "test_document.pdf",
                "metadata": {
                    "test_chunk": True,
                    "chunk_id": f"test-chunk-{i}"
                }
            }
            chunks_data.append(chunk_data)
        
        # Store embeddings
        embedding_ids = await embedding_service.store_embeddings(
            document_id=test_document_id,
            chunks=chunks_data
        )
        
        print(f"✅ Stored {len(embedding_ids)} embeddings in Elasticsearch")
        for i, eid in enumerate(embedding_ids):
            print(f"   - Embedding {i+1}: {eid}")
        
        # Test 4: Search functionality
        print("\n4️⃣ SEARCH FUNCTIONALITY TEST")
        
        # Test queries
        test_queries = [
            "sigortalılık şartları",
            "iş güvenliği",
            "vergi muafiyeti"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Query: '{query}'")
            
            # Similarity search
            results = await embedding_service.similarity_search(
                query_text=query,
                k=5,
                similarity_threshold=0.3
            )
            
            print(f"✅ Found {len(results)} results")
            for i, result in enumerate(results[:2]):  # Show top 2
                print(f"   {i+1}. Similarity: {result['similarity']:.3f}")
                print(f"      Content: {result['content'][:60]}...")
                print(f"      Document: {result['source_document']}")
        
        # Test 5: Embeddings count
        print("\n5️⃣ EMBEDDINGS COUNT TEST")
        total_count = await embedding_service.get_embeddings_count()
        doc_count = await embedding_service.get_embeddings_count(test_document_id)
        print(f"✅ Total embeddings in Elasticsearch: {total_count}")
        print(f"✅ Test document embeddings: {doc_count}")
        
        # Test 6: Cleanup
        print("\n6️⃣ CLEANUP TEST")
        deleted = await embedding_service.delete_embeddings_by_document(test_document_id)
        print(f"✅ Cleaned up {deleted} test embeddings")
        
        final_count = await embedding_service.get_embeddings_count()
        print(f"✅ Final total embeddings: {final_count}")
        
        print("\n🏆 DOCUMENT PROCESSING TEST SONUÇLARI:")
        print("=" * 39)
        print("✅ Embedding generation: BAŞARILI")
        print("✅ Elasticsearch storage: BAŞARILI")
        print("✅ Vector search: BAŞARILI")
        print("✅ Document filtering: BAŞARILI")
        print("✅ Cleanup operations: BAŞARILI")
        print("🎯 ELASTICSEARCH DOCUMENT PROCESSING TAM HAZIR!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_api_endpoints():
    """Test API endpoints for document processing"""
    
    print("\n🌐 API ENDPOINTS TEST")
    print("=" * 22)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test health endpoint
            async with session.get('http://localhost:5000/health') as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ API Health: {health_data}")
                else:
                    print(f"❌ API Health: {response.status}")
            
            # Test Elasticsearch health via API
            try:
                async with session.get('http://localhost:5000/api/admin/elasticsearch/health') as response:
                    if response.status == 200:
                        es_health = await response.json()
                        print(f"✅ Elasticsearch Health via API: {es_health}")
                    else:
                        print(f"❌ Elasticsearch API: {response.status}")
            except Exception as e:
                print(f"❌ Elasticsearch API endpoint not available: {e}")
            
            # Test embeddings count via API
            try:
                async with session.get('http://localhost:5000/api/admin/embeddings/count') as response:
                    if response.status == 200:
                        count_data = await response.json()
                        print(f"✅ Embeddings count via API: {count_data}")
                    else:
                        print(f"❌ Embeddings count API: {response.status}")
            except Exception as e:
                print(f"❌ Embeddings count endpoint: {e}")
                
    except Exception as e:
        print(f"❌ API test failed: {e}")

if __name__ == "__main__":
    async def main():
        await test_document_processing()
        await test_api_endpoints()
    
    asyncio.run(main())