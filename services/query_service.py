"""
Query service for Ask endpoint orchestration
Handles the complete flow from user query to AI response
"""

import time
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from services.embedding_service import EmbeddingService
from services.search_service import SearchService
from services.llm_service import ollama_service
from services.redis_service import redis_service
from models.supabase_client import supabase_client
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class QueryService:
    """Service for orchestrating the complete ask pipeline"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.search_service = SearchService(db)
    
    async def process_ask_query(
        self, 
        query: str,
        user_id: str,
        institution_filter: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Process complete ask query pipeline
        
        Args:
            query: User's question
            user_id: Current user ID
            institution_filter: Optional institution filter
            limit: Max search results
            similarity_threshold: Min similarity for search
            use_cache: Whether to use Redis cache
            
        Returns:
            Complete response with answer, sources, and metadata
        """
        try:
            pipeline_start = time.time()
            
            # 1. Rate limiting check
            is_allowed, remaining = await redis_service.check_rate_limit(
                user_id=user_id,
                endpoint="ask",
                limit=30,  # 30 requests per minute
                window=60
            )
            
            if not is_allowed:
                raise AppException(
                    message="Rate limit exceeded",
                    detail="You have exceeded the maximum number of requests per minute",
                    status_code=429,
                    error_code="RATE_LIMIT_EXCEEDED"
                )
            
            # 2. Check cache for similar query
            search_filters = {"institution": institution_filter} if institution_filter else None
            cached_results = None
            
            if use_cache:
                cached_results = await redis_service.get_cached_search_results(
                    query=query,
                    filters=search_filters
                )
            
            # 3. Generate embedding (with cache)
            embedding_start = time.time()
            query_embedding = None
            
            if use_cache:
                query_embedding = await redis_service.get_cached_embedding(query)
            
            if not query_embedding:
                query_embedding = await self.embedding_service.generate_embedding(query)
                if use_cache:
                    await redis_service.cache_embedding(query, query_embedding)
            
            embedding_time = int((time.time() - embedding_start) * 1000)
            
            # 4. Perform search (use cache if available)
            search_start = time.time()
            
            if cached_results:
                search_results = cached_results
                logger.info(f"Using cached search results for: {query[:50]}")
            else:
                # Get institutions if filter requested
                if institution_filter:
                    # Update available institutions cache
                    await self._update_institutions_cache()
                
                search_results = await self.search_service.semantic_search(
                    query=query,
                    limit=limit,
                    similarity_threshold=similarity_threshold,
                    category_filter=None,
                    date_filter=None
                )
                
                # Filter by institution if specified
                if institution_filter and search_results:
                    search_results = [
                        result for result in search_results 
                        if institution_filter.lower() in result.get("source_institution", "").lower()
                    ]
                
                # Cache search results
                if use_cache and search_results:
                    await redis_service.cache_search_results(
                        query=query,
                        results=search_results,
                        filters=search_filters,
                        ttl=1800  # 30 minutes
                    )
            
            search_time = int((time.time() - search_start) * 1000)
            
            # 5. Generate AI response
            llm_response = await ollama_service.generate_response(
                query=query,
                context=search_results,
                institution_filter=institution_filter
            )
            
            # 6. Update user history and analytics
            if use_cache:
                await redis_service.add_user_search(
                    user_id=user_id,
                    query=query,
                    institution=institution_filter
                )
                await redis_service.increment_search_popularity(query)
            
            # 7. Log search for analytics
            await self._log_search_query(
                user_id=user_id,
                query=query,
                institution_filter=institution_filter,
                results_count=len(search_results),
                response_generated=True
            )
            
            pipeline_time = int((time.time() - pipeline_start) * 1000)
            
            # 8. Build response
            response = {
                "query": query,
                "answer": llm_response["answer"],
                "confidence_score": llm_response["confidence_score"],
                "sources": self._format_sources(search_results),
                "institution_filter": institution_filter,
                "search_stats": {
                    "total_chunks_found": len(search_results),
                    "embedding_time_ms": embedding_time,
                    "search_time_ms": search_time,
                    "generation_time_ms": llm_response["generation_time_ms"],
                    "total_pipeline_time_ms": pipeline_time,
                    "cache_used": cached_results is not None,
                    "rate_limit_remaining": remaining
                },
                "llm_stats": {
                    "model_used": llm_response["model_used"],
                    "prompt_tokens": llm_response.get("prompt_tokens", 0),
                    "response_tokens": llm_response.get("response_tokens", 0)
                }
            }
            
            logger.info(f"Ask query processed: '{query[:50]}' - {len(search_results)} sources, {pipeline_time}ms")
            
            return response
            
        except AppException:
            raise
        except Exception as e:
            logger.error(f"Failed to process ask query: {e}")
            raise AppException(
                message="Failed to process query",
                detail=str(e),
                error_code="QUERY_PROCESSING_FAILED"
            )
    
    async def get_user_suggestions(self, user_id: str) -> Dict[str, Any]:
        """Get personalized suggestions for user"""
        try:
            # Get user's recent searches
            recent_searches = await redis_service.get_user_search_history(
                user_id=user_id,
                limit=5
            )
            
            # Get popular searches
            popular_searches = await redis_service.get_popular_searches(limit=10)
            
            # Get available institutions
            institutions = await redis_service.get_available_institutions()
            if not institutions:
                await self._update_institutions_cache()
                institutions = await redis_service.get_available_institutions()
            
            return {
                "recent_searches": recent_searches,
                "popular_searches": popular_searches,
                "available_institutions": institutions,
                "suggestions": self._generate_query_suggestions(recent_searches, popular_searches)
            }
            
        except Exception as e:
            logger.warning(f"Failed to get user suggestions: {e}")
            return {
                "recent_searches": [],
                "popular_searches": [],
                "available_institutions": [],
                "suggestions": []
            }
    
    def _format_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format search results for response"""
        formatted_sources = []
        
        for result in search_results:
            formatted_sources.append({
                "document_id": result.get("document_id"),
                "document_title": result.get("document_title"),
                "source_institution": result.get("source_institution"),
                "content": result.get("content", "")[:500] + "..." if len(result.get("content", "")) > 500 else result.get("content", ""),
                "similarity_score": result.get("similarity_score"),
                "category": result.get("category"),
                "publish_date": result.get("publish_date")
            })
        
        return formatted_sources
    
    def _generate_query_suggestions(
        self, 
        recent_searches: List[Dict], 
        popular_searches: List[Dict]
    ) -> List[str]:
        """Generate query suggestions based on history and popularity"""
        suggestions = []
        
        # Add variations of recent searches
        for search in recent_searches[:3]:
            query = search.get("query", "")
            if len(query) > 10:  # Only suggest meaningful queries
                suggestions.append(f"{query} hakkında detaylı bilgi")
        
        # Add popular searches
        for search in popular_searches[:5]:
            if search["query"] not in [s.lower() for s in suggestions]:
                suggestions.append(search["query"])
        
        # Add common legal query templates
        common_templates = [
            "Bu konuda hangi yasal düzenlemeler var?",
            "İlgili ceza hükümleri nelerdir?",
            "Başvuru süreçleri nasıl işliyor?",
            "Hangi belgeler gerekli?",
            "Yasal süreler nelerdir?"
        ]
        
        suggestions.extend(common_templates[:2])
        
        return suggestions[:10]  # Return max 10 suggestions
    
    async def _update_institutions_cache(self):
        """Update available institutions cache"""
        try:
            # Get distinct institutions from database
            response = supabase_client.supabase.table('mevzuat_documents').select('source_institution').execute()
            
            if response.data:
                institutions = list(set([
                    doc['source_institution'] 
                    for doc in response.data 
                    if doc.get('source_institution')
                ]))
                institutions.sort()
                
                await redis_service.cache_institutions(institutions)
                logger.info(f"Updated institutions cache: {len(institutions)} institutions")
            
        except Exception as e:
            logger.warning(f"Failed to update institutions cache: {e}")
    
    async def _log_search_query(
        self,
        user_id: str,
        query: str,
        institution_filter: Optional[str],
        results_count: int,
        response_generated: bool
    ):
        """Log search query for analytics"""
        try:
            log_data = {
                "user_id": user_id,
                "query": query,
                "institution_filter": institution_filter,
                "results_count": results_count,
                "response_generated": response_generated,
                "query_type": "ask",
                "created_at": "now()"
            }
            
            supabase_client.supabase.table('search_logs').insert(log_data).execute()
            
        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")