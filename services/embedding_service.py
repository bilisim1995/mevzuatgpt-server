"""
Elasticsearch Embedding Service - Ultra Optimized for 2048 Dimensions
Handles OpenAI text-embedding-3-large + Elasticsearch vector operations
CLEAN VERSION - No Supabase vector dependencies
"""

from typing import List, Dict, Any, Optional
import logging
import openai
import asyncio

from core.config import get_settings
from services.elasticsearch_service import ElasticsearchService
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Clean Elasticsearch-based embedding service with OpenAI text-embedding-3-large"""
    
    def __init__(self, *args, **kwargs):
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
            # Ensure text is properly encoded for OpenAI API
            try:
                # Handle Turkish characters properly for API call
                if isinstance(text, bytes):
                    processed_text = text.decode('utf-8', errors='replace')
                else:
                    processed_text = str(text)
                
                # Normalize Unicode for consistency
                import unicodedata
                processed_text = unicodedata.normalize('NFC', processed_text.strip())
                
                # Ensure text length is reasonable for API
                if len(processed_text) > 8000:  # OpenAI limit safety
                    processed_text = processed_text[:8000]
                    logger.warning(f"Text truncated to 8000 characters for embedding generation")
                
            except Exception as text_processing_error:
                logger.warning(f"Text processing issue: {text_processing_error}")
                processed_text = str(text).strip()[:8000]
            
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.embeddings.create(
                    model=self.settings.OPENAI_EMBEDDING_MODEL,  # text-embedding-3-large
                    input=processed_text,
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

    # Legacy compatibility methods for existing code
    async def search_similar_embeddings(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        similarity_threshold: float = 0.7,
        category_filter: Optional[str] = None,
        document_ids_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Use similarity_search() instead
        Legacy compatibility wrapper for Elasticsearch similarity search
        """
        logger.warning("search_similar_embeddings() is deprecated, use similarity_search() instead")
        
        # Use Elasticsearch via similarity search
        results = await self.elasticsearch_service.similarity_search(
            query_vector=query_embedding,
            k=limit,
            institution_filter=category_filter,
            document_ids=document_ids_filter,
            similarity_threshold=similarity_threshold
        )
        
        # Format for backward compatibility
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result["id"],
                "document_id": result["document_id"],
                "document_title": result.get("source_document", "Unknown Document"),
                "content": result["content"],
                "metadata": result.get("metadata", {}),
                "category": result.get("source_institution"),
                "source_institution": result.get("source_institution"),
                "publish_date": None,
                "similarity_score": result["similarity"]
            })
        
        return formatted_results