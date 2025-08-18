"""
Kredi Yönetim Servisi

Bu servis kullanıcıların kredi bakiyelerini yönetir ve transaction geçmişini tutar.
Modüler tasarım ile mevcut sistemi bozmadan entegre edilmiştir.

Özellikler:
- Kullanıcı kredi bakiye kontrolü
- Kredi düşme ve iade işlemleri  
- Transaction geçmiş takibi
- Admin kredi yönetimi
"""

import math
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

# Core imports için config kullanımı kaldırıldı
from models.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class CreditService:
    """Kullanıcı kredi yönetimi için modüler servis"""
    
    def __init__(self):
        self.initial_credit_amount = 30  # Yeni kullanıcılara verilen kredi
        self.base_credit_cost = 1        # Her sorgu için temel kredi
        self.character_threshold = 100   # Karakter bazlı ek kredi eşiği
    
    async def get_user_balance(self, user_id: str) -> int:
        """
        Kullanıcının mevcut kredi bakiyesini getir
        Admin kullanıcılar unlimited kredi sahibidir
        
        Args:
            user_id: Kullanıcı UUID'si
            
        Returns:
            Mevcut kredi bakiyesi (admin için 999999)
        """
        try:
            # Admin kullanıcılar için unlimited kredi
            if await self.is_admin_user(user_id):
                return 999999  # Unlimited credits for admin
            
            response = supabase_client.supabase.table('user_credit_balance') \
                .select('current_balance') \
                .eq('user_id', user_id) \
                .single() \
                .execute()
            
            if response.data:
                return response.data['current_balance']
            else:
                # Kullanıcının henüz kredi kaydı yoksa başlangıç kredisi ver
                await self.add_initial_credits(user_id)
                return self.initial_credit_amount
                
        except Exception as e:
            logger.error(f"Kullanıcı bakiye getirme hatası {user_id}: {e}")
            return 0
    
    def calculate_credit_cost(self, query: str) -> int:
        """
        Sorgu için gerekli kredi miktarını hesapla
        
        Formül: Temel Kredi (1) + Karakter Kredisi (uzunluk/100)
        
        Args:
            query: Kullanıcı sorusu
            
        Returns:
            Gerekli kredi miktarı
        """
        if not query:
            return self.base_credit_cost
            
        character_credits = math.ceil(len(query) / self.character_threshold)
        total_cost = self.base_credit_cost + character_credits
        
        logger.debug(f"Kredi hesaplama: '{query[:50]}...' -> {total_cost} kredi")
        return total_cost
    
    async def check_sufficient_credits(self, user_id: str, required_credits: int) -> bool:
        """
        Kullanıcının yeterli kredisi olup olmadığını kontrol et
        
        Args:
            user_id: Kullanıcı UUID'si
            required_credits: Gereken kredi miktarı
            
        Returns:
            True: Yeterli kredi var, False: Yetersiz kredi
        """
        current_balance = await self.get_user_balance(user_id)
        return current_balance >= required_credits
    
    async def deduct_credits(self, user_id: str, amount: int, description: str, 
                           query_id: Optional[str] = None) -> bool:
        """
        Kullanıcı kredisinden belirli miktarı düş
        Admin kullanıcılar için kredi düşme işlemi bypass edilir
        
        Args:
            user_id: Kullanıcı UUID'si
            amount: Düşülecek kredi miktarı
            description: İşlem açıklaması
            query_id: Sorgu referansı (opsiyonel)
            
        Returns:
            True: İşlem başarılı, False: İşlem başarısız
        """
        try:
            # Admin kullanıcılar için kredi düşme işlemi bypass et
            if await self.is_admin_user(user_id):
                logger.info(f"Admin kullanıcı kredi bypass: {user_id} - {description}")
                return True
            
            current_balance = await self.get_user_balance(user_id)
            
            if current_balance < amount:
                logger.warning(f"Yetersiz kredi: {user_id} - Bakiye: {current_balance}, Gerekli: {amount}")
                return False
            
            new_balance = current_balance - amount
            
            # Transaction kaydet
            transaction_data = {
                'user_id': user_id,
                'transaction_type': 'deduction',
                'amount': -amount,  # Negatif değer (düşüm)
                'balance_after': new_balance,
                'description': description,
                'query_id': query_id
            }
            
            response = supabase_client.supabase.table('user_credits') \
                .insert(transaction_data) \
                .execute()
            
            if response.data:
                logger.info(f"Kredi düşüldü: {user_id} - {amount} kredi, Kalan: {new_balance}")
                return True
            else:
                logger.error(f"Kredi düşme işlemi başarısız: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Kredi düşme hatası {user_id}: {e}")
            return False
    
    async def refund_credits(self, user_id: str, amount: int, query_id: str, 
                           reason: str = "İşlem hatası nedeniyle iade") -> bool:
        """
        Kullanıcıya kredi iadesi yap
        
        Args:
            user_id: Kullanıcı UUID'si
            amount: İade edilecek kredi miktarı
            query_id: Hangi sorgu için iade
            reason: İade nedeni
            
        Returns:
            True: İade başarılı, False: İade başarısız
        """
        try:
            current_balance = await self.get_user_balance(user_id)
            new_balance = current_balance + amount
            
            # İade transaction'ı kaydet
            transaction_data = {
                'user_id': user_id,
                'transaction_type': 'refund',
                'amount': amount,  # Pozitif değer (ekleme)
                'balance_after': new_balance,
                'description': reason,
                'query_id': query_id
            }
            
            response = supabase_client.supabase.table('user_credits') \
                .insert(transaction_data) \
                .execute()
            
            if response.data:
                logger.info(f"Kredi iadesi yapıldı: {user_id} - {amount} kredi, Toplam: {new_balance}")
                return True
            else:
                logger.error(f"Kredi iade işlemi başarısız: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Kredi iade hatası {user_id}: {e}")
            return False
    
    async def add_initial_credits(self, user_id: str) -> bool:
        """
        Yeni kullanıcıya başlangıç kredisi ekle
        
        Args:
            user_id: Kullanıcı UUID'si
            
        Returns:
            True: İşlem başarılı, False: İşlem başarısız
        """
        try:
            # Daha önce kredi verilmiş mi kontrol et
            existing = supabase_client.supabase.table('user_credits') \
                .select('id') \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()
            
            if existing.data:
                logger.info(f"Kullanıcı zaten kredi almış: {user_id}")
                return True
            
            # İlk kredi ver
            transaction_data = {
                'user_id': user_id,
                'transaction_type': 'initial',
                'amount': self.initial_credit_amount,
                'balance_after': self.initial_credit_amount,
                'description': 'İlk kayıt kredisi'
            }
            
            response = supabase_client.supabase.table('user_credits') \
                .insert(transaction_data) \
                .execute()
            
            if response.data:
                logger.info(f"Başlangıç kredisi verildi: {user_id} - {self.initial_credit_amount} kredi")
                return True
            else:
                logger.error(f"Başlangıç kredisi verilemedi: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Başlangıç kredisi hatası {user_id}: {e}")
            return False
    
    async def get_transaction_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Kullanıcının kredi transaction geçmişini getir
        
        Args:
            user_id: Kullanıcı UUID'si
            limit: Maksimum kayıt sayısı
            
        Returns:
            Transaction listesi
        """
        try:
            response = supabase_client.supabase.table('user_credits') \
                .select('*') \
                .eq('user_id', user_id) \
                .order('created_at', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Transaction geçmişi getirme hatası {user_id}: {e}")
            return []
    
    async def is_admin_user(self, user_id: str) -> bool:
        """
        Kullanıcının admin olup olmadığını kontrol et
        Admin kullanıcılar unlimited kredi kullanabilir
        
        Args:
            user_id: Kullanıcı UUID'si
            
        Returns:
            True: Admin kullanıcı, False: Normal kullanıcı
        """
        try:
            # user_profiles tablosundan role kontrol et (id column kullan, user_id değil)
            response = supabase_client.supabase.table('user_profiles') \
                .select('role') \
                .eq('id', user_id) \
                .single() \
                .execute()
            
            if response.data:
                return response.data.get('role') == 'admin'
            
            return False
            
        except Exception as e:
            logger.error(f"Admin kontrol hatası {user_id}: {e}")
            return False
    
    async def get_credit_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Kullanıcının kredi özet bilgilerini getir
        
        Args:
            user_id: Kullanıcı UUID'si
            
        Returns:
            Kredi özet bilgileri
        """
        try:
            # Mevcut bakiye
            current_balance = await self.get_user_balance(user_id)
            
            # Son işlemler
            recent_transactions = await self.get_transaction_history(user_id, limit=5)
            
            # İstatistikler
            stats_response = supabase_client.supabase.table('user_credits') \
                .select('transaction_type, amount') \
                .eq('user_id', user_id) \
                .execute()
            
            total_spent = 0
            total_earned = 0
            
            for tx in stats_response.data or []:
                if tx['amount'] < 0:
                    total_spent += abs(tx['amount'])
                else:
                    total_earned += tx['amount']
            
            return {
                'current_balance': current_balance,
                'total_earned': total_earned,
                'total_spent': total_spent,
                'recent_transactions': recent_transactions,
                'is_admin': await self.is_admin_user(user_id)
            }
            
        except Exception as e:
            logger.error(f"Kredi özet getirme hatası {user_id}: {e}")
            return {
                'current_balance': 0,
                'total_earned': 0,
                'total_spent': 0,
                'recent_transactions': [],
                'is_admin': False
            }

# Global instance
credit_service = CreditService()