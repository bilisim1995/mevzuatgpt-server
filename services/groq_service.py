"""
Groq service for fast AI inference
High-performance alternative to Ollama with cost efficiency
"""

import logging
from typing import Dict, Any, Optional, List
from groq import Groq
import time

from core.config import settings
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class GroqService:
    """Service class for Groq AI inference"""
    
    def __init__(self):
        """Initialize Groq client"""
        if not settings.GROQ_API_KEY:
            raise AppException(
                message="Groq API key not configured", 
                error_code="GROQ_CONFIG_ERROR"
            )
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.default_model = "llama3-8b-8192"  # Fast and efficient
        
        logger.info("Groq service initialized successfully")
    
    async def generate_response(
        self,
        prompt: str,
        context: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate AI response using Groq
        
        Args:
            prompt: User's question/prompt
            context: Relevant document context
            model: Model to use (default: llama3-8b-8192)
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.1 for factual responses)
            
        Returns:
            Dict with response, metadata, and performance metrics
        """
        start_time = time.time()
        
        try:
            # Use specified model or default
            model_name = model or self.default_model
            
            # Construct system message for legal document Q&A
            system_message = """Sen hukuki belge analiz uzmanısın. Görevin:
1. Verilen belge içeriğine dayalı doğru ve kesin cevaplar vermek
2. Kaynak belgeleri referans göstermek
3. Emin olmadığın konularda "bilgi yok" demek
4. Türkçe ve anlaşılır dilde cevap vermek
5. Hukuki terimler kullanırken açıklama yapmak"""
            
            # Construct user message with context
            user_message = f"""BELGE İÇERİĞİ:
{context}

SORU:
{prompt}

Lütfen yukarıdaki belge içeriğine dayanarak soruyu yanıtla. Cevabın belgede geçen bilgilerle desteklenmiş olsun."""
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                stream=False
            )
            
            # Extract response
            ai_response = response.choices[0].message.content.strip()
            
            # Calculate processing time
            processing_time = round(time.time() - start_time, 2)
            
            # Calculate confidence based on response characteristics
            confidence_score = self._calculate_confidence(ai_response, context)
            
            logger.info(f"Groq response generated in {processing_time}s (model: {model_name})")
            
            return {
                "response": ai_response,
                "model_used": model_name,
                "processing_time": processing_time,
                "confidence_score": confidence_score,
                "token_usage": {
                    "completion_tokens": response.usage.completion_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            error_msg = f"Groq API error: {str(e)}"
            logger.error(error_msg)
            raise AppException(
                message="AI response generation failed",
                detail=error_msg,
                error_code="GROQ_GENERATION_FAILED"
            )
    
    def _calculate_confidence(self, response: str, context: str) -> float:
        """
        Calculate confidence score for the AI response
        
        Args:
            response: Generated AI response
            context: Source context used
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Base confidence factors
            confidence = 0.5
            
            # Length factor (longer responses tend to be more comprehensive)
            if len(response) > 100:
                confidence += 0.1
            if len(response) > 300:
                confidence += 0.1
            
            # Context utilization (response should reference context)
            context_words = set(context.lower().split())
            response_words = set(response.lower().split())
            overlap_ratio = len(context_words.intersection(response_words)) / max(len(context_words), 1)
            confidence += overlap_ratio * 0.2
            
            # Uncertainty indicators (lower confidence if uncertain language)
            uncertainty_phrases = ['emin değilim', 'sanırım', 'belki', 'muhtemelen', 'galiba']
            for phrase in uncertainty_phrases:
                if phrase in response.lower():
                    confidence -= 0.1
            
            # Definitive language (higher confidence for definitive statements)
            definitive_phrases = ['kanun', 'madde', 'yönetmelik', 'karar', 'hüküm']
            definitive_count = sum(1 for phrase in definitive_phrases if phrase in response.lower())
            confidence += min(definitive_count * 0.05, 0.2)
            
            # Ensure confidence is within bounds
            confidence = max(0.0, min(1.0, confidence))
            
            return round(confidence, 2)
            
        except Exception as e:
            logger.warning(f"Error calculating confidence: {str(e)}")
            return 0.5  # Default confidence
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Groq service health
        
        Returns:
            Health status and available models
        """
        try:
            # Simple test request
            test_response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10,
                temperature=0
            )
            
            return {
                "status": "healthy",
                "default_model": self.default_model,
                "test_tokens": test_response.usage.total_tokens,
                "available": True
            }
            
        except Exception as e:
            logger.error(f"Groq health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "available": False
            }
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Groq models
        
        Returns:
            List of model names
        """
        # Groq's current model lineup (as of 2025)
        return [
            "llama3-8b-8192",      # Fast, efficient
            "llama3-70b-8192",     # More capable, slower
            "mixtral-8x7b-32768",  # Long context
            "gemma-7b-it"          # Google's model
        ]