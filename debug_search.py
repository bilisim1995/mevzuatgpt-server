"""
Debug script to test search functionality directly
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from core.supabase_client import supabase_client

async def test_search_direct():
    """Test search functionality directly without authentication"""
    print("🔍 Testing search functionality...")
    
    # Test 1: Check if embeddings exist (use service client to bypass RLS)
    try:
        service_client = supabase_client.get_client(use_service_key=True)
        response = service_client.table('mevzuat_embeddings').select('id').limit(5).execute()
        count = len(response.data) if response.data else 0
        print(f"✅ Found {count} embeddings in database (sample)")
    except Exception as e:
        print(f"❌ Error checking embeddings: {e}")
        print("This indicates RLS policy issues!")
    
    # Test 2: Check documents (use service client to bypass RLS)
    try:
        service_client = supabase_client.get_client(use_service_key=True)
        response = service_client.table('mevzuat_documents').select('id, title').limit(5).execute()
        print(f"✅ Found {len(response.data)} documents:")
        for doc in response.data[:3]:
            print(f"  - {doc.get('title', 'No title')}")
    except Exception as e:
        print(f"❌ Error checking documents: {e}")
        print("This indicates RLS policy issues!")
        return
    
    # Test 3: Test embedding search
    try:
        embedding_service = EmbeddingService()
        
        # Generate a test query embedding
        print("\n🧪 Testing query: 'Sigortalılık şartları'")
        query_embedding = await embedding_service.generate_embedding("Sigortalılık şartları nelerdir?")
        print(f"✅ Generated query embedding: {len(query_embedding)} dimensions")
        
        # Search for similar
        results = await embedding_service.search_similar_embeddings(
            query_embedding=query_embedding,
            limit=5,
            similarity_threshold=0.2  # Lower threshold for debugging
        )
        
        print(f"✅ Search returned {len(results)} results")
        
        if results:
            print("\n📋 Top results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i+1}. Similarity: {result['similarity_score']:.3f}")
                print(f"     Content: {result['content'][:100]}...")
                print(f"     Document: {result.get('document_title', 'Unknown')}")
                print()
        else:
            print("❌ No results found - this explains the 'no information' response!")
            
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_direct())