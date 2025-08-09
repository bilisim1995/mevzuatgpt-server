"""
Fix empty embeddings by generating embeddings for existing documents
"""
import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.supabase_client import supabase_client
from services.embedding_service import EmbeddingService

async def fix_empty_embeddings():
    """Generate embeddings for documents that don't have them"""
    print("🔧 Fixing empty embeddings...")
    
    try:
        service_client = supabase_client.get_client(use_service_key=True)
        
        # Get documents without embeddings
        docs_response = service_client.table('mevzuat_documents').select('*').execute()
        
        if not docs_response.data:
            print("❌ No documents found!")
            return
            
        print(f"📄 Found {len(docs_response.data)} documents")
        
        # Check existing embeddings
        embeddings_response = service_client.table('mevzuat_embeddings').select('document_id').execute()
        existing_doc_ids = set([e['document_id'] for e in embeddings_response.data]) if embeddings_response.data else set()
        
        print(f"📊 Existing embeddings for {len(existing_doc_ids)} documents")
        
        # Initialize embedding service
        embedding_service = EmbeddingService()
        
        # Process each document
        for doc in docs_response.data:
            doc_id = doc['id']
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')
            
            print(f"\n📝 Processing: {title}")
            
            if doc_id in existing_doc_ids:
                print("  ✅ Already has embeddings, skipping")
                continue
                
            if not content:
                print("  ⚠️  No content found, using title for embedding")
                content = f"Bu dokuman {title} konusunu kapsamaktadır. Türkiye sigorta sektörü ile ilgili yasal düzenlemeler ve mevzuat bilgileri içermektedir."
                
            try:
                # Generate embedding for document content
                print(f"  🧠 Generating embedding for content ({len(content)} chars)")
                
                # Use content or title + content for embedding
                text_to_embed = f"{title}\n\n{content}"
                embedding_vector = await embedding_service.generate_embedding(text_to_embed)
                
                print(f"  ✅ Generated {len(embedding_vector)}-dimensional embedding")
                
                # Insert embedding into database
                embedding_data = {
                    "document_id": doc_id,
                    "content": text_to_embed[:1000] + "..." if len(text_to_embed) > 1000 else text_to_embed,
                    "embedding": embedding_vector,  # This will be converted to vector format by Supabase
                    "metadata": {
                        "chunk_index": 0,
                        "chunk_type": "full_document",
                        "source_title": title,
                        "generation_method": "automatic_fix"
                    }
                }
                
                # Insert with service client
                insert_response = service_client.table('mevzuat_embeddings').insert(embedding_data).execute()
                
                if insert_response.data:
                    print(f"  ✅ Embedding saved successfully!")
                else:
                    print(f"  ❌ Failed to save embedding")
                    
            except Exception as doc_error:
                print(f"  ❌ Error processing document: {doc_error}")
                continue
        
        # Final verification
        print("\n🔍 Final verification...")
        final_embeddings = service_client.table('mevzuat_embeddings').select('id').execute()
        final_docs = service_client.table('mevzuat_documents').select('id').execute()
        
        print(f"📊 Final state:")
        print(f"  - Documents: {len(final_docs.data) if final_docs.data else 0}")
        print(f"  - Embeddings: {len(final_embeddings.data) if final_embeddings.data else 0}")
        
        if final_embeddings.data:
            print("✅ Embeddings fixed! Search should work now.")
        else:
            print("❌ Still no embeddings. Check errors above.")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_empty_embeddings())