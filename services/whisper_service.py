"""
OpenAI Whisper transcription service for Turkish audio-to-text conversion
"""

import logging
import tempfile
import os
from typing import Dict, Any, Optional
import openai
from openai import AsyncOpenAI

from core.config import get_settings
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
settings = get_settings()


class WhisperService:
    """Service for audio transcription using OpenAI Whisper"""
    
    def __init__(self):
        """Initialize Whisper service with OpenAI client"""
        if not settings.OPENAI_API_KEY:
            raise AppException(
                message="OpenAI API key not configured",
                error_code="OPENAI_CONFIG_ERROR"
            )
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-transcribe"  # High quality Turkish transcription
        logger.info(f"WhisperService initialized with model: {self.model}")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.webm",
        language: str = "tr"
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text using OpenAI Whisper
        
        Args:
            audio_data: Raw audio file bytes
            filename: Original filename (for format detection)
            language: Language code (default: "tr" for Turkish)
            
        Returns:
            Dict containing transcribed text and metadata
            
        Raises:
            AppException: If transcription fails
        """
        temp_file_path = None
        
        try:
            # Create temporary file for audio data
            # OpenAI API requires file-like object
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            logger.info(f"Transcribing audio: {filename} ({len(audio_data)} bytes) in language: {language}")
            
            # Open file and send to OpenAI Whisper
            with open(temp_file_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    response_format="verbose_json"
                )
            
            # Extract transcription data
            transcribed_text = response.text
            duration = getattr(response, 'duration', None)
            
            logger.info(f"Transcription successful: {len(transcribed_text)} characters, duration: {duration}s")
            
            return {
                "text": transcribed_text,
                "language": language,
                "duration": duration,
                "model": self.model,
                "character_count": len(transcribed_text),
                "word_count": len(transcribed_text.split())
            }
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI Whisper error: {str(e)}")
            raise AppException(
                message="Audio transcription failed",
                detail=f"OpenAI error: {str(e)}",
                error_code="TRANSCRIPTION_FAILED"
            )
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise AppException(
                message="Audio transcription failed",
                detail=str(e),
                error_code="TRANSCRIPTION_ERROR"
            )
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Cleaned up temp file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {temp_file_path}: {e}")
