"""
OpenAI Text-to-Speech (TTS) service for converting text to audio
"""

import logging
import base64
from typing import Dict, Any, Optional
import openai
from openai import AsyncOpenAI

from core.config import get_settings
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSService:
    """Service for text-to-speech conversion using OpenAI TTS"""
    
    def __init__(self):
        """Initialize TTS service with OpenAI client"""
        if not settings.OPENAI_API_KEY:
            raise AppException(
                message="OpenAI API key not configured",
                error_code="OPENAI_CONFIG_ERROR"
            )
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini-tts"  # Advanced TTS with customization
        self.default_voice = "alloy"  # Default voice
        logger.info(f"TTSService initialized with model: {self.model}")
    
    async def text_to_speech(
        self,
        text: str,
        voice: str = "alloy",
        instructions: Optional[str] = None,
        response_format: str = "mp3",
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """
        Convert text to speech using OpenAI TTS
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, ash, ballad, coral, echo, sage, shimmer, verse, marin, cedar)
            instructions: Optional voice instructions (only works with gpt-4o-mini-tts)
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
            speed: Speech speed (0.25 to 4.0)
            
        Returns:
            Dict containing audio data (base64 encoded) and metadata
            
        Raises:
            AppException: If TTS generation fails
        """
        try:
            logger.info(f"Generating TTS: {len(text)} chars, voice={voice}, format={response_format}")
            
            # Validate text length
            if len(text) == 0:
                raise AppException(
                    message="Text is empty",
                    detail="Cannot generate speech from empty text",
                    error_code="EMPTY_TEXT"
                )
            
            if len(text) > 4096:  # OpenAI TTS limit
                logger.warning(f"Text too long ({len(text)} chars), truncating to 4096")
                text = text[:4096]
            
            # Create TTS request parameters
            tts_params = {
                "model": self.model,
                "voice": voice,
                "input": text,
                "response_format": response_format,
                "speed": speed
            }
            
            # Add instructions only for gpt-4o-mini-tts
            if instructions and self.model == "gpt-4o-mini-tts":
                tts_params["instructions"] = instructions
            
            # Generate speech
            response = await self.client.audio.speech.create(**tts_params)
            
            # Get audio bytes
            audio_bytes = response.content
            
            # Encode to base64 for JSON response
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            logger.info(f"TTS generation successful: {len(audio_bytes)} bytes, {len(audio_base64)} base64 chars")
            
            return {
                "audio_base64": audio_base64,
                "audio_format": response_format,
                "audio_size_bytes": len(audio_bytes),
                "voice": voice,
                "model": self.model,
                "text_length": len(text)
            }
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI TTS error: {str(e)}")
            raise AppException(
                message="Text-to-speech generation failed",
                detail=f"OpenAI error: {str(e)}",
                error_code="TTS_GENERATION_FAILED"
            )
        except Exception as e:
            logger.error(f"TTS error: {str(e)}")
            raise AppException(
                message="Text-to-speech generation failed",
                detail=str(e),
                error_code="TTS_ERROR"
            )
