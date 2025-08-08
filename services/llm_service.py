"""
LLM service for Ollama integration
Handles AI response generation using local Ollama instance
"""

import httpx
import json
import logging
import time
from typing import Dict, List, Any, Optional
from core.config import settings
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class OllamaService:
    """Service for interacting with Ollama LLM"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = getattr(settings, 'OLLAMA_MODEL', 'llama3')
        self.timeout = getattr(settings, 'OLLAMA_TIMEOUT', 30)
        self.max_tokens = getattr(settings, 'OLLAMA_MAX_TOKENS', 2048)
    
    async def generate_response(
        self, 
        query: str, 
        context: List[Dict[str, Any]],
        institution_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response using Ollama with context
        
        Args:
            query: User's question
            context: Search results from vector database
            institution_filter: Optional institution filter for context
            
        Returns:
            Dict with response, confidence score and metadata
        """
        try:
            start_time = time.time()
            
            # Build context text from search results
            context_text = self._build_context_text(context, institution_filter)
            
            # Create prompt
            prompt = self._create_prompt(query, context_text, institution_filter)
            
            # Generate response
            response_data = await self._call_ollama(prompt)
            
            generation_time = int((time.time() - start_time) * 1000)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(context, response_data)
            
            return {
                "answer": response_data.get("response", "").strip(),
                "confidence_score": confidence_score,
                "generation_time_ms": generation_time,
                "model_used": self.model,
                "context_sources": len(context),
                "prompt_tokens": response_data.get("prompt_eval_count", 0),
                "response_tokens": response_data.get("eval_count", 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise AppException(
                message="AI response generation failed",
                detail=str(e),
                error_code="LLM_GENERATION_FAILED"
            )
    
    def _build_context_text(
        self, 
        context: List[Dict[str, Any]], 
        institution_filter: Optional[str] = None
    ) -> str:
        """Build context text from search results"""
        if not context:
            return "İlgili belge bulunamadı."
        
        context_parts = []
        for i, result in enumerate(context, 1):
            # Filter by institution if specified
            if institution_filter:
                source_institution = result.get("source_institution", "").lower()
                if institution_filter.lower() not in source_institution:
                    continue
            
            title = result.get("document_title", "Bilinmeyen Belge")
            content = result.get("content", "")
            similarity = result.get("similarity_score", 0)
            institution = result.get("source_institution", "Bilinmeyen Kurum")
            
            context_parts.append(
                f"Kaynak {i} - {title} ({institution})\n"
                f"Benzerlik: {similarity:.2f}\n"
                f"İçerik: {content}\n"
            )
        
        if not context_parts:
            return f"'{institution_filter}' kurumuna ait ilgili belge bulunamadı."
        
        return "\n" + "="*50 + "\n".join(context_parts)
    
    def _create_prompt(
        self, 
        query: str, 
        context_text: str, 
        institution_filter: Optional[str] = None
    ) -> str:
        """Create structured prompt for Ollama"""
        
        institution_instruction = ""
        if institution_filter:
            institution_instruction = f"\n- Özellikle '{institution_filter}' kurumunun belgelerine odaklan"
        
        prompt = f"""Sen Türkiye hukuk sisteminde uzman bir asistansın. Aşağıdaki hukuki belge içeriklerini kullanarak kullanıcının sorusuna doğru, kapsamlı ve anlaşılır bir cevap ver.

SORU: {query}

HUKUKI BELGE İÇERİKLERİ:
{context_text}

YANIT KURALLARI:
- Sadece verilen belge içeriklerini kullan
- Eğer sorunun cevabı belgelerde yoksa, bunu açıkça belirt
- Cevabını hangi belgelerden aldığını belirt
- Hukuki terminolojiyi anlaşılır şekilde açıkla
- Türkçe, net ve yapılandırılmış bir cevap ver
- Belirsizlik varsa, bunları belirt{institution_instruction}
- Madde numaralarını ve kaynak bilgilerini dahil et

CEVAP:"""
        
        return prompt
    
    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Make HTTP request to Ollama API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Lower for more consistent legal responses
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                            "num_predict": self.max_tokens
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise AppException(
                        message=f"Ollama API error: {response.status_code}",
                        detail=response.text,
                        error_code="OLLAMA_API_ERROR"
                    )
                
                return response.json()
                
        except httpx.TimeoutException:
            raise AppException(
                message="Ollama request timeout",
                detail=f"Request took longer than {self.timeout} seconds",
                error_code="OLLAMA_TIMEOUT"
            )
        except httpx.ConnectError:
            raise AppException(
                message="Cannot connect to Ollama",
                detail=f"Failed to connect to {self.base_url}",
                error_code="OLLAMA_CONNECTION_ERROR"
            )
    
    def _calculate_confidence_score(
        self, 
        context: List[Dict[str, Any]], 
        response_data: Dict[str, Any]
    ) -> float:
        """Calculate confidence score based on context quality and response"""
        if not context:
            return 0.1
        
        # Base confidence from search results
        avg_similarity = sum(
            result.get("similarity_score", 0) for result in context
        ) / len(context)
        
        # Adjust based on number of sources
        source_factor = min(len(context) / 5, 1.0)  # Max benefit from 5 sources
        
        # Adjust based on response length (longer responses often more comprehensive)
        response_text = response_data.get("response", "")
        length_factor = min(len(response_text) / 500, 1.0)  # Normalize to 500 chars
        
        # Combine factors
        confidence = (
            avg_similarity * 0.6 +  # Search relevance most important
            source_factor * 0.25 +  # Number of sources
            length_factor * 0.15    # Response completeness
        )
        
        return round(min(confidence, 0.95), 2)  # Cap at 95%
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama service is available"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/version")
                
                if response.status_code == 200:
                    version_data = response.json()
                    return {
                        "status": "healthy",
                        "version": version_data.get("version", "unknown"),
                        "model": self.model,
                        "base_url": self.base_url
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status_code}",
                        "base_url": self.base_url
                    }
                    
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "base_url": self.base_url
            }
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return models
                else:
                    logger.warning(f"Failed to get models: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.warning(f"Failed to get available models: {e}")
            return []

# Global LLM service instance
ollama_service = OllamaService()