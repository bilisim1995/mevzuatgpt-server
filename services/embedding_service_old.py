"""
Elasticsearch Embedding Service - Ultra Optimized for 2048 Dimensions
Handles OpenAI text-embedding-3-large + Elasticsearch vector operations
"""

from typing import List, Dict, Any, Optional
import logging
import openai
import asyncio
from uuid import UUID

from core.config import get_settings
from services.elasticsearch_service import ElasticsearchService
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Elasticsearch-based embedding service with OpenAI text-embedding-3-large"""
    
    def __init__(self):
        self.settings = get_settings()
        self.openai_client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
        self.elasticsearch_service = ElasticsearchService()
        
        logger.info("EmbeddingService initialized with Elasticsearch backend")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate 2048-dimensional embedding using OpenAI text-embedding-3-large
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of 2048 embedding values optimized for Elasticsearch
            
        Raises:
            AppException: If embedding generation fails
        """
        try:
            # Run OpenAI API call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.embeddings.create(
                    model=self.settings.OPENAI_EMBEDDING_MODEL,  # text-embedding-3-large
                    input=text.strip(),
                    encoding_format="float",
                    dimensions=self.settings.OPENAI_EMBEDDING_DIMENSIONS  # 2048 for ES optimization
                )
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"Generated 2048D embedding for text (length: {len(text)}, dimensions: {len(embedding)})")
            
            # Verify dimensions
            if len(embedding) != self.settings.OPENAI_EMBEDDING_DIMENSIONS:
                raise AppException(
                    message=f"Invalid embedding dimensions: {len(embedding)}, expected: {self.settings.OPENAI_EMBEDDING_DIMENSIONS}",
                    error_code="INVALID_EMBEDDING_DIMENSIONS"
                )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate 2048D embedding: {str(e)}")
            raise AppException(
                message="Failed to generate text embedding",
                detail=str(e),
                error_code="EMBEDDING_GENERATION_FAILED"
            )
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate 2048-dimensional embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to generate embeddings for
            
        Returns:
            List of 2048-dimensional embedding lists
            
        Raises:
            AppException: If batch embedding generation fails
        """
        try:
            # OpenAI supports batch embedding generation
            # Clean and prepare texts
            clean_texts = [text.strip() for text in texts if text.strip()]
            
            if not clean_texts:
                return []
            
            # Run batch embedding generation with text-embedding-3-large
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.embeddings.create(
                    model=self.settings.OPENAI_EMBEDDING_MODEL,  # text-embedding-3-large
                    input=clean_texts,
                    encoding_format="float",
                    dimensions=self.settings.OPENAI_EMBEDDING_DIMENSIONS  # 2048
                )
            )
            
            embeddings = [item.embedding for item in response.data]
            
            # Verify all embeddings have correct dimensions
            for i, embedding in enumerate(embeddings):
                if len(embedding) != self.settings.OPENAI_EMBEDDING_DIMENSIONS:
                    raise AppException(
                        message=f"Invalid embedding dimensions for text {i}: {len(embedding)}, expected: {self.settings.OPENAI_EMBEDDING_DIMENSIONS}",
                        error_code="INVALID_BATCH_EMBEDDING_DIMENSIONS"
                    )
            
            logger.info(f"Generated {len(embeddings)} 2048D embeddings in batch")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate 2048D embeddings batch: {str(e)}")
            raise AppException(
                message="Failed to generate text embeddings",
                detail=str(e),
                error_code="BATCH_EMBEDDING_GENERATION_FAILED"
            )
    
    async def store_embeddings(
        self, 
        document_id: str, 
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Store embeddings in Elasticsearch with ultra optimization
        
        Args:
            document_id: Document UUID as string
            chunks: List of text chunks with embeddings and metadata
            
        Returns:
            List of Elasticsearch document IDs
            
        Raises:
            AppException: If storage fails
        """
        try:
            # Delete existing embeddings for this document
            await self.delete_embeddings_by_document(document_id)
            
            # Prepare embeddings data for Elasticsearch bulk insert
            embeddings_data = []
            for i, chunk in enumerate(chunks):
                # Ensure embedding is a list of floats
                embedding_vector = chunk["embedding"]
                if isinstance(embedding_vector, str):
                    import json
                    try:
                        embedding_vector = json.loads(embedding_vector)
                    except:
                        logger.error(f"Failed to parse embedding string for chunk {i}")
                        raise AppException("Invalid embedding format")
                
                # Verify 2048 dimensions
                if len(embedding_vector) != self.settings.OPENAI_EMBEDDING_DIMENSIONS:
                    raise AppException(
                        message=f"Invalid embedding dimensions for chunk {i}: {len(embedding_vector)}, expected: {self.settings.OPENAI_EMBEDDING_DIMENSIONS}",
                        error_code="INVALID_EMBEDDING_DIMENSIONS"
                    )
                
                # Prepare Elasticsearch document
                embedding_data = {
                    "document_id": document_id,
                    "content": chunk["content"],
                    "embedding": embedding_vector,
                    "chunk_index": i,
                    "page_number": chunk.get("page_number"),
                    "line_start": chunk.get("line_start"),
                    "line_end": chunk.get("line_end"),
                    "source_institution": chunk.get("source_institution"),
                    "source_document": chunk.get("source_document"),
                    "metadata": chunk.get("metadata", {})
                }
                embeddings_data.append(embedding_data)
            
            # Bulk insert to Elasticsearch
            embedding_ids = await self.elasticsearch_service.bulk_create_embeddings(embeddings_data)
            
            logger.info(f"Stored {len(embedding_ids)} embeddings in Elasticsearch for document {document_id}")
            
            return embedding_ids
            
        except Exception as e:
            logger.error(f"Failed to store embeddings for document {document_id}: {str(e)}")
            raise AppException(
                message="Failed to store embeddings in Elasticsearch",
                detail=str(e),
                error_code="ELASTICSEARCH_STORAGE_FAILED"
            )
    
    async def delete_embeddings_by_document(self, document_id: str) -> bool:
        """
        Delete all embeddings for a document from Elasticsearch
        
        Args:
            document_id: Document UUID as string
            
        Returns:
            True if deletion successful
        """
        try:
            deleted_count = await self.elasticsearch_service.delete_document_embeddings(document_id)
            logger.info(f"Deleted {deleted_count} embeddings from Elasticsearch for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings for document {document_id}: {str(e)}")
            return False
    
    async def similarity_search(
        self,
        query_text: str,
        k: int = 10,
        institution_filter: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity search using Elasticsearch
        
        Args:
            query_text: Text to search for
            k: Number of results to return
            institution_filter: Filter by source institution
            document_ids: Filter by specific document IDs
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of search results with similarity scores
        """
        try:
            # Generate embedding for query text
            query_embedding = await self.generate_embedding(query_text)
            
            # Perform similarity search in Elasticsearch
            results = await self.elasticsearch_service.similarity_search(
                query_vector=query_embedding,
                k=k,
                institution_filter=institution_filter,
                document_ids=document_ids,
                similarity_threshold=similarity_threshold
            )
            
            logger.info(f"Similarity search found {len(results)} results for query: {query_text[:50]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise AppException(
                message="Failed to perform similarity search",
                detail=str(e),
                error_code="SIMILARITY_SEARCH_FAILED"
            )
    
    async def hybrid_search(
        self,
        query_text: str,
        k: int = 10,
        institution_filter: Optional[str] = None,
        vector_boost: float = 2.0,
        text_boost: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and text search
        
        Args:
            query_text: Text to search for
            k: Number of results to return
            institution_filter: Filter by source institution
            vector_boost: Weight for vector search
            text_boost: Weight for text search
            
        Returns:
            List of hybrid search results
        """
        try:
            # Generate embedding for query text
            query_embedding = await self.generate_embedding(query_text)
            
            # Perform hybrid search in Elasticsearch
            results = await self.elasticsearch_service.hybrid_search(
                query_vector=query_embedding,
                query_text=query_text,
                k=k,
                institution_filter=institution_filter,
                vector_boost=vector_boost,
                text_boost=text_boost
            )
            
            logger.info(f"Hybrid search found {len(results)} results for query: {query_text[:50]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise AppException(
                message="Failed to perform hybrid search",
                detail=str(e),
                error_code="HYBRID_SEARCH_FAILED"
            )
    
    async def get_embeddings_count(self, document_id: Optional[str] = None) -> int:
        """
        Get total embeddings count from Elasticsearch
        
        Args:
            document_id: Optional document ID to filter by
            
        Returns:
            Number of embeddings
        """
        try:
            count = await self.elasticsearch_service.get_embeddings_count(document_id)
            return count
            
        except Exception as e:
            logger.error(f"Failed to get embeddings count: {str(e)}")
            return 0
    
    async def search_similar_embeddings(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        similarity_threshold: float = 0.3,
        category_filter: Optional[str] = None,
        document_ids_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings using vector similarity
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            category_filter: Optional category filter
            document_ids_filter: Optional list of document IDs to limit search to
            
        Returns:
            List of similar embeddings with similarity scores
        """
        try:
            # Use Supabase REST API directly for vector similarity (bypass SQLAlchemy)
            from core.supabase_client import supabase_client
            import json
            
            # Skip RPC function - use direct query for reliability
            # RPC function may not handle threshold correctly or may not exist in production
            
            # Fallback: Use direct Supabase table query without SQLAlchemy
            try:
                # Query embeddings directly from Supabase using service client (bypass RLS)
                service_client = supabase_client.get_client(use_service_key=True)
                
                # Apply document ID filter if provided (for institution filtering)
                query = service_client.table('mevzuat_embeddings') \
                    .select('id, document_id, content, metadata, embedding')
                
                if document_ids_filter:
                    query = query.in_('document_id', document_ids_filter)
                    logger.info(f"Applying document ID filter: {len(document_ids_filter)} documents")
                
                embedding_response = query.execute()
                    
                # Get document info separately to avoid join issues
                document_titles = {}
                if embedding_response.data:
                    doc_ids = list(set([row['document_id'] for row in embedding_response.data]))
                    doc_response = service_client.table('mevzuat_documents') \
                        .select('id, title') \
                        .in_('id', doc_ids) \
                        .execute()
                    
                    if doc_response.data:
                        document_titles = {doc['id']: doc['title'] for doc in doc_response.data}
                
                logger.info(f"Search Debug: Retrieved {len(embedding_response.data) if embedding_response.data else 0} embeddings from Supabase")
                
                if embedding_response.data:
                    # Calculate cosine similarity in Python (fallback)
                    import numpy as np
                    
                    results = []
                    processed_count = 0
                    error_count = 0
                    
                    for embedding_row in embedding_response.data:
                        processed_count += 1
                        
                        try:
                            # Get embedding vector
                            stored_embedding = embedding_row.get('embedding')
                            if not stored_embedding:
                                error_count += 1
                                continue
                            
                            # Parse embedding if it's stored as string
                            if isinstance(stored_embedding, str):
                                try:
                                    stored_embedding = json.loads(stored_embedding)
                                except Exception as parse_error:
                                    logger.warning(f"Failed to parse embedding JSON: {str(parse_error)[:100]}")
                                    error_count += 1
                                    continue
                            
                            # Ensure both vectors have same length
                            if len(stored_embedding) != len(query_embedding):
                                logger.warning(f"Embedding dimension mismatch: {len(stored_embedding)} vs {len(query_embedding)}")
                                error_count += 1
                                continue
                                
                            # Calculate cosine similarity
                            stored_vec = np.array(stored_embedding)
                            query_vec = np.array(query_embedding)
                            
                            # Cosine similarity
                            similarity = np.dot(stored_vec, query_vec) / (np.linalg.norm(stored_vec) * np.linalg.norm(query_vec))
                            
                            logger.debug(f"Calculated similarity: {similarity:.3f} for content: {embedding_row['content'][:50]}...")
                            
                            # Use dynamic threshold
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
                                
                        except Exception as row_error:
                            logger.error(f"Error processing embedding row: {str(row_error)}")
                            error_count += 1
                            continue
                    
                    logger.info(f"Search Debug: Processed {processed_count} embeddings, {error_count} errors, {len(results)} matches above threshold {similarity_threshold}")
                    
                    # Sort by similarity and limit
                    results.sort(key=lambda x: x["similarity_score"], reverse=True)
                    results = results[:limit]
                    
                    logger.info(f"Found {len(results)} similar embeddings via direct Supabase query (threshold: {similarity_threshold})")
                    
                    # Debug: Log top 3 results if any
                    for i, result in enumerate(results[:3]):
                        logger.info(f"Top result {i+1}: similarity={result['similarity_score']:.3f}, content={result['content'][:100]}")
                    
                    return results
                    
            except Exception as direct_error:
                logger.error(f"Direct Supabase query also failed: {direct_error}")
            
            # Final fallback: empty results
            logger.warning("All search methods failed, returning empty results")
            return []
            
        except Exception as e:
            logger.error(f"Failed to search similar embeddings: {str(e)}")
            return []
    
    async def get_document_embeddings(self, document_id: str) -> List[Dict[str, Any]]:
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
