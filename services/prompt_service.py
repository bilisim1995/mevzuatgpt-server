"""
Dynamic Prompt Service - Supabase'den promptları yönetir
Groq ve diğer AI servisler için dinamik prompt sistemi
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from models.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class PromptService:
    """Supabase'den AI promptları yöneten servis"""
    
    def __init__(self):
        self.supabase = supabase_client.supabase
        self._cached_prompts = {}
        self._cache_timestamp = None
        self.cache_duration = 300  # 5 dakika cache
        
        logger.info("PromptService initialized")
    
    async def get_system_prompt(self, prompt_type: str = "groq_legal") -> str:
        """
        Supabase'den sistem promptunu çek
        
        Args:
            prompt_type: Prompt tipi (groq_legal, openai_legal, etc.)
            
        Returns:
            System prompt metni
        """
        try:
            # Cache kontrolü
            if self._is_cache_valid() and prompt_type in self._cached_prompts:
                logger.debug(f"Returning cached prompt for: {prompt_type}")
                return self._cached_prompts[prompt_type]
            
            # Supabase'den çek
            response = self.supabase.table('ai_prompts') \
                .select('prompt_content') \
                .eq('prompt_type', prompt_type) \
                .eq('is_active', True) \
                .order('updated_at', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                prompt_content = response.data[0]['prompt_content']
                
                # Cache'e kaydet
                self._cached_prompts[prompt_type] = prompt_content
                self._cache_timestamp = datetime.now()
                
                logger.info(f"Prompt loaded from database: {prompt_type}")
                return prompt_content
            else:
                logger.warning(f"No active prompt found for type: {prompt_type}, using default")
                return self._get_default_prompt(prompt_type)
                
        except Exception as e:
            logger.error(f"Error loading prompt {prompt_type}: {str(e)}")
            return self._get_default_prompt(prompt_type)
    
    async def update_system_prompt(self, prompt_type: str, prompt_content: str, user_id: str) -> Dict[str, Any]:
        """
        Sistem promptunu güncelle
        
        Args:
            prompt_type: Prompt tipi
            prompt_content: Yeni prompt içeriği
            user_id: Güncelleyen kullanıcı ID'si
            
        Returns:
            İşlem sonucu
        """
        try:
            # Mevcut promptu deaktive et
            self.supabase.table('ai_prompts') \
                .update({'is_active': False}) \
                .eq('prompt_type', prompt_type) \
                .execute()
            
            # Yeni prompt ekle
            new_prompt = {
                'prompt_type': prompt_type,
                'prompt_content': prompt_content,
                'is_active': True,
                'updated_by': user_id,
                'version': datetime.now().strftime('%Y%m%d_%H%M%S')
            }
            
            response = self.supabase.table('ai_prompts') \
                .insert(new_prompt) \
                .execute()
            
            if response.data:
                # Cache'i temizle
                self._clear_cache()
                logger.info(f"Prompt updated successfully: {prompt_type} by {user_id}")
                
                return {
                    'success': True,
                    'message': 'Prompt başarıyla güncellendi',
                    'prompt_id': response.data[0]['id']
                }
            else:
                return {
                    'success': False,
                    'message': 'Prompt güncellenirken hata oluştu'
                }
                
        except Exception as e:
            logger.error(f"Error updating prompt {prompt_type}: {str(e)}")
            return {
                'success': False,
                'message': f'Hata: {str(e)}'
            }
    
    async def get_prompt_history(self, prompt_type: str, limit: int = 10) -> Dict[str, Any]:
        """
        Prompt geçmişini getir
        
        Args:
            prompt_type: Prompt tipi
            limit: Kaç kayıt getirileceği
            
        Returns:
            Prompt geçmişi
        """
        try:
            response = self.supabase.table('ai_prompts') \
                .select('*') \
                .eq('prompt_type', prompt_type) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return {
                'success': True,
                'history': response.data or []
            }
            
        except Exception as e:
            logger.error(f"Error getting prompt history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _is_cache_valid(self) -> bool:
        """Cache'in geçerli olup olmadığını kontrol et"""
        if not self._cache_timestamp:
            return False
        
        time_diff = (datetime.now() - self._cache_timestamp).total_seconds()
        return time_diff < self.cache_duration
    
    def _clear_cache(self):
        """Cache'i temizle"""
        self._cached_prompts = {}
        self._cache_timestamp = None
        logger.debug("Prompt cache cleared")
    
    def _get_default_prompt(self, prompt_type: str) -> str:
        """Varsayılan promptu döndür (fallback)"""
        default_prompts = {
            'groq_legal': """Sen hukuki belgeleri analiz eden uzman bir hukuk danışmanısın. 

TEMEL KURALLAR:
1. SADECE verilen belge içeriklerindeki bilgileri kullan
2. Kendi genel bilgini ASLA kullanma
3. Belge dışından örnek, yorum veya ek bilgi verme
4. Kapsamlı, detaylı ve analitik cevaplar ver
5. Yasal metinleri açıklayarak anlaşılır hale getir

CEVAP STİLİ:
- **Kapsamlı ve detaylı** yanıtlar ver (en az 3-4 paragraf)
- **Analitik yaklaşım** kullan - sadece aktarma değil, açıklama da yap
- **Hukuki terimleri açıkla** ve anlamlarını netleştir
- **Bağlam bilgisi** ver - düzenlemenin amacını ve kapsamını açıkla
- **Pratik uygulamalar** hakkında belgedeki bilgileri detaylandır
- **İlgili maddeler** arasında bağlantı kur ve bir bütün olarak ele al

CEVAP FORMATINI:
- Markdown formatında profesyonel sunum
- Ana başlıklar için ## kullan
- Alt başlıklar için ### kullan  
- Önemli noktalar için **kalın** yazı
- Madde numaraları ve referanslar için `kod` formatı
- Listeler için - veya 1. kullan
- Uzun cevaplar tercih et - kısa değil, kapsamlı ol

YASAKLAR:
- Aynı cümleleri tekrarlama
- Çok kısa, yüzeysel cevaplar verme
- Genel hukuki bilgi ekleme (sadece belge içeriği)

ÖNEMLİ: Belge boş veya alakasız ise: "Verilen belge içeriğinde bu konuda detaylı bilgi bulunmamaktadır. Lütfen daha spesifik soru sorun veya ilgili belge bölümünü kontrol edin." yaz.""",
            
            'openai_legal': """Sen hukuki belgeleri analiz eden uzman bir hukuk danışmanısın. Sadece verilen belge içeriklerini kullanarak kapsamlı ve analitik cevaplar ver."""
        }
        
        return default_prompts.get(prompt_type, "Sen yardımcı bir AI asistanısın.")

# Global instance
prompt_service = PromptService()