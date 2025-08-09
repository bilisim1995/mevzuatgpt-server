"""
Feedback service - Kullanıcı geri bildirim yönetimi
Modüler tasarım ile mevcut sistemi etkilemeden feedback özelliği sağlar
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from models.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class FeedbackService:
    """Kullanıcı feedback yönetimi için modüler servis"""
    
    def __init__(self):
        self.supabase = supabase_client.supabase
    
    async def submit_feedback(
        self,
        user_id: str,
        search_log_id: str,
        query_text: str,
        answer_text: str,
        feedback_type: str,
        feedback_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Kullanıcı feedback'ini kaydet veya güncelle
        
        Args:
            user_id: Kullanıcı UUID'si
            search_log_id: Search log referansı
            query_text: Orijinal soru
            answer_text: Verilen cevap
            feedback_type: 'positive' veya 'negative'
            feedback_comment: Opsiyonel açıklama
            
        Returns:
            İşlem sonucu ve feedback bilgisi
        """
        try:
            # Validation
            if feedback_type not in ['positive', 'negative']:
                raise ValueError("feedback_type 'positive' veya 'negative' olmalı")
            
            # Feedback data
            feedback_data = {
                'user_id': user_id,
                'search_log_id': search_log_id,
                'query_text': query_text,
                'answer_text': answer_text,
                'feedback_type': feedback_type,
                'feedback_comment': feedback_comment
            }
            
            # UPSERT: Mevcut feedback varsa güncelle, yoksa ekle
            response = self.supabase.table('user_feedback') \
                .upsert(feedback_data, on_conflict='user_id,search_log_id') \
                .execute()
            
            if response.data:
                logger.info(f"Feedback kaydedildi: {user_id} - {search_log_id} - {feedback_type}")
                return {
                    'success': True,
                    'message': 'Feedback başarıyla kaydedildi',
                    'feedback': response.data[0]
                }
            else:
                logger.error(f"Feedback kaydetme başarısız: {user_id} - {search_log_id}")
                return {
                    'success': False,
                    'message': 'Feedback kaydedilemedi'
                }
                
        except Exception as e:
            logger.error(f"Feedback kaydetme hatası {user_id}: {e}")
            return {
                'success': False,
                'message': f'Feedback kaydetme hatası: {str(e)}'
            }
    
    async def get_user_feedback(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Kullanıcının feedback geçmişini getir
        
        Args:
            user_id: Kullanıcı UUID'si
            limit: Maksimum kayıt sayısı
            offset: Başlangıç pozisyonu
            
        Returns:
            Feedback listesi
        """
        try:
            response = self.supabase.table('user_feedback') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Kullanıcı feedback getirme hatası {user_id}: {e}")
            return []
    
    async def get_feedback_by_search_log(
        self,
        user_id: str,
        search_log_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Belirli bir sorgu için kullanıcının feedback'ini getir
        
        Args:
            user_id: Kullanıcı UUID'si
            search_log_id: Search log referansı
            
        Returns:
            Feedback bilgisi veya None
        """
        try:
            response = self.supabase.table('user_feedback') \
                .select('*') \
                .eq('user_id', user_id) \
                .eq('search_log_id', search_log_id) \
                .single() \
                .execute()
            
            return response.data
            
        except Exception as e:
            logger.debug(f"Feedback bulunamadı {user_id} - {search_log_id}: {e}")
            return None
    
    async def get_all_feedback_admin(
        self,
        feedback_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Tüm feedback'leri getir (admin için)
        
        Args:
            feedback_type: Filtre ('positive', 'negative' veya None)
            limit: Maksimum kayıt sayısı
            offset: Başlangıç pozisyonu
            
        Returns:
            Feedback listesi ve toplam sayı
        """
        try:
            # Base query - count parametresini kaldır
            query = self.supabase.table('user_feedback') \
                .select('*')
            
            # Tip filtresi
            if feedback_type:
                query = query.eq('feedback_type', feedback_type)
            
            # Execute with pagination
            response = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()
            
            return {
                'feedback_list': response.data or [],
                'total_count': response.count or 0,
                'has_more': (response.count or 0) > (offset + limit)
            }
            
        except Exception as e:
            logger.error(f"Admin feedback getirme hatası: {e}")
            return {
                'feedback_list': [],
                'total_count': 0,
                'has_more': False
            }
    
    async def delete_feedback(
        self,
        feedback_id: str,
        user_id: str
    ) -> bool:
        """
        Feedback'i sil (kullanıcı sadece kendi feedback'ini silebilir)
        
        Args:
            feedback_id: Feedback UUID'si
            user_id: Kullanıcı UUID'si
            
        Returns:
            Silme işlemi başarılı mı
        """
        try:
            response = self.supabase.table('user_feedback') \
                .delete() \
                .eq('id', feedback_id) \
                .eq('user_id', user_id) \
                .execute()
            
            if response.data:
                logger.info(f"Feedback silindi: {feedback_id} by {user_id}")
                return True
            else:
                logger.warning(f"Feedback silinemedi: {feedback_id} by {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Feedback silme hatası {feedback_id}: {e}")
            return False

# Global instance
feedback_service = FeedbackService()