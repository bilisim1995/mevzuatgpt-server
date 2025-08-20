"""
Supabase client for MevzuatGPT
Handles database operations via Supabase REST API
"""
import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
import asyncio

class SupabaseClient:
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    async def create_document(self, doc_data: dict) -> str:
        """Create a new document record"""
        try:
            # Map to actual database schema fields
            insert_data = {
                'title': doc_data.get('title'),
                'filename': doc_data.get('filename'), 
                'file_url': doc_data.get('file_url'),
                'file_size': doc_data.get('file_size'),
                'uploaded_by': doc_data.get('uploaded_by'),
                'status': 'active',  # Use 'active' instead of 'processing'
                'processing_status': 'pending',
                'metadata': doc_data.get('metadata', {})
            }
            
            # Add optional fields from metadata if provided - use category column only
            metadata = doc_data.get('metadata', {})
            if metadata.get('category'):
                insert_data['category'] = metadata['category']  # Use category column instead of document_type
            if metadata.get('source_institution'):
                insert_data['institution'] = metadata['source_institution']
            if metadata.get('description'):
                insert_data['content_preview'] = metadata['description'][:500]
                
            response = self.supabase.table('mevzuat_documents').insert(insert_data).execute()
            
            return response.data[0]['id']
        except Exception as e:
            print(f"Document creation error: {e}")
            raise
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            response = self.supabase.table('mevzuat_documents').select('*').eq('id', doc_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Get document error: {e}")
            return None
    
    async def update_document_status(self, doc_id: str, status: str, error: Optional[str] = None):
        """Update document processing status"""
        try:
            update_data = {'status': status}
            if error:
                update_data['processing_error'] = error
                
            response = self.supabase.table('mevzuat_documents').update(update_data).eq('id', doc_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Update document status error: {e}")
            raise
    
    async def create_embedding_with_sources(self, doc_id: str, content: str, embedding: List[float], 
                                          chunk_index: int = 0, page_number: Optional[int] = None, 
                                          line_start: Optional[int] = None, line_end: Optional[int] = None, 
                                          metadata: Optional[Dict[str, Any]] = None):
        """Create an embedding record with enhanced source information"""
        try:
            embedding_data = {
                'document_id': doc_id,
                'content': content,
                'embedding': embedding,
                'chunk_index': chunk_index,
                'metadata': metadata or {}
            }
            
            # Add source information if provided
            if page_number is not None:
                embedding_data['page_number'] = page_number
            if line_start is not None:
                embedding_data['line_start'] = line_start
            if line_end is not None:
                embedding_data['line_end'] = line_end
            
            response = self.supabase.table('mevzuat_embeddings').insert(embedding_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Create embedding with sources error: {e}")
            raise
    
    async def create_embedding(self, doc_id: str, content: str, embedding: List[float], chunk_index: int = 0, metadata: Optional[Dict[str, Any]] = None):
        """Create an embedding record with basic metadata (backward compatibility)"""
        try:
            response = self.supabase.table('mevzuat_embeddings').insert({
                'document_id': doc_id,
                'content': content,
                'embedding': embedding,
                'chunk_index': chunk_index,
                'metadata': metadata or {}
            }).execute()
            
            return response.data[0]['id']
        except Exception as e:
            print(f"Embedding creation error: {e}")
            raise
    
    async def search_embeddings(self, query_embedding: List[float], limit: int = 10, threshold: float = 0.7):
        """Search embeddings using vector similarity (fallback method)"""
        try:
            # Fallback: get all embeddings and calculate similarity client-side
            # This is temporary until vector search function is properly set up
            response = self.supabase.table('mevzuat_embeddings').select(
                '*, mevzuat_documents(title, filename, status)'
            ).execute()
            
            results = []
            for item in response.data:
                if item['mevzuat_documents']['status'] == 'completed':
                    # Enhanced search results with metadata
                    metadata = item.get('metadata', {})
                    results.append({
                        'id': item['id'],
                        'document_id': item['document_id'],
                        'content': item['content'],
                        'page_number': item.get('page_number') or metadata.get('page_number'),
                        'line_start': item.get('line_start') or metadata.get('line_start'),
                        'line_end': item.get('line_end') or metadata.get('line_end'),
                        'similarity': 0.8,  # Mock similarity for now
                        'document_title': item['mevzuat_documents']['title'],
                        'document_filename': item['mevzuat_documents']['filename'],
                        'chunk_index': item.get('chunk_index', 0),
                        'metadata': metadata,
                        'text_preview': metadata.get('text_preview', item['content'][:200])
                    })
            
            return results[:limit]
        except Exception as e:
            print(f"Embedding search error: {e}")
            return []
    
    async def get_all_documents(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all documents, optionally filtered by status"""
        try:
            query = self.supabase.table('mevzuat_documents').select('*')
            if status:
                query = query.eq('status', status)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Get all documents error: {e}")
            return []
    
    async def log_search(self, user_id: str, query: str, results_count: int, execution_time: float):
        """Log search query"""
        try:
            response = self.supabase.table('search_logs').insert({
                'user_id': user_id,
                'query': query,
                'results_count': results_count,
                'execution_time': execution_time
            }).execute()
            
            return response.data[0]['id']
        except Exception as e:
            print(f"Search log error: {e}")
            return None

# Global instance
supabase_client = SupabaseClient()