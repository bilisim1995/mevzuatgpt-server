"""
Query service for Ask endpoint orchestration
Handles the complete flow from user query to AI response
"""

import time
import logging
import re
from typing import Dict, List, Any, Optional, Literal
from sqlalchemy.ext.asyncio import AsyncSession
import openai
from openai import AsyncOpenAI

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
from core.config import settings

logger = logging.getLogger(__name__)

# Intent classification types
QueryIntent = Literal["general_conversation", "legal_question", "ambiguous"]

def fix_markdown_formatting(text: str) -> str:
    """
    Post-process AI response to ensure proper markdown formatting.
    Adds blank lines before headings if missing.
    
    Args:
        text: AI-generated markdown text
        
    Returns:
        Properly formatted markdown text
    """
    if not text:
        return text
    
    lines = text.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Check if current line is a heading (starts with ##)
        is_heading = line.strip().startswith('##')
        
        if is_heading and i > 0:
            # Get previous line
            prev_line = lines[i-1].strip()
            
            # If previous line is not empty, add blank line before heading
            if prev_line and not prev_line.startswith('##'):
                # Check if the line before this in fixed_lines is already empty
                if fixed_lines and fixed_lines[-1].strip():
                    fixed_lines.append('')  # Add blank line
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

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
        if settings.AI_PROVIDER == "groq" and settings.GROQ_API_KEY:
            self.ai_service = GroqService()
            self.ai_provider = "groq"
        else:
            self.ai_service = ollama_service
            self.ai_provider = "ollama"
        
        # Initialize OpenAI client for fallback
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
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
    
    def calculate_intent_based_credits(self, query: str) -> int:
        """
        Calculate required credits based on query intent
        
        Args:
            query: User's query
            
        Returns:
            Required credits based on intent type
        """
        try:
            query_intent = self.classify_query_intent(query)
            
            if query_intent == "general_conversation":
                # Fixed 1 credit for general conversation
                logger.info(f"Intent-based credits: 1 credit for general_conversation")
                return 1
            
            elif query_intent == "ambiguous":
                # Fixed 1 credit for clarification questions
                logger.info(f"Intent-based credits: 1 credit for ambiguous query")
                return 1
            
            else:  # legal_question
                # Use normal credit calculation for legal questions
                from services.credit_service import credit_service
                normal_credits = credit_service.calculate_credit_cost(query)
                logger.info(f"Intent-based credits: {normal_credits} credits for legal_question")
                return normal_credits
                
        except Exception as e:
            logger.warning(f"Intent-based credit calculation failed: {e}, using fallback")
            # Fallback to normal calculation
            from services.credit_service import credit_service
            return credit_service.calculate_credit_cost(query)
    
    async def handle_general_conversation(self, query: str, user_id: str) -> Dict[str, Any]:
        """
        Handle general conversation queries with simple responses
        
        Args:
            query: User's conversational message
            user_id: Current user ID
            
        Returns:
            Simple conversational response with 1 credit cost
        """
        try:
            start_time = time.time()
            
            # Classify the specific type of conversation
            query_clean = query.strip().lower()
            
            # Define response templates
            responses = {
                'greeting': {
                    'message': "Merhaba! Size hukuki belgelerimiz doğrultusunda nasıl yardımcı olabilirim? 😊",
                    'keywords': ['merhaba', 'selam', 'günaydın', 'iyi akşamlar']
                },
                'how_are_you': {
                    'message': "Teşekkür ederim, size yardımcı olmaya hazırım. Hangi konuyu incelememizi istersiniz?",
                    'keywords': ['nasılsın', 'nasılsınız', 'ne haber', 'ne var ne yok', 'naber']
                },
                'thanks': {
                    'message': "Rica ederim! Başka bir sorunuz olursa çekinmeden sorun.",
                    'keywords': ['teşekkür', 'teşekkürler', 'sağol', 'sağolun']
                },
                'goodbye': {
                    'message': "Hoşçakalın! Her zaman yardıma hazırım.",
                    'keywords': ['hoşçakal', 'görüşürüz', 'bay bay', 'iyi geceler']
                },
                'combined_greeting': {
                    'message': "Merhaba, teşekkür ederim! Size belgelerimizdeki bilgilerle destek olmak için buradayım. Konunuz nedir? 😊",
                    'keywords': ['merhaba nasıl', 'selam nasıl', 'günaydın nasıl']
                },
                'default': {
                    'message': "Size nasıl yardımcı olabilirim? Hukuki sorularınız için buradayım.",
                    'keywords': []
                }
            }
            
            # Find the appropriate response
            selected_response = responses['default']['message']
            response_type = 'default'
            
            for response_key, response_data in responses.items():
                if response_key == 'default':
                    continue
                    
                # Check for keyword matches
                for keyword in response_data['keywords']:
                    if keyword in query_clean:
                        selected_response = response_data['message']
                        response_type = response_key
                        break
                        
                if response_type != 'default':
                    break
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            
            # Format response
            response = {
                "query": query,  # Include original query like legal document responses
                "answer": selected_response,
                "intent": "general_conversation",
                "response_type": response_type,
                "confidence_score": 1.0,  # High confidence for pre-defined responses
                "sources": [],  # No document sources for general conversation
                "institution_filter": None,
                "search_stats": {
                    "total_chunks_found": 0,
                    "embedding_time_ms": 0,
                    "search_time_ms": 0,
                    "generation_time_ms": processing_time,
                    "reliability_time_ms": 0,
                    "total_pipeline_time_ms": processing_time,
                    "cache_used": False,
                    "rate_limit_remaining": 30,
                    "low_confidence": False,
                    "confidence_threshold": 0.0,
                    "credits_used": 1  # Fixed 1 credit for general conversation
                },
                "llm_stats": {
                    "model_used": "conversation_templates",
                    "prompt_tokens": len(query.split()),
                    "response_tokens": len(selected_response.split())
                }
            }
            
            logger.info(f"General conversation handled: '{query[:50]}' -> {response_type} ({processing_time}ms)")
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle general conversation: {e}")
            # Fallback to default response
            return {
                "query": query,  # Include original query in error fallback too
                "answer": "Size nasıl yardımcı olabilirim? Hukuki sorularınız için buradayım.",
                "intent": "general_conversation",
                "response_type": "error_fallback",
                "confidence_score": 1.0,
                "sources": [],
                "institution_filter": None,
                "search_stats": {
                    "total_chunks_found": 0,
                    "embedding_time_ms": 0,
                    "search_time_ms": 0,
                    "generation_time_ms": 0,
                    "reliability_time_ms": 0,
                    "total_pipeline_time_ms": 0,
                    "cache_used": False,
                    "rate_limit_remaining": 30,
                    "low_confidence": False,
                    "confidence_threshold": 0.0,
                    "credits_used": 1
                },
                "llm_stats": {
                    "model_used": "conversation_templates",
                    "prompt_tokens": 0,
                    "response_tokens": 0
                }
            }
    
    async def handle_ambiguous_query(self, query: str, user_id: str) -> Dict[str, Any]:
        """
        Handle ambiguous queries with clarifying questions
        
        Args:
            query: User's unclear message
            user_id: Current user ID
            
        Returns:
            Clarifying question response with 1 credit cost
        """
        try:
            start_time = time.time()
            
            # Analyze the type of ambiguity
            query_clean = query.strip().lower()
            query_words = query_clean.split()
            
            # Define clarifying response templates
            clarifying_responses = {
                'too_short': {
                    'message': "Sorunuzu biraz daha detaylandırabilir misiniz? Hangi konuda bilgi almak istiyorsunuz?",
                    'condition': len(query_words) <= 2
                },
                'single_word': {
                    'message': f"'{query}' hakkında daha spesifik bir soru sorabilir misiniz? Örneğin: '{query} nedir?', '{query} nasıl yapılır?' gibi.",
                    'condition': len(query_words) == 1 and query_words[0] not in ['ne', 'nah', 'evet', 'hayır']
                },
                'incomplete': {
                    'message': "Sorunuz tamamlanmamış gibi görünüyor. Tam olarak ne öğrenmek istiyorsunuz?",
                    'condition': query_clean.endswith('...') or query_clean.endswith('..')
                },
                'uncertain': {
                    'message': "Hangi konuda yardıma ihtiyacınız var? Size daha iyi yardımcı olabilmem için sorunuzu netleştirebilir misiniz?",
                    'condition': any(phrase in query_clean for phrase in ['bilmiyorum', 'emin değilim', 'ne yapacağım'])
                },
                'yes_no_only': {
                    'message': "Bu yanıt bir önceki soruyla mı ilgili? Lütfen tam sorunuzu tekrar belirtin ki size doğru şekilde yardımcı olabileyim.",
                    'condition': query_clean in ['evet', 'hayır', 'tamam', 'ok', 'olur', 'iyi', 'kötü']
                },
                'general_unclear': {
                    'message': "Size nasıl yardımcı olabileceğimi daha iyi anlayabilmem için sorunuzu biraz daha açıklayabilir misiniz? Hangi hukuki konu hakkında bilgi almak istiyorsunuz?",
                    'condition': True  # Default fallback
                }
            }
            
            # Find the appropriate clarifying response
            selected_response = clarifying_responses['general_unclear']['message']
            response_type = 'general_unclear'
            
            for response_key, response_data in clarifying_responses.items():
                if response_key == 'general_unclear':
                    continue
                    
                if response_data['condition']:
                    selected_response = response_data['message']
                    response_type = response_key
                    break
            
            # Add helpful suggestions based on query context
            suggestions = []
            if len(query_words) == 1:
                keyword = query_words[0]
                if keyword in ['miras', 'boşanma', 'kira', 'şirket', 'sigorta']:
                    suggestions.append(f"'{keyword} hukuku nedir?'")
                    suggestions.append(f"'{keyword} ile ilgili haklarım neler?'")
                    suggestions.append(f"'{keyword} süreci nasıl işler?'")
            
            if suggestions:
                suggestion_text = "\n\nÖrnek sorular:\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
                selected_response += suggestion_text
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            
            # Format response
            response = {
                "query": query,  # Include original query for consistency
                "answer": selected_response,
                "intent": "ambiguous",
                "response_type": response_type,
                "confidence_score": 1.0,  # High confidence for clarification responses
                "sources": [],  # No document sources for clarification
                "institution_filter": None,
                "search_stats": {
                    "total_chunks_found": 0,
                    "embedding_time_ms": 0,
                    "search_time_ms": 0,
                    "generation_time_ms": processing_time,
                    "reliability_time_ms": 0,
                    "total_pipeline_time_ms": processing_time,
                    "cache_used": False,
                    "rate_limit_remaining": 30,
                    "low_confidence": False,
                    "confidence_threshold": 0.0,
                    "credits_used": 1,  # Fixed 1 credit for clarification
                    "clarification_needed": True
                },
                "llm_stats": {
                    "model_used": "clarification_templates",
                    "prompt_tokens": len(query.split()),
                    "response_tokens": len(selected_response.split())
                },
                "suggestions": suggestions  # Include suggestions for frontend
            }
            
            logger.info(f"Ambiguous query handled: '{query[:50]}' -> {response_type} ({processing_time}ms)")
            return response
            
        except Exception as e:
            logger.error(f"Failed to handle ambiguous query: {e}")
            # Fallback to default clarification
            return {
                "query": query,  # Include original query in error fallback
                "answer": "Sorunuzu biraz daha detaylandırabilir misiniz? Size daha iyi yardımcı olabilmem için hangi konuda bilgi almak istediğinizi belirtebilirsiniz.",
                "intent": "ambiguous",
                "response_type": "error_fallback",
                "confidence_score": 1.0,
                "sources": [],
                "institution_filter": None,
                "search_stats": {
                    "total_chunks_found": 0,
                    "embedding_time_ms": 0,
                    "search_time_ms": 0,
                    "generation_time_ms": 0,
                    "reliability_time_ms": 0,
                    "total_pipeline_time_ms": 0,
                    "cache_used": False,
                    "rate_limit_remaining": 30,
                    "low_confidence": False,
                    "confidence_threshold": 0.0,
                    "credits_used": 1,
                    "clarification_needed": True
                },
                "llm_stats": {
                    "model_used": "clarification_templates",
                    "prompt_tokens": 0,
                    "response_tokens": 0
                },
                "suggestions": []
            }
    
    async def process_ask_query(
        self, 
        query: str,
        user_id: str,
        institution_filter: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.5,
        use_cache: bool = True,
        intent: Optional[QueryIntent] = None,
        response_style: Optional[str] = None,
        conversation_id: Optional[str] = None
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
            
            # 🎯 STEP 0: Intent Classification (NEW - Most Important Step)
            query_intent = intent or self.classify_query_intent(query)
            if intent:
                logger.info(f"🎯 Using pre-calculated intent: {query_intent} for query: '{query[:50]}'")
            else:
                logger.info(f"🎯 Query intent classified as: {query_intent} for query: '{query[:50]}'")
            
            # Route to appropriate handler based on intent
            if query_intent == "general_conversation":
                logger.info("🗣️ Routing to general conversation handler")
                return await self.handle_general_conversation(query, user_id)
            
            elif query_intent == "ambiguous":
                logger.info("❓ Routing to ambiguous query handler")
                return await self.handle_ambiguous_query(query, user_id)
            
            # If we reach here, it's a legal_question - continue with full RAG pipeline
            logger.info("⚖️ Routing to legal question handler (full RAG pipeline)")
            
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
                # Use Groq service for fast inference with OpenAI fallback
                context_text = self._prepare_context_for_groq(search_results)
                conversation_context = ""
                if conversation_id:
                    conversation_context = await self._get_recent_conversation_context(
                        conversation_id=conversation_id,
                        user_id=user_id,
                        limit=10
                    )
                
                try:
                    ai_result = await self.ai_service.generate_response(
                        query=query,
                        context=context_text,
                        response_style=response_style,
                        conversation_context=conversation_context
                    )
                    
                    llm_response = {
                        "answer": fix_markdown_formatting(ai_result["response"]),  # Post-process markdown
                        "confidence_score": ai_result["confidence_score"],
                        "sources": self.source_enhancement_service.format_sources_for_response(search_results),
                        "ai_model": ai_result["model_used"],
                        "processing_time": ai_result["processing_time"],
                        "token_usage": ai_result.get("token_usage", {})
                    }
                    
                except Exception as groq_error:
                    # Check if it's a rate limit error (429)
                    error_str = str(groq_error)
                    
                    # For AppException, check both message and detail
                    if hasattr(groq_error, 'detail'):
                        error_str += f" {groq_error.detail}"
                    
                    is_rate_limit = (
                        "429" in error_str or 
                        "rate limit" in error_str.lower() or
                        "rate_limit_exceeded" in error_str.lower()
                    )
                    
                    if is_rate_limit:
                        logger.warning(f"Groq rate limit reached, falling back to OpenAI: {groq_error}")
                        
                        if self.openai_client:
                            try:
                                # Fallback to OpenAI GPT-4o
                                openai_response = await self._generate_openai_fallback(
                                    query=query,
                                    context=context_text,
                                    search_results=search_results,
                                    conversation_context=conversation_context
                                )
                                llm_response = openai_response
                                logger.info("Successfully used OpenAI fallback for rate-limited Groq request")
                            except Exception as openai_error:
                                logger.error(f"OpenAI fallback also failed: {openai_error}")
                                raise AppException(
                                    message="AI service temporarily unavailable - please try again in a few minutes",
                                    error_code="AI_SERVICE_UNAVAILABLE"
                                )
                        else:
                            logger.error("No OpenAI API key configured for fallback")
                            raise AppException(
                                message="AI service temporarily unavailable - please try again in a few minutes", 
                                error_code="AI_SERVICE_UNAVAILABLE"
                            )
                    else:
                        # Other Groq errors, re-raise
                        logger.error(f"Groq service error (non-rate-limit): {groq_error}")
                        raise groq_error
                        
            else:
                # Use Ollama service (fallback)
                llm_response = await ollama_service.generate_response(
                    query=query,
                    context=search_results,
                    institution_filter=institution_filter
                )
                # Post-process markdown for Ollama responses too
                if "answer" in llm_response:
                    llm_response["answer"] = fix_markdown_formatting(llm_response["answer"])
            
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
    
    async def _get_recent_conversation_context(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 10
    ) -> str:
        """Fetch last N user questions as context (best-effort)."""
        try:
            result = supabase_client.supabase.table("conversation_messages").select(
                "role, search_log_id, created_at"
            ).eq("conversation_id", conversation_id) \
             .eq("user_id", user_id) \
             .eq("role", "user") \
             .order("created_at", desc=True) \
             .limit(limit) \
             .execute()
            
            rows = result.data or []
            if not rows:
                return ""
            
            rows = list(reversed(rows))
            search_log_ids = [row.get("search_log_id") for row in rows if row.get("search_log_id")]
            if not search_log_ids:
                return ""
            
            logs_result = supabase_client.supabase.table("search_logs").select(
                "id, query, response"
            ).in_("id", search_log_ids).execute()
            log_map = {row["id"]: row for row in (logs_result.data or [])}
            
            lines = []
            for row in rows:
                log_id = row.get("search_log_id")
                if not log_id or log_id not in log_map:
                    continue
                log_row = log_map[log_id]
                text = log_row.get("query") or ""
                if text:
                    lines.append(text)
            
            if not lines:
                return ""
            
            header = "Önceki kullanıcı soruları (bağlam için, bilgi kaynağı değildir):"
            return header + "\n" + "\n".join([f"Kullanıcı: {text}" for text in lines])
            
        except Exception as e:
            logger.warning(f"Failed to load conversation context {conversation_id}: {e}")
            return ""
    
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
    
    async def _generate_openai_fallback(
        self, 
        query: str, 
        context: str, 
        search_results: List[Dict[str, Any]],
        conversation_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response using OpenAI as fallback when Groq fails
        
        Args:
            query: User's question
            context: Prepared context text
            search_results: Search results for source formatting
            
        Returns:
            Response dictionary compatible with Groq response format
        """
        start_time = time.time()
        
        try:
            # Get system prompt for legal questions
            from services.prompt_service import prompt_service
            system_message = await prompt_service.get_system_prompt("groq_legal")
            
            # Prepare messages for OpenAI
            conversation_section = ""
            if conversation_context and conversation_context.strip():
                conversation_section = (
                    "ÖNCEKİ KONUŞMALAR (yalnızca bağlam için, bilgi kaynağı değildir):\n"
                    f"{conversation_context}\n\n"
                )
            
            user_message = (
                f"{conversation_section}"
                f"Soru: {query}\n\n"
                f"Bağlam (BELGE İÇERİĞİ):\n{context}\n\n"
                "Yanıtını sadece BELGE İÇERİĞİNE dayandır."
            )
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # Call OpenAI GPT-4o
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                top_p=0.9
            )
            
            ai_response = response.choices[0].message.content
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                "answer": fix_markdown_formatting(ai_response),  # Post-process markdown
                "confidence_score": 0.8,  # Default confidence for OpenAI fallback
                "sources": self.source_enhancement_service.format_sources_for_response(search_results),
                "ai_model": "gpt-4o (fallback)",
                "processing_time": processing_time,
                "token_usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI fallback failed: {e}")
            raise AppException(
                message="AI service temporarily unavailable",
                error_code="OPENAI_FALLBACK_FAILED"
            )
    
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