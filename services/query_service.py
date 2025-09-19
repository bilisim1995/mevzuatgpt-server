"""
Query service for Ask endpoint orchestration
Handles the complete flow from user query to AI response
"""

import time
import logging
import re
from typing import Dict, List, Any, Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession

from services.embedding_service import EmbeddingService
from services.search_service import SearchService
from services.llm_service import ollama_service
from services.groq_service import GroqService
from services.redis_service import RedisService
from services.reliability_service import ReliabilityService
from services.source_enhancement_service import SourceEnhancementService
from services.search_history_service import SearchHistoryService
from services.credit_service import credit_service
from core.supabase_client import supabase_client
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

# Intent classification types
QueryIntent = Literal["general_conversation", "legal_question", "ambiguous"]

class QueryService:
    """Service for orchestrating the complete ask pipeline"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.search_service = SearchService(db)
        self.reliability_service = ReliabilityService()
        self.source_enhancement_service = SourceEnhancementService()
        self.search_history_service = SearchHistoryService(db)
        self.redis_service = RedisService()  # Add redis_service instance
        
        # Initialize AI provider based on configuration
        from core.config import settings
        if settings.AI_PROVIDER == "groq" and settings.GROQ_API_KEY:
            self.ai_service = GroqService()
            self.ai_provider = "groq"
        else:
            self.ai_service = ollama_service
            self.ai_provider = "ollama"
    
    def classify_query_intent(self, query: str) -> QueryIntent:
        """
        Classify user query intent into three categories
        
        Args:
            query: User's input message
            
        Returns:
            QueryIntent: 'general_conversation', 'legal_question', or 'ambiguous'
        """
        try:
            # Clean and normalize query
            query_clean = query.strip().lower()
            query_words = query_clean.split()
            
            # Skip empty or very short queries
            if not query_clean or len(query_words) < 1:
                return "ambiguous"
            
            # 1. GENERAL CONVERSATION PATTERNS
            # Direct greetings and social expressions
            greeting_patterns = [
                'merhaba', 'selam', 'selam aleykum', 'günaydın', 'iyi akşamlar', 
                'iyi geceler', 'hoşçakal', 'görüşürüz', 'bay bay', 'hadi eyvallah',
                'nasılsın', 'nasılsınız', 'ne haber', 'ne var ne yok', 'naber',
                'teşekkür', 'teşekkürler', 'sağol', 'sağolun', 'rica ederim',
                'özür', 'kusura bakma', 'pardon', 'affedersin'
            ]
            
            # Check for exact greeting matches
            for pattern in greeting_patterns:
                if pattern in query_clean:
                    logger.info(f"Intent: general_conversation (greeting detected: '{pattern}')")
                    return "general_conversation"
            
            # Combined greeting patterns (like "merhaba nasılsın")
            combined_greetings = [
                ('merhaba', 'nasıl'), ('selam', 'nasıl'), ('günaydın', 'nasıl'),
                ('teşekkür', 'ederim'), ('sağ', 'ol')
            ]
            
            for pattern1, pattern2 in combined_greetings:
                if pattern1 in query_clean and pattern2 in query_clean:
                    logger.info(f"Intent: general_conversation (combined greeting: '{pattern1}' + '{pattern2}')")
                    return "general_conversation"
            
            # 2. LEGAL QUESTION PATTERNS
            # Legal keywords and question indicators
            legal_keywords = [
                'hukuk', 'kanun', 'yasa', 'madde', 'fıkra', 'bent', 'mevzuat',
                'sözleşme', 'dava', 'mahkeme', 'hakim', 'avukat', 'savcı',
                'miras', 'veraset', 'boşanma', 'nafaka', 'velayet', 
                'tapu', 'gayrimenkul', 'kira', 'emlak', 'icra', 'haciz',
                'şirket', 'ortaklık', 'vergi', 'gümrük', 'ticaret',
                'sigorta', 'emekli', 'işçi', 'işveren', 'iş hukuku',
                'ceza', 'suç', 'hapis', 'para', 'tazminat', 'zarar',
                'hak', 'yükümlülük', 'sorumluluk', 'borç', 'alacak'
            ]
            
            # Question indicators
            question_indicators = [
                '?', 'nedir', 'nasıl', 'neden', 'niçin', 'ne zaman', 'kim',
                'hangi', 'kaç', 'ne kadar', 'nerede', 'nereden', 'nereye',
                'yapabilir', 'edebilir', 'olur', 'mümkün', 'gerekir', 'lazım'
            ]
            
            # Check for legal keywords
            has_legal_keyword = any(keyword in query_clean for keyword in legal_keywords)
            has_question_indicator = any(indicator in query_clean for indicator in question_indicators)
            
            # Strong legal question indicators
            if has_legal_keyword and (has_question_indicator or len(query_words) > 5):
                logger.info(f"Intent: legal_question (legal keywords + question pattern)")
                return "legal_question"
            
            # Question with sufficient length (likely legal)
            if '?' in query and len(query_words) > 4:
                logger.info(f"Intent: legal_question (question mark + sufficient length: {len(query_words)} words)")
                return "legal_question"
            
            # Long statements that are likely legal (>8 words)
            if len(query_words) > 8 and not any(greeting in query_clean for greeting in greeting_patterns):
                logger.info(f"Intent: legal_question (long statement: {len(query_words)} words)")
                return "legal_question"
            
            # 3. AMBIGUOUS PATTERNS
            # Very short, unclear, or incomplete queries
            ambiguous_patterns = [
                query_clean in ['ne', 'nah', 'evet', 'hayır', 'tamam', 'ok', 'olur', 'iyi', 'kötü'],
                len(query_words) == 1 and query_words[0] not in greeting_patterns,
                len(query_words) == 2 and not any(greeting in query_clean for greeting in greeting_patterns),
                query_clean.endswith('...') or query_clean.endswith('..'),
                'bilmiyorum' in query_clean,
                'emin değilim' in query_clean
            ]
            
            if any(ambiguous_patterns):
                logger.info(f"Intent: ambiguous (unclear or incomplete query)")
                return "ambiguous"
            
            # 4. DEFAULT: Assume legal question
            # If we reach here, it's likely a legal question
            logger.info(f"Intent: legal_question (default classification)")
            return "legal_question"
            
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, defaulting to legal_question")
            return "legal_question"
    
    async def process_ask_query(
        self, 
        query: str,
        user_id: str,
        institution_filter: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5,
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
            
            # Debug log for limit parameter
            logger.info(f"🔢 Processing query with limit={limit}, similarity_threshold={similarity_threshold}")
            
            # 1. Rate limiting check
            is_allowed, remaining = await self.redis_service.check_rate_limit(
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
                cached_results = await self.redis_service.get_cached_search_results(
                    query=query,
                    filters=search_filters or {},
                    limit=limit,
                    similarity_threshold=similarity_threshold
                )
            
            # 3. Generate embedding (with cache)
            embedding_start = time.time()
            query_embedding = None
            
            if use_cache:
                query_embedding = await self.redis_service.get_cached_embedding(query)
            
            if not query_embedding:
                query_embedding = await self.embedding_service.generate_embedding(query)
                if use_cache:
                    await self.redis_service.cache_embedding(query, query_embedding)
            
            embedding_time = int((time.time() - embedding_start) * 1000)
            
            # 4. Perform search (use cache if available)
            search_start = time.time()
            
            if cached_results:
                search_results = cached_results
                logger.info(f"Using cached search results for: {query[:50]}")
                # IMPORTANT: Cached results also need enhancement for PDF URLs
                logger.info(f"🔄 Cached results found, but will still enhance for PDF URLs")
            else:
                # Pre-filter documents by institution for optimization
                document_ids_filter = None
                if institution_filter:
                    logger.info(f"Starting institution pre-filtering for: '{institution_filter}'")
                    await self._update_institutions_cache()
                    try:
                        document_ids_filter = await self._get_documents_by_institution(institution_filter)
                        if document_ids_filter:
                            logger.info(f"OPTIMIZATION: Pre-filtering to {len(document_ids_filter)} documents for institution: '{institution_filter}'")
                        else:
                            logger.warning(f"No documents found for institution: '{institution_filter}' - continuing without filter")
                            document_ids_filter = None
                    except Exception as e:
                        logger.error(f"Pre-filtering failed: {e}")
                        document_ids_filter = None
                
                logger.info(f"🔍 Calling semantic_search with limit={limit}")
                search_results = await self.search_service.semantic_search(
                    query=query,
                    limit=limit,
                    similarity_threshold=similarity_threshold,
                    category_filter=None,
                    date_filter=None,
                    document_ids_filter=document_ids_filter  # Pass pre-filtered document IDs
                )
                
                # Cache search results
                if use_cache and search_results:
                    await self.redis_service.cache_search_results(
                        query=query,
                        results=search_results,
                        filters=search_filters or {},
                        limit=limit,
                        similarity_threshold=similarity_threshold,
                        ttl=1800  # 30 minutes
                    )
            
            search_time = int((time.time() - search_start) * 1000)
            
            # 4.5. Enhance search results with source information  
            logger.info(f"Total search results before enhancement: {len(search_results) if search_results else 0}")
            
            if search_results:
                try:
                    logger.info(f"🔧 About to enhance {len(search_results)} search results")
                    search_results = self.source_enhancement_service.enhance_search_results(search_results)
                    logger.info(f"✅ Enhanced {len(search_results)} search results with source information")
                except Exception as e:
                    logger.error(f"Enhancement service failed: {e}")
                    import traceback
                    logger.error(f"Enhancement traceback: {traceback.format_exc()}")
                    # Continue with unenhanced results
            
            # 5. Generate AI response using configured provider
            ai_start = time.time()
            
            if self.ai_provider == "groq":
                # Use Groq service for fast inference
                context_text = self._prepare_context_for_groq(search_results)
                
                ai_result = await self.ai_service.generate_response(
                    query=query,
                    context=context_text
                )
                
                llm_response = {
                    "answer": ai_result["response"],
                    "confidence_score": ai_result["confidence_score"],
                    "sources": self.source_enhancement_service.format_sources_for_response(search_results),  # Use enhanced source formatting
                    "ai_model": ai_result["model_used"],
                    "processing_time": ai_result["processing_time"],
                    "token_usage": ai_result.get("token_usage", {})
                }
            else:
                # Use Ollama service (fallback)
                llm_response = await ollama_service.generate_response(
                    query=query,
                    context=search_results,
                    institution_filter=institution_filter
                )
            
            ai_time = int((time.time() - ai_start) * 1000)
            
            # 6. Calculate comprehensive confidence score with detailed breakdown
            reliability_start = time.time()
            try:
                reliability_data = await self.reliability_service.calculate_comprehensive_confidence(
                    search_results, llm_response.get("answer", "")
                )
                enhanced_confidence = reliability_data.get("confidence_score", 0.5)
                confidence_breakdown = reliability_data.get("confidence_breakdown")
                logger.info(f"Reliability data calculated successfully: {enhanced_confidence}")
            except Exception as e:
                logger.error(f"Reliability calculation failed: {e}")
                enhanced_confidence = self._calculate_simple_confidence(search_results, llm_response.get("answer", ""))
                confidence_breakdown = None
            reliability_time = int((time.time() - reliability_start) * 1000)
            
            # 7. Apply confidence-based credit and source filtering
            confidence_threshold = 0.4  # 40% eşiği
            is_low_confidence = enhanced_confidence < confidence_threshold
            
            if is_low_confidence:
                # Düşük güvenilirlik: kredi kesme, kaynakları filtreleme
                actual_credits = 0  # Kredi kesilmez
                filtered_sources = []  # Kaynaklar gösterilmez
                logger.info(f"Low confidence detected ({enhanced_confidence:.2f} < {confidence_threshold}) - No credits charged, sources filtered")
            else:
                # Normal güvenilirlik: normal işlem
                actual_credits = credit_service.calculate_credit_cost(query) if not await credit_service.is_admin_user(user_id) else 0
                filtered_sources = self.source_enhancement_service.format_sources_for_response(search_results)
                logger.info(f"Normal confidence ({enhanced_confidence:.2f} >= {confidence_threshold}) - Credits charged normally")
            
            # 8. Update user history and analytics
            if use_cache:
                await self.redis_service.add_user_search(
                    user_id=user_id,
                    query=query,
                    institution=institution_filter or ""
                )
                await self.redis_service.increment_search_popularity(query)
            
            # 9. Log search with enhanced data
            
            search_log_id = await self._log_search_query(
                user_id=user_id,
                query=query,
                response=llm_response.get("answer", llm_response.get("response", "")),
                sources=filtered_sources,  # Log filtered sources based on confidence
                reliability_score=float(enhanced_confidence) if enhanced_confidence is not None else 0.0,
                credits_used=actual_credits,
                institution_filter=institution_filter,
                results_count=len(search_results),
                response_generated=True
            )
            
            pipeline_time = int((time.time() - pipeline_start) * 1000)
            
            # 10. Build response with enhanced confidence and conditional warning
            original_answer = llm_response.get("answer", llm_response.get("response", ""))
            
            if is_low_confidence:
                # Add warning message for low confidence responses
                confidence_percentage = int(enhanced_confidence * 100)
                warning_message = f"""⚠️ **Güvenilirlik Uyarısı**

