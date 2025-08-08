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
            # Build SQL query for vector similarity search
            # Using cosine similarity via pgvector extension
            query = """
            SELECT 
                e.id,
                e.document_id,
                e.content,
                e.metadata,
                e.created_at,
                d.title as document_title,
                d.category,
                d.source_institution,
                d.publish_date,
                1 - (e.embedding <=> %s) as similarity_score
            FROM mevzuat_embeddings e
            JOIN mevzuat_documents d ON e.document_id = d.id
            WHERE d.status = 'active' 
                AND d.processing_status = 'completed'
                AND (1 - (e.embedding <=> %s)) >= %s
            """
            
            params = [query_embedding, query_embedding, similarity_threshold]
            
            # Add category filter if specified
            if category_filter:
                query += " AND d.category = %s"
                params.append(category_filter)
            
            query += " ORDER BY similarity_score DESC LIMIT %s"
            params.append(limit)
            
            # Execute raw SQL query for vector search
            result = await self.db.execute(query, params)
            rows = result.fetchall()
            
            # Convert results to dictionaries
            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "document_id": row[1],
                    "content": row[2],
                    "metadata": row[3] or {},
                    "created_at": row[4],
                    "document_title": row[5],
                    "category": row[6],
                    "source_institution": row[7],
                    "publish_date": row[8],
                    "similarity_score": float(row[9])
                })
            
            logger.info(f"Found {len(results)} similar embeddings")
            
            return results
            
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
