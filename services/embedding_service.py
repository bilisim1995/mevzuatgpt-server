"""
Embedding service
Handles OpenAI embedding generation and vector database operations
"""

from typing import List, Dict, Any, Optional
import logging
import openai
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from core.config import settings
from models.database import Embedding, Document
from models.schemas import EmbeddingCreate, EmbeddingResponse
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service class for embedding generation and management"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using OpenAI API
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of embedding values
            
        Raises:
            AppException: If embedding generation fails
        """
        try:
            # Run OpenAI API call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.embeddings.create(
                    model="text-embedding-3-small",  # Force 1536 dimensions
                    input=text.strip(),
                    encoding_format="float"
                )
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"Generated embedding for text (length: {len(text)}, dimension: {len(embedding)})")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise AppException(
                message="Failed to generate text embedding",
                detail=str(e),
                error_code="EMBEDDING_GENERATION_FAILED"
            )
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of embedding lists
            
        Raises:
            AppException: If batch embedding generation fails
        """
        try:
            # OpenAI supports batch embedding generation
            # Clean and prepare texts
            clean_texts = [text.strip() for text in texts if text.strip()]
            
            if not clean_texts:
                return []
            
            # Run batch embedding generation
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.embeddings.create(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    input=clean_texts,
                    encoding_format="float"
                )
            )
            
            embeddings = [item.embedding for item in response.data]
            
            logger.info(f"Generated {len(embeddings)} embeddings in batch")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings batch: {str(e)}")
            raise AppException(
                message="Failed to generate text embeddings",
                detail=str(e),
                error_code="BATCH_EMBEDDING_GENERATION_FAILED"
            )
    
    async def store_embeddings(
        self, 
        document_id: UUID, 
        chunks: List[Dict[str, Any]]
    ) -> List[EmbeddingResponse]:
        """
        Store embeddings in database
        
        Args:
            document_id: Document UUID
            chunks: List of text chunks with embeddings and metadata
            
        Returns:
            List of stored embeddings
            
        Raises:
            AppException: If storage fails
        """
        try:
            # Delete existing embeddings for this document
            await self.delete_embeddings_by_document(document_id)
            
            # Create embedding records
            embedding_records = []
            for chunk in chunks:
                # Ensure embedding is a list of floats, not a string
                embedding_vector = chunk["embedding"]
                if isinstance(embedding_vector, str):
                    # If it's a string, try to parse it as a list
                    import json
                    try:
                        embedding_vector = json.loads(embedding_vector)
                    except:
                        logger.error(f"Failed to parse embedding string: {embedding_vector[:100]}...")
                        raise AppException("Invalid embedding format")
                
                embedding_record = Embedding(
                    document_id=document_id,
                    content=chunk["content"],
                    embedding=embedding_vector,
                    metadata=chunk.get("metadata", {})
                )
                embedding_records.append(embedding_record)
            
            # Bulk insert embeddings
            self.db.add_all(embedding_records)
            await self.db.flush()
            
            # Refresh to get IDs
            for record in embedding_records:
                await self.db.refresh(record)
            
            logger.info(f"Stored {len(embedding_records)} embeddings for document {document_id}")
            
            # Convert to response models
            embedding_responses = []
            for record in embedding_records:
                embedding_responses.append(EmbeddingResponse(
                    id=record.id,
                    document_id=record.document_id,
                    content=record.content,
                    metadata=record.metadata,
                    created_at=record.created_at
                ))
            
            return embedding_responses
            
        except Exception as e:
            logger.error(f"Failed to store embeddings for document {document_id}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to store embeddings",
                detail=str(e),
                error_code="EMBEDDING_STORAGE_FAILED"
            )
    
    async def delete_embeddings_by_document(self, document_id: UUID) -> bool:
        """
        Delete all embeddings for a document
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if deletion successful
        """
        try:
            stmt = delete(Embedding).where(Embedding.document_id == document_id)
            result = await self.db.execute(stmt)
            await self.db.flush()
            
            logger.info(f"Deleted {result.rowcount} embeddings for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings for document {document_id}: {str(e)}")
            return False
    
    async def search_similar_embeddings(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        similarity_threshold: float = 0.7,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings using vector similarity
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            category_filter: Optional category filter
            
        Returns:
            List of similar embeddings with similarity scores
        """
        try:
            # Use Supabase REST API directly for vector similarity (bypass SQLAlchemy)
            from models.supabase_client import supabase_client
            import json
            
            # Try Supabase stored function first
            try:
                response = supabase_client.supabase.rpc('search_embeddings', {
                    'query_embedding': query_embedding,
                    'match_threshold': similarity_threshold,
                    'match_count': limit
                }).execute()
                
                if response.data:
                    # Convert to expected format
                    results = []
                    for row in response.data:
                        results.append({
                            "id": row["id"],
                            "document_id": row["document_id"], 
                            "content": row["content"],
                            "metadata": row.get("metadata", {}),
                            "created_at": None,  # Not needed for search
                            "document_title": row["document_title"],
                            "category": None,  # Not in function yet
                            "source_institution": None,  # Not in function yet  
                            "publish_date": None,  # Not in function yet
                            "similarity_score": float(row["similarity"])
                        })
                    
                    logger.info(f"Found {len(results)} similar embeddings via Supabase RPC")
                    return results
                    
            except Exception as rpc_error:
                logger.warning(f"Supabase RPC search failed, trying direct table query: {rpc_error}")
            
            # Fallback: Use direct Supabase table query without SQLAlchemy
            try:
                # Query embeddings directly from Supabase (only existing columns) - fixed join
                embedding_response = supabase_client.supabase.table('mevzuat_embeddings') \
                    .select('id, document_id, content, metadata, embedding') \
                    .execute()
                    
                # Get document info separately to avoid join issues
                document_titles = {}
                if embedding_response.data:
                    doc_ids = list(set([row['document_id'] for row in embedding_response.data]))
                    doc_response = supabase_client.supabase.table('mevzuat_documents') \
                        .select('id, title') \
                        .in_('id', doc_ids) \
                        .execute()
                    
                    if doc_response.data:
                        document_titles = {doc['id']: doc['title'] for doc in doc_response.data}
                
                if embedding_response.data:
                    # Calculate cosine similarity in Python (fallback)
                    import numpy as np
                    
                    results = []
                    for embedding_row in embedding_response.data:
                        # Get embedding vector
                        stored_embedding = embedding_row.get('embedding')
                        if not stored_embedding:
                            continue
                        
                        # Parse embedding if it's stored as string
                        if isinstance(stored_embedding, str):
                            try:
                                stored_embedding = json.loads(stored_embedding)
                            except:
                                continue  # Skip invalid embeddings
                        
                        # Ensure both vectors have same length
                        if len(stored_embedding) != len(query_embedding):
                            continue
                            
                        # Calculate cosine similarity
                        stored_vec = np.array(stored_embedding)
                        query_vec = np.array(query_embedding)
                        
                        # Cosine similarity
                        similarity = np.dot(stored_vec, query_vec) / (np.linalg.norm(stored_vec) * np.linalg.norm(query_vec))
                        
                        if similarity >= similarity_threshold:
                            document_id = embedding_row["document_id"]
                            
                            results.append({
                                "id": embedding_row["id"],
                                "document_id": document_id,
                                "content": embedding_row["content"],
                                "metadata": embedding_row.get("metadata", {}),
                                "created_at": None,
                                "document_title": document_titles.get(document_id, "Unknown Document"),
                                "category": None,  # Not available yet
                                "source_institution": None,  # Not available yet
                                "publish_date": None,  # Not available yet
                                "similarity_score": float(similarity)
                            })
                    
                    # Sort by similarity and limit
                    results.sort(key=lambda x: x["similarity_score"], reverse=True)
                    results = results[:limit]
                    
                    logger.info(f"Found {len(results)} similar embeddings via direct Supabase query")
                    return results
                    
            except Exception as direct_error:
                logger.error(f"Direct Supabase query also failed: {direct_error}")
            
            # Final fallback: empty results
            logger.warning("All search methods failed, returning empty results")
            return []
            
        except Exception as e:
            logger.error(f"Failed to search similar embeddings: {str(e)}")
            return []
    
    async def get_document_embeddings(self, document_id: UUID) -> List[EmbeddingResponse]:
        """
        Get all embeddings for a document
        
        Args:
            document_id: Document UUID
            
        Returns:
            List of embeddings for the document
        """
        try:
            stmt = (
                select(Embedding)
                .where(Embedding.document_id == document_id)
                .order_by(Embedding.created_at)
            )
            
            result = await self.db.execute(stmt)
            embeddings = result.scalars().all()
            
            # Convert to response models
            embedding_responses = []
            for embedding in embeddings:
                embedding_responses.append(EmbeddingResponse(
                    id=embedding.id,
                    document_id=embedding.document_id,
                    content=embedding.content,
                    metadata=embedding.metadata,
                    created_at=embedding.created_at
                ))
            
            return embedding_responses
            
        except Exception as e:
            logger.error(f"Failed to get embeddings for document {document_id}: {str(e)}")
            return []
    
    async def get_embedding_stats(self) -> Dict[str, Any]:
        """
        Get embedding statistics
        
        Returns:
            Dictionary with embedding statistics
        """
        try:
            # Count total embeddings
            from sqlalchemy import func
            total_query = select(func.count(Embedding.id))
            total_result = await self.db.execute(total_query)
            total_embeddings = total_result.scalar()
            
            # Count embeddings by document
            doc_query = select(func.count(func.distinct(Embedding.document_id)))
            doc_result = await self.db.execute(doc_query)
            documents_with_embeddings = doc_result.scalar()
            
            return {
                "total_embeddings": total_embeddings,
                "documents_with_embeddings": documents_with_embeddings,
                "average_chunks_per_document": (
                    total_embeddings / documents_with_embeddings 
                    if documents_with_embeddings > 0 else 0
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {str(e)}")
            return {
                "total_embeddings": 0,
                "documents_with_embeddings": 0,
                "average_chunks_per_document": 0
            }
