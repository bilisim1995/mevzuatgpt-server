"""
Search service for semantic search and AI-powered question answering
Handles vector similarity search and OpenAI chat completion integration
"""

from typing import List, Dict, Any, Optional
import logging
import openai
import asyncio
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from services.embedding_service import EmbeddingService
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class SearchService:
    """Service class for semantic search and AI-powered responses"""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()
        self.client = openai.OpenAI(api_key=self.settings.OPENAI_API_KEY)
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        similarity_threshold: float = 0.65,
        category_filter: Optional[str] = None,
        date_filter: Optional[Dict[str, date]] = None,
        document_ids_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity
        
        Args:
            query: Search query text
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            category_filter: Optional category filter
            date_filter: Optional date range filter
            
        Returns:
            List of search results with similarity scores
            
        Raises:
            AppException: If search fails
        """
        try:
            # Generate embedding for the search query
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform Elasticsearch vector similarity search
            results = await self.embedding_service.similarity_search(
                query_text=query,
                k=limit,
                institution_filter=category_filter,
                document_ids=document_ids_filter,
                similarity_threshold=similarity_threshold
            )
            
            # Apply date filter if provided
            if date_filter and results:
                filtered_results = []
                for result in results:
                    publish_date = result.get("publish_date")
                    if publish_date:
                        if isinstance(publish_date, str):
                            publish_date = datetime.strptime(publish_date, "%Y-%m-%d").date()
                        
                        # Check date range
                        if "start" in date_filter and publish_date < date_filter["start"]:
                            continue
                        if "end" in date_filter and publish_date > date_filter["end"]:
                            continue
                    
                    filtered_results.append(result)
                
                results = filtered_results[:limit]
            
            # Format results for API response (Elasticsearch format)
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "document_id": str(result["document_id"]),
                    "document_title": result.get("source_document", "Unknown Document"),
                    "content": result["content"],
                    "similarity_score": round(result["similarity"], 4),
                    "chunk_index": result.get("chunk_index", 0),
                    "page_number": result.get("page_number"),
                    "source_institution": result.get("source_institution"),
                    "metadata": result.get("metadata", {})
                })
            
            logger.info(f"Semantic search completed: '{query}' - {len(formatted_results)} results")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Semantic search failed for query '{query}': {str(e)}")
            raise AppException(
                message="Search operation failed",
                detail=str(e),
                error_code="SEMANTIC_SEARCH_FAILED"
            )
    
    async def generate_answer(
        self, 
        question: str, 
        context_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate AI-powered answer using retrieved context
        
        Args:
            question: User's question
            context_chunks: Relevant document chunks from search
            
        Returns:
            Dictionary with answer, sources, and confidence level
            
        Raises:
            AppException: If answer generation fails
        """
        try:
            if not context_chunks:
                return {
                    "question": question,
                    "answer": "Üzgünüm, sorunuzla ilgili belgelerimde yeterli bilgi bulamadım. Lütfen sorunuzu farklı şekilde ifade etmeyi deneyin.",
                    "sources": [],
                    "confidence": "low"
                }
            
            # Prepare context from search results
            context_texts = []
            sources = []
            
            for i, chunk in enumerate(context_chunks):
                context_texts.append(f"[{i+1}] {chunk['content']}")
                
                source_info = {
                    "document_id": chunk["document_id"],
                    "document_title": chunk["document_title"],
                    "similarity_score": chunk["similarity_score"],
                    "metadata": chunk.get("metadata", {})
                }
                sources.append(source_info)
            
            # Create context string
            context = "\n\n".join(context_texts)
            
            # Prepare prompt for OpenAI
            system_prompt = """Sen Türkiye'deki mevzuat ve yasal belgeler konusunda uzman bir asistansın. 
            Verilen belgeler ve bağlam bilgilerini kullanarak kullanıcının sorularını detaylı ve doğru şekilde yanıtlaman gerekiyor.

            Önemli kurallar:
            1. Sadece verilen bağlam bilgilerini kullan, kendi bilgilerini ekleme
            2. Yanıtını Türkçe olarak ver
            3. Eğer bağlam bilgileri soruyu yanıtlamak için yeterli değilse, bunu belirt
            4. Kaynak belgelerden alıntı yaparken [1], [2] gibi referansları kullan
            5. Yanıtını net, anlaşılır ve profesyonel bir dilde ver"""
            
            user_prompt = f"""Bağlam bilgileri:
{context}

Soru: {question}

Lütfen yukarıdaki bağlam bilgilerini kullanarak soruyu yanıtla. Yanıtında hangi belgelerden yararlandığını [1], [2] şeklinde belirt."""
            
            # Generate answer using OpenAI
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,  # gpt-4o
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=settings.OPENAI_MAX_TOKENS,
                    temperature=0.2,  # Lower temperature for more factual responses
                    frequency_penalty=0.1,
                    presence_penalty=0.1
                )
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Determine confidence level based on similarity scores
            avg_similarity = sum(chunk["similarity_score"] for chunk in context_chunks) / len(context_chunks)
            
            if avg_similarity >= 0.8:
                confidence = "high"
            elif avg_similarity >= 0.6:
                confidence = "medium"
            else:
                confidence = "low"
            
            result = {
                "question": question,
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "context_chunks_used": len(context_chunks),
                "average_similarity": round(avg_similarity, 4)
            }
            
            logger.info(f"Answer generated for question: '{question[:50]}...' (confidence: {confidence})")
            
            return result
            
        except Exception as e:
            logger.error(f"Answer generation failed for question '{question}': {str(e)}")
            raise AppException(
                message="Failed to generate answer",
                detail=str(e),
                error_code="ANSWER_GENERATION_FAILED"
            )
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        Get search suggestions based on partial query
        
        Args:
            partial_query: Partial search query
            limit: Maximum number of suggestions
            
        Returns:
            List of search suggestions
        """
        try:
            # This could be enhanced with more sophisticated suggestion logic
            # For now, we'll use simple keyword matching from document titles and content
            
            suggestions = []
            
            # Query database for similar terms in document titles
            query = """
            SELECT DISTINCT title 
            FROM mevzuat_documents 
            WHERE status = 'active' 
                AND processing_status = 'completed'
                AND title ILIKE %s
            ORDER BY title
            LIMIT %s
            """
            
            result = await self.db.execute(query, [f"%{partial_query}%", limit])
            rows = result.fetchall()
            
            for row in rows:
                suggestions.append(row[0])
            
            # If we need more suggestions, look in document categories
            if len(suggestions) < limit:
                remaining = limit - len(suggestions)
                
                category_query = """
                SELECT DISTINCT category 
                FROM mevzuat_documents 
                WHERE status = 'active' 
                    AND processing_status = 'completed'
                    AND category IS NOT NULL
                    AND category ILIKE %s
                ORDER BY category
                LIMIT %s
                """
                
                result = await self.db.execute(category_query, [f"%{partial_query}%", remaining])
                rows = result.fetchall()
                
                for row in rows:
                    if row[0] not in suggestions:
                        suggestions.append(row[0])
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions for '{partial_query}': {str(e)}")
            return []
    
    async def log_search(
        self,
        user_id: Optional[str],
        query: str,
        results_count: int,
        execution_time: float,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Log search query for analytics
        
        Args:
            user_id: User ID who performed the search
            query: Search query
            results_count: Number of results returned
            execution_time: Search execution time in seconds
            ip_address: User's IP address
            user_agent: User's browser user agent
            
        Returns:
            True if logged successfully
        """
        try:
            from models.database import SearchLog
            from uuid import UUID
            
            # Create search log entry
            search_log = SearchLog(
                user_id=UUID(user_id) if user_id else None,
                query=query,
                results_count=results_count,
                execution_time=execution_time,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(search_log)
            await self.db.flush()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log search: {str(e)}")
            return False
    
    async def get_popular_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get popular search queries for analytics
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of popular queries with counts
        """
        try:
            query = """
            SELECT query, COUNT(*) as search_count
            FROM search_logs
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY query
            ORDER BY search_count DESC
            LIMIT %s
            """
            
            result = await self.db.execute(query, [limit])
            rows = result.fetchall()
            
            popular_searches = []
            for row in rows:
                popular_searches.append({
                    "query": row[0],
                    "search_count": row[1]
                })
            
            return popular_searches
            
        except Exception as e:
            logger.error(f"Failed to get popular searches: {str(e)}")
            return []
