"""
Dosya Okuma ve OCR Servisi
PDF, Word, Resim formatlarından metin çıkarır
"""

import logging
import io
import base64
from typing import Dict, Any, BinaryIO
from pathlib import Path
import pdfplumber
from PIL import Image
from openai import AsyncOpenAI

from core.config import settings

logger = logging.getLogger(__name__)


class FileOCRService:
    """Dosyalardan metin çıkaran ve OCR yapan servis"""
    
    SUPPORTED_FORMATS = {
        'pdf': ['.pdf'],
        'word': ['.docx', '.doc'],
        'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
        'text': ['.txt', '.md']
    }
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def extract_text_from_file(
        self,
        file_content: bytes,
        filename: str,
        use_nlp: bool = True
    ) -> Dict[str, Any]:
        """
        Dosyadan metin çıkar (format otomatik tespit)
        
        Args:
            file_content: Dosya içeriği (bytes)
            filename: Dosya adı
            use_nlp: NLP ile metin temizleme yapılsın mı
            
        Returns:
            Dict: {
                'text': str,
                'format': str,
                'method': str,
                'confidence': float
            }
        """
        try:
            file_ext = Path(filename).suffix.lower()
            
            # Format tespiti
            if file_ext in self.SUPPORTED_FORMATS['pdf']:
                result = await self._extract_from_pdf(file_content)
            elif file_ext in self.SUPPORTED_FORMATS['word']:
                result = await self._extract_from_word(file_content)
            elif file_ext in self.SUPPORTED_FORMATS['image']:
                result = await self._extract_from_image(file_content, use_nlp)
            elif file_ext in self.SUPPORTED_FORMATS['text']:
                result = await self._extract_from_text(file_content)
            else:
                raise ValueError(f"Desteklenmeyen dosya formatı: {file_ext}")
            
            # NLP ile temizleme (opsiyonel)
            if use_nlp and result.get('text'):
                result['text'] = self._clean_text_with_nlp(result['text'])
            
            return result
            
        except Exception as e:
            logger.error(f"Text extraction failed for {filename}: {str(e)}")
            raise
    
    async def _extract_from_pdf(self, file_content: bytes) -> Dict[str, Any]:
        """PDF'den metin çıkar"""
        
        try:
            text_parts = []
            
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            full_text = "\n\n".join(text_parts)
            
            return {
                'text': full_text,
                'format': 'pdf',
                'method': 'pdfplumber',
                'confidence': 0.95,
                'pages': len(text_parts)
            }
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            raise ValueError(f"PDF okuma hatası: {str(e)}")
    
    async def _extract_from_word(self, file_content: bytes) -> Dict[str, Any]:
        """Word belgesinden metin çıkar"""
        
        try:
            from docx import Document
            
            doc = Document(io.BytesIO(file_content))
            text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
            full_text = "\n\n".join(text_parts)
            
            return {
                'text': full_text,
                'format': 'word',
                'method': 'python-docx',
                'confidence': 0.98,
                'paragraphs': len(text_parts)
            }
            
        except ImportError:
            raise ValueError("python-docx kütüphanesi kurulu değil. Lütfen 'pip install python-docx' çalıştırın.")
        except Exception as e:
            logger.error(f"Word extraction failed: {str(e)}")
            raise ValueError(f"Word belgesi okuma hatası: {str(e)}")
    
    async def _extract_from_image(
        self,
        file_content: bytes,
        use_advanced_ocr: bool = True
    ) -> Dict[str, Any]:
        """Resimden OCR ile metin çıkar"""
        
        if use_advanced_ocr and self.openai_client:
            return await self._ocr_with_openai_vision(file_content)
        else:
            # Fallback: Tesseract (eğer kuruluysa)
            return await self._ocr_with_tesseract(file_content)
    
    async def _ocr_with_openai_vision(self, file_content: bytes) -> Dict[str, Any]:
        """OpenAI Vision API ile gelişmiş OCR"""
        
        try:
            # Base64 encode
            base64_image = base64.b64encode(file_content).decode('utf-8')
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Sen Türkçe mevzuat belgelerini okuyabilen bir OCR asistanısın. Resimdeki metni kelime kelime, noktalama işaretleriyle birlikte aynen çıkar. Hiçbir şey ekleme, sadece gördüğün metni yaz."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Bu resimdeki tüm metni oku ve aynen yaz. Sadece metni çıkar, başka açıklama yapma."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            extracted_text = response.choices[0].message.content
            
            return {
                'text': extracted_text,
                'format': 'image',
                'method': 'openai-vision-ocr',
                'confidence': 0.92,
                'model': 'gpt-4o-mini'
            }
            
        except Exception as e:
            logger.error(f"OpenAI Vision OCR failed: {str(e)}")
            # Fallback to Tesseract
            return await self._ocr_with_tesseract(file_content)
    
    async def _ocr_with_tesseract(self, file_content: bytes) -> Dict[str, Any]:
        """Tesseract OCR ile metin çıkar (fallback)"""
        
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(io.BytesIO(file_content))
            
            # Türkçe dil desteği ile OCR
            text = pytesseract.image_to_string(
                image,
                lang='tur',
                config='--psm 6'  # Assume uniform block of text
            )
            
            return {
                'text': text,
                'format': 'image',
                'method': 'tesseract-ocr',
                'confidence': 0.75,
                'language': 'turkish'
            }
            
        except ImportError:
            raise ValueError(
                "OCR kütüphaneleri kurulu değil. "
                "OpenAI Vision API kullanılamıyor ve Tesseract kurulu değil."
            )
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {str(e)}")
            raise ValueError(f"OCR işlemi başarısız: {str(e)}")
    
    async def _extract_from_text(self, file_content: bytes) -> Dict[str, Any]:
        """Plain text dosyasından metin çıkar"""
        
        try:
            # Encoding detection
            encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'latin1']
            
            for encoding in encodings:
                try:
                    text = file_content.decode(encoding)
                    return {
                        'text': text,
                        'format': 'text',
                        'method': 'direct-read',
                        'confidence': 1.0,
                        'encoding': encoding
                    }
                except UnicodeDecodeError:
                    continue
            
            # Son çare: errors='ignore' ile oku
            text = file_content.decode('utf-8', errors='ignore')
            return {
                'text': text,
                'format': 'text',
                'method': 'direct-read-fallback',
                'confidence': 0.85,
                'encoding': 'utf-8-fallback'
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise ValueError(f"Metin okuma hatası: {str(e)}")
    
    def _clean_text_with_nlp(self, text: str) -> str:
        """NLP ile metin temizleme ve normalizasyon"""
        
        import re
        
        # 1. Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # 2. Satır sonlarını düzelt
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 3. Türkçe karakterleri koru
        # (Zaten doğru şekilde işleniyor)
        
        # 4. Madde numaralarını düzelt
        text = re.sub(r'MADDE\s*(\d+)', r'MADDE \1', text)
        
        # 5. Boş satırları temizle
        text = text.strip()
        
        return text
    
    def get_supported_formats(self) -> Dict[str, list]:
        """Desteklenen dosya formatlarını döndür"""
        return self.SUPPORTED_FORMATS
    
    @staticmethod
    def validate_file_size(file_size: int, max_size_mb: int = 10) -> bool:
        """Dosya boyutu kontrolü"""
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size <= max_size_bytes