Sorgunuz için sistemimizde yeterli güvenilir bilgi bulunamadı (Güvenilirlik: %{confidence_percentage}). 

Bu yanıt için **kredi kesilmedi** ve **kaynaklar gösterilmedi**. Daha spesifik bir soru sormayı deneyebilir veya konu ile ilgili güncel belgelerin sisteme yüklenmesini talep edebilirsiniz.

---
{original_answer}"""
                final_answer = warning_message
            else:
                final_answer = original_answer
            
            response = {
                "query": query,
                "answer": final_answer,
                "confidence_score": enhanced_confidence,
                "search_log_id": search_log_id,  # Add search log ID for feedback
                "confidence_breakdown": confidence_breakdown,  # Add detailed breakdown
                "sources": filtered_sources,  # Use filtered sources based on confidence
                "institution_filter": institution_filter,
                "search_stats": {
                    "total_chunks_found": len(search_results),
                    "embedding_time_ms": embedding_time,
                    "search_time_ms": search_time,
                    "generation_time_ms": llm_response.get("generation_time_ms", ai_time),
                    "reliability_time_ms": reliability_time,
                    "total_pipeline_time_ms": pipeline_time,
                    "cache_used": cached_results is not None,
                    "rate_limit_remaining": remaining,
                    "low_confidence": is_low_confidence,  # Track low confidence responses
                    "confidence_threshold": confidence_threshold,
                    "credits_waived": is_low_confidence  # Track if credits were waived
                },
                "llm_stats": {
                    "model_used": llm_response.get("model_used", "llama3-8b-8192"),
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
            recent_searches = await self.redis_service.get_user_search_history(
                user_id=user_id,
                limit=5
            )
            
            # Get popular searches
            popular_searches = await self.redis_service.get_popular_searches(limit=10)
            
            # Get available institutions
            institutions = await self.redis_service.get_available_institutions()
            if not institutions:
                await self._update_institutions_cache()
                institutions = await self.redis_service.get_available_institutions()
            
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
    
    def _format_sources_safe(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format search results for response with error handling"""
        try:
            logger.info(f"Starting _format_sources_safe with {len(search_results) if search_results else 0} results")
            formatted_sources = []
            
            for i, result in enumerate(search_results):
                try:
                    formatted_source = {
                        "document_id": result.get("document_id"),
                        "document_title": result.get("document_title"),
                        "source_institution": result.get("source_institution"),
                        "content": result.get("content", "")[:500] + "..." if len(result.get("content", "")) > 500 else result.get("content", ""),
                        "similarity_score": result.get("similarity_score"),
                        "category": result.get("category"),
                        "publish_date": result.get("publish_date"),
                        "pdf_url": result.get("pdf_url"),
                        "citation": result.get("citation"),
                        "page_number": result.get("page_number"),
                        "line_start": result.get("line_start"),
                        "line_end": result.get("line_end"),
                        "content_preview": result.get("content_preview"),
                        "chunk_index": result.get("chunk_index")
                    }
                    formatted_sources.append(formatted_source)
                    
                except Exception as format_error:
                    logger.error(f"Failed to format source {i+1}: {format_error}")
                    # Add minimal source on error
                    formatted_sources.append({
                        "document_title": result.get("document_title", "Unknown"),
                        "content": result.get("content", "")[:100],
                        "similarity_score": result.get("similarity_score", 0)
                    })
            
            logger.info(f"_format_sources_safe completed: {len(formatted_sources)} sources formatted")
            return formatted_sources
            
        except Exception as e:
            logger.error(f"Critical error in _format_sources_safe: {e}")
            # Return unformatted results as fallback
            return search_results if search_results else []

    def _format_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format search results for response (original method kept for compatibility)"""
        return self._format_sources_safe(search_results)
    
    def _prepare_context_for_groq(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare context text for Groq API from search results
        
        Args:
            search_results: List of search result dictionaries
            
        Returns:
            Formatted context string
        """
        if not search_results:
            return "Sorgu ile alakalı belge bulunamadı."
        
        context_parts = []
        
        for i, result in enumerate(search_results[:10], 1):  # Limit to top 10 results
            title = result.get("document_title", "Bilinmeyen Belge")
            content = result.get("content", "")
            similarity = result.get("similarity_score", 0.0)
            institution = result.get("source_institution", "")
            
            # Format each source with metadata
            source_text = f"""[KAYNAK {i}]
Belge: {title}
Kurum: {institution}
Benzerlik: {similarity:.2f}
İçerik: {content}

"""
            context_parts.append(source_text)
        
        return "\n".join(context_parts)
    
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
    
    def _build_empty_response(self, query: str, institution_filter: str = None) -> Dict[str, Any]:
        """Build empty response when no documents match institution filter"""
        return {
            "success": True,
            "data": {
                "query": query,
                "institution_filter": institution_filter,
                "answer": "Belirtilen kurum için ilgili belgeler bulunamadı.",
                "sources": [],
                "total_results": 0,
                "reliability_score": 0.0,
                "search_metadata": {
                    "total_documents_searched": 0,
                    "embedding_time": 0,
                    "search_time": 0,
                    "ai_time": 0,
                    "total_time": 0
                }
            }
        }
    
    async def _update_institutions_cache(self):
        """Update available institutions cache - Using metadata field for institution data"""
        try:
            # Get distinct institutions from metadata field
            response = supabase_client.supabase.table('mevzuat_documents').select('metadata').execute()
            
            institutions = set()
            if response.data:
                for doc in response.data:
                    metadata = doc.get('metadata', {})
                    if isinstance(metadata, dict) and metadata.get('source_institution'):
                        institutions.add(metadata['source_institution'])
                
                institutions_list = sorted(list(institutions))
                
                # Add default institutions if none found
                if not institutions_list:
                    institutions_list = [
                        "Sosyal Güvenlik Kurumu",
                        "Çalışma ve Sosyal Güvenlik Bakanlığı", 
                        "Hazine ve Maliye Bakanlığı",
                        "Adalet Bakanlığı",
                        "İçişleri Bakanlığı"
                    ]
                
                await self.redis_service.cache_institutions(institutions_list)
                
            logger.info(f"Updated institutions cache with {len(institutions_list)} institutions")
            
        except Exception as e:
            logger.warning(f"Failed to update institutions cache: {e}")
    
    def _calculate_simple_confidence(self, search_results: List[Dict[str, Any]], ai_answer: str) -> float:
        """
        Calculate simple confidence score based on search quality and AI response
        
        Args:
            search_results: List of search results
            ai_answer: Generated AI response
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            if not search_results or not ai_answer:
                return 0.3  # Low confidence for no results or no answer
            
            # Base score from search results
            avg_similarity = sum(r.get('similarity_score', 0) for r in search_results) / len(search_results)
            result_count_factor = min(len(search_results) / 5.0, 1.0)  # More results = higher confidence
            
            # AI answer quality factors
            answer_length_factor = min(len(ai_answer) / 200.0, 1.0)  # Longer answers generally better
            
            # Check for uncertainty phrases
            uncertainty_phrases = [
                "belirsiz", "kesin değil", "tam olarak bilinmiyor", 
                "açık değil", "net değil", "bilgi bulunmamaktadır"
            ]
            uncertainty_penalty = 0.2 if any(phrase in ai_answer.lower() for phrase in uncertainty_phrases) else 0.0
            
            # Calculate final confidence
            confidence = (
                avg_similarity * 0.4 +           # 40% from search similarity
                result_count_factor * 0.3 +      # 30% from result count
                answer_length_factor * 0.3       # 30% from answer quality
            ) - uncertainty_penalty
            
            # Ensure range 0.3-0.95 (avoid extremes)
            final_confidence = max(0.3, min(0.95, confidence))
            
            logger.debug(f"Confidence calculation: similarity={avg_similarity:.3f}, "
                        f"count_factor={result_count_factor:.3f}, "
                        f"answer_factor={answer_length_factor:.3f}, "
                        f"penalty={uncertainty_penalty:.3f}, "
                        f"final={final_confidence:.3f}")
            
            return final_confidence
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return 0.5  # Neutral fallback
    
    def _matches_institution_filter(self, search_result: Dict[str, Any], institution_filter: str) -> bool:
        """Check if search result matches the institution filter using metadata"""
        try:
            # Check metadata for institution information
            metadata = search_result.get("metadata", {})
            if isinstance(metadata, dict):
                source_institution = metadata.get("source_institution", "")
                if source_institution and institution_filter.lower() in source_institution.lower():
                    return True
            
            # Fallback: check document title for institution keywords
            title = search_result.get("document_title", "")
            filter_lower = institution_filter.lower()
            
            # Map common filter terms to title keywords
            institution_keywords = {
                "sosyal güvenlik": ["sgk", "sigorta", "sosyal", "güvenlik"],
                "çalışma": ["çalışma", "iş", "işçi"],
                "hazine": ["hazine", "maliye", "vergi"],
                "adalet": ["adalet", "mahkeme", "ceza"],
                "içişleri": ["içişleri", "polis", "güvenlik"]
            }
            
            for institution, keywords in institution_keywords.items():
                if institution in filter_lower:
                    if any(keyword in title.lower() for keyword in keywords):
                        return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error matching institution filter: {e}")
            return False
    
    async def _log_search_query(
        self,
        user_id: str,
        query: str,
        response: str = None,
        sources: List[Dict] = None,
        reliability_score: float = None,
        credits_used: int = 0,
        institution_filter: Optional[str] = None,
        results_count: int = 0,
        response_generated: bool = True
    ) -> Optional[str]:
        """Log search query with full details and return the search log ID"""
        try:
            # Use service client to bypass RLS issues
            log_data = {
                "user_id": user_id,
                "query": query,
                "response": response,
                "sources": sources,
                "reliability_score": reliability_score,
                "credits_used": credits_used,
                "institution_filter": institution_filter,
                "results_count": results_count,
                "execution_time": 0.5,  # Add execution time placeholder
                "ip_address": "127.0.0.1"
            }
            
            result = supabase_client.service_client.table('search_logs').insert(log_data).execute()
            
            if result.data and len(result.data) > 0:
                search_log_id = result.data[0]['id']  # Return the UUID ID
                logger.info(f"Search query logged with full details - ID: {search_log_id}")
                return search_log_id
            return None
            
        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")
            return None
    
    async def _get_documents_by_institution(self, institution_filter: str) -> List[str]:
        """Get document IDs that belong to the specified institution"""
        try:
            # Query documents with metadata containing the institution (use service client to bypass RLS)
            service_client = supabase_client.get_client(use_service_key=True)
            response = service_client.table('mevzuat_documents') \
                .select('id') \
                .filter('metadata->source_institution', 'ilike', f'%{institution_filter}%') \
                .execute()
            
            if response.data:
                document_ids = [doc['id'] for doc in response.data]
                logger.info(f"Found {len(document_ids)} documents for institution '{institution_filter}'")
                return document_ids
            else:
                logger.warning(f"No documents found for institution: '{institution_filter}'")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get documents by institution: {e}")
            return []