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
from services.prompt_service import prompt_service

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
        # Model bilgisi artık tamamen veritabanından çekilecek
        
        logger.info("Groq service initialized successfully")
    
    def get_current_settings(self) -> Dict[str, Any]:
        """
        Get current Groq settings directly from database
        
        Returns:
            Current Groq settings dictionary
        """
        try:
            # Import here to avoid circular imports
            from api.admin.groq_routes import get_groq_settings_from_db
            import asyncio
            
            # Get fresh settings from database
            if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() is not None:
                # We're in an async context, create a new event loop
                loop = asyncio.new_event_loop()
                settings = loop.run_until_complete(get_groq_settings_from_db())
                loop.close()
            else:
                # We're not in an async context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                settings = loop.run_until_complete(get_groq_settings_from_db())
                loop.close()
            
            return settings
            
        except Exception as e:
            logger.warning(f"Failed to get fresh settings from database: {str(e)}")
            return {
                "default_model": "llama-3.3-70b-versatile",  # Fallback default
                "temperature": 0.3,
                "max_tokens": 2048,
                "top_p": 0.9,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.6,
                "creativity_mode": "balanced",
                "response_style": "detailed",
                "available_models": [
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant", 
                    "gpt-oss-120B"
                ]
            }
    
    async def generate_response(
        self,
        query: str,
        context: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        response_style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response using Groq with dynamic admin settings
        
        Args:
            query: User's question/query
            context: Relevant document context
            model: Model to use (if not specified, uses admin settings)
            max_tokens: Maximum tokens in response (if not specified, uses admin settings)
            temperature: Response creativity (if not specified, uses admin settings)
            
        Returns:
            Dict with response, metadata, and performance metrics
        """
        start_time = time.time()
        
        try:
            # Get current admin settings
            current_settings = self.get_current_settings()
            
            # Use specified parameters or fall back to admin settings
            model_name = model or current_settings.get("default_model", "llama-3.3-70b-versatile")
            max_tokens_final = max_tokens or current_settings.get("max_tokens", 2048)
            temperature_final = temperature if temperature is not None else current_settings.get("temperature", 0.3)
            top_p = current_settings.get("top_p", 0.9)
            frequency_penalty = current_settings.get("frequency_penalty", 0.5)
            presence_penalty = current_settings.get("presence_penalty", 0.6)
            
            # Get dynamic system message from database
            system_message = await prompt_service.get_system_prompt("groq_legal")
            
            # Construct user message based on response style
            # Use provided response_style parameter or fall back to admin settings
            response_style_final = response_style or current_settings.get("response_style", "detailed")
            creativity_mode = current_settings.get("creativity_mode", "balanced")
            
            # Adjust user prompt based on response style
            # MARKDOWN FORMAT RULES - Applied to ALL styles
            markdown_formatting_rules = """
KRİTİK: MARKDOWN FORMATINI DOĞRU KULLAN - HER ELEMENTIN SONRASINDA MUTLAKA BOŞ SATIR!

TEMEL KURAL: Her markdown elementinin (başlık, liste, quote, paragraf) SONRASINDA mutlaka BOŞ SATIR bırak!

1. **BAŞLIKLAR** - Sonunda ## kapatma işareti YOK:
   
   DOĞRU ÖRNEK:
   
   ## Genel Açıklama
   
   Sigortalılık, bir bireyin sosyal güvenlik sistemi...
   
   ## Yasal Çerçeve
   
   İlgili mevzuat...
   
   YANLIŞ:
   ## Genel Açıklama ##
   Sigortalılık...

2. **PARAGRAFLAR** - Her paragraf arasında boş satır:
   
   DOĞRU ÖRNEK:
   
   Bu ilk paragraf bilgi içerir.
   
   Bu ikinci paragraf başka bilgi verir.
   
   Bu üçüncü paragraf sonuçtur.

3. **LİSTELER** - Liste öncesi ve sonrası boş satır:
   
   DOĞRU ÖRNEK:
   
   Başvuru için gerekli belgeler:
   
   - Kimlik fotokopisi
   - İkametgah belgesi
   - Hizmet akdi
   
   Belgeler teslim edildikten sonra...

4. **QUOTE BLOKLARI** - Quote öncesi ve sonrası boş satır:
   
   DOĞRU ÖRNEK:
   
   Kanun maddesi şu şekildedir:
   
   > "Madde 4/a: Hizmet akdi ile bir veya birden fazla işveren yanında çalışanlar sigortalı sayılır."
   
   Bu maddeye göre sigortalılık şartları...

5. **VURGULAR**:
   - **kalın** yazı (önemli terimler)
   - *italik* yazı (vurgu)
   - `kod formatı` (kanun numaraları, tarihler)

6. **KOMPLE DOĞRU ÖRNEK**:

## Genel Açıklama

Sigortalılık, **5510 sayılı Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu** kapsamında düzenlenen bir sistemdir.

## Yasal Çerçeve

İlgili düzenleme şu şekildedir:

> "Madde 4/a: Hizmet akdi ile bir veya birden fazla işveren yanında çalışanlar sigortalı sayılır."

Bu maddeye göre aşağıdaki şartlar aranır:

- Hizmet akdinin varlığı
- İşveren yanında çalışma
- **01.10.2008** tarihinden sonra işe başlama

Tescil işlemleri için `30 gün` süre tanınmıştır.

## Uygulama Detayları

Uygulamada dikkat edilmesi gereken hususlar vardır.

## Sonuç

Yukarıdaki bilgiler ışığında değerlendirme yapılabilir.
"""
            
            style_instructions = {
                "concise": f"""Kısa ve öz bir cevap ver. Ana noktaları özetleyerek maksimum 100-150 kelimelik açıklama yap.

{markdown_formatting_rules}""",
                "detailed": f"""Bu soruyu kapsamlı, detaylı ve analitik şekilde cevapla. Sadece kısa cevap verme - konuyu derinlemesine açıkla, belgedeki ilgili tüm bilgileri kullan ve hukuki terimleri anlaşılır şekilde açıkla. En az 200-300 kelimelik detaylı analiz yap.

{markdown_formatting_rules}

YAPISAL ORGANİZASYON (bu başlıkları kullan, arada boş satırlar bırak):

## Genel Açıklama

(giriş paragrafı - konunun temel tanımı)

## Yasal Çerçeve

(ilgili kanun maddeleri ve yasal düzenlemeler)

## Uygulama Detayları

(pratik bilgiler ve uygulamadaki durum)

## Önemli Noktalar

(dikkat edilmesi gerekenler ve özel durumlar)""",
                "analytical": f"""Bu soruyu analitik bir yaklaşımla cevapla. Konuyu sistematik olarak incele, farklı boyutlarını ele al ve hukuki çerçevede değerlendir. Sebep-sonuç ilişkilerini açıkla.

{markdown_formatting_rules}

YAPISAL ORGANİZASYON (bu başlıkları kullan, arada boş satırlar bırak):

## Hukuki Analiz

(yasal dayanak ve hukuki çerçeve)

## Değerlendirme

(farklı boyutlar ve sebep-sonuç ilişkileri)

## Sonuç ve Öneriler

(genel değerlendirme ve öneriler)""",
                "conversational": f"""Bu soruyu sohbet tarzında, anlaşılır ve samimi bir dille cevapla. Karmaşık terimleri basit örneklerle açıkla ve kullanıcıyla diyalog kuruyormuş gibi yaz.

{markdown_formatting_rules}"""
            }
            
            style_instruction = style_instructions.get(response_style_final, style_instructions["detailed"])
            
            # Construct user message with context
            if not context or context.strip() == "":
                user_message = f"""BELGE İÇERİĞİ: [BOŞ]

SORU: {query}

{style_instruction}"""
            else:
                user_message = f"""BELGE İÇERİĞİ:
{context}

SORU: {query}

{style_instruction}"""
            
            # Call Groq API with dynamic admin settings
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=max_tokens_final,
                temperature=temperature_final,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=False
            )
            
            # Extract response and clean repetitions
            ai_response = response.choices[0].message.content
            if ai_response:
                ai_response = ai_response.strip()
            else:
                ai_response = ""
            
            # Post-process to remove repetitive patterns
            ai_response = self._clean_repetitive_text(ai_response)
            
            # Calculate processing time
            processing_time = round(time.time() - start_time, 2)
            
            # Calculate confidence based on response characteristics
            confidence_score = self._calculate_confidence(ai_response, context)
            
            logger.info(f"Groq response generated in {processing_time}s (model: {model_name}, style: {response_style}, creativity: {creativity_mode})")
            
            return {
                "answer": ai_response,  # Match expected field name
                "response": ai_response,
                "model_used": model_name,
                "processing_time": processing_time,
                "generation_time_ms": int(processing_time * 1000),  # Add missing field
                "confidence_score": confidence_score,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "response_tokens": response.usage.completion_tokens if response.usage else 0,
                "token_usage": {
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "settings_used": {
                    "model": model_name,
                    "temperature": temperature_final,
                    "max_tokens": max_tokens_final,
                    "top_p": top_p,
                    "frequency_penalty": frequency_penalty,
                    "presence_penalty": presence_penalty,
                    "response_style": response_style,
                    "creativity_mode": creativity_mode
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
            if len(response) > 200:
                confidence += 0.1
            if len(response) > 500:
                confidence += 0.1
            if len(response) > 800:
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
    
    def _clean_repetitive_text(self, text: str) -> str:
        """
        Remove repetitive patterns from AI response
        
        Args:
            text: Raw AI response text
            
        Returns:
            Cleaned text without repetitions
        """
        try:
            import re
            
            # Remove obvious repetitive patterns like "text, text, text, text..."
            text = re.sub(r'(\b.{10,50}?)\s*,\s*\1(?:\s*,\s*\1){2,}', r'\1', text)
            
            # Remove sentences that repeat more than twice
            sentences = [s.strip() for s in re.split(r'[.!?]', text) if s.strip()]
            
            if len(sentences) <= 2:
                return text
            
            # Track sentence frequency and remove excessive repetitions
            sentence_count = {}
            cleaned_sentences = []
            
            for sentence in sentences:
                normalized = sentence.lower().strip()
                if len(normalized) < 10:  # Keep short sentences
                    cleaned_sentences.append(sentence)
                    continue
                    
                sentence_count[normalized] = sentence_count.get(normalized, 0) + 1
                
                # Only keep first 2 occurrences of any sentence
                if sentence_count[normalized] <= 2:
                    cleaned_sentences.append(sentence)
            
            # Reconstruct text
            if cleaned_sentences:
                cleaned_text = '. '.join(cleaned_sentences)
                if not cleaned_text.endswith('.'):
                    cleaned_text += '.'
                return cleaned_text
            
            return text
            
        except Exception as e:
            logger.warning(f"Error cleaning repetitive text: {e}")
            return text
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check Groq service health
        
        Returns:
            Health status and available models
        """
        try:
            # Get current model from settings
            current_settings = self.get_current_settings()
            model_name = current_settings.get("default_model", "llama-3.3-70b-versatile")
            
            # Simple test request
            test_response = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10,
                temperature=0
            )
            
            return {
                "status": "healthy",
                "default_model": model_name,
                "test_tokens": test_response.usage.total_tokens if test_response.usage else 0,
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
        Get list of available Groq models from database
        
        Returns:
            List of model names
        """
        try:
            # Get model list from admin settings
            current_settings = self.get_current_settings()
            models_from_db = current_settings.get("available_models", [])
            
            # If we got models from database, return them
            if models_from_db and isinstance(models_from_db, list) and len(models_from_db) > 0:
                logger.info(f"Loaded {len(models_from_db)} models from database")
                return models_from_db
            
            # Fallback: default 3 models if database is empty
            fallback_models = [
                "llama-3.3-70b-versatile",   # En güçlü model (70B, 128K context)
                "llama-3.1-8b-instant",      # Hızlı ve verimli (8B, fast)
                "gpt-oss-120B"               # OpenAI açık kaynak (120B, yeni)
            ]
            logger.warning("No models found in database, using fallback models")
            return fallback_models
            
        except Exception as e:
            logger.error(f"Error loading models from database: {str(e)}")
            # Emergency fallback
            return [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant", 
                "gpt-oss-120B"
            ]