"""
Support Service - Destek ticket sistemi iş mantığı
Modüler tasarım ile mevcut sistemi etkilemeden ticket yönetimi sağlar
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from models.supabase_client import supabase_client
from models.support_schemas import (
    TicketCategory, TicketPriority, TicketStatus,
    TicketFilterParams, SupportTicket, SupportMessage,
    SupportTicketDetail
)

logger = logging.getLogger(__name__)


class SupportService:
    """Destek ticket yönetimi için modüler servis"""
    
    def __init__(self):
        self.supabase = supabase_client.supabase
    
    async def create_ticket(
        self,
        user_id: str,
        subject: str,
        category: TicketCategory,
        priority: TicketPriority,
        initial_message: str
    ) -> Dict[str, Any]:
        """Yeni destek ticket'ı oluştur"""
        try:
            # 1. Ticket oluştur
            ticket_data = {
                'user_id': user_id,
                'subject': subject,
                'category': category.value if isinstance(category, TicketCategory) else category,
                'priority': priority.value if isinstance(priority, TicketPriority) else priority,
                'status': 'acik'
            }
            
            ticket_response = self.supabase.table('support_tickets') \
                .insert(ticket_data) \
                .execute()
            
            if not ticket_response.data:
                return {
                    'success': False,
                    'error': 'Ticket oluşturulamadı'
                }
            
            ticket = ticket_response.data[0]
            ticket_id = ticket['id']
            
            # 2. İlk mesajı ekle
            message_data = {
                'ticket_id': ticket_id,
                'sender_id': user_id,
                'message': initial_message
            }
            
            message_response = self.supabase.table('support_messages') \
                .insert(message_data) \
                .execute()
            
            if not message_response.data:
                # Ticket'ı da sil (rollback)
                self.supabase.table('support_tickets').delete().eq('id', ticket_id).execute()
                return {
                    'success': False,
                    'error': 'Ticket mesajı oluşturulamadı'
                }
            
            logger.info(f"Yeni ticket oluşturuldu: {ticket['ticket_number']} - {user_id}")
            
            return {
                'success': True,
                'message': 'Destek talebiniz başarıyla oluşturuldu',
                'ticket': ticket,
                'ticket_id': ticket_id
            }
            
        except Exception as e:
            logger.error(f"Ticket oluşturma hatası {user_id}: {e}")
            return {
                'success': False,
                'error': 'Sistem hatası oluştu'
            }
    
    async def get_user_tickets(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 10,
        filters: Optional[TicketFilterParams] = None
    ) -> Dict[str, Any]:
        """Kullanıcının ticket'larını listele"""
        try:
            # Base query
            query = self.supabase.table('support_tickets') \
                .select('''
                    id, ticket_number, subject, category, priority, status,
                    created_at, updated_at,
                    user_profiles!inner(id, full_name, email)
                ''') \
                .eq('user_id', user_id)
            
            # Filtreler uygula
            if filters:
                if filters.status:
                    query = query.eq('status', filters.status.value if hasattr(filters.status, 'value') else filters.status)
                if filters.category:
                    query = query.eq('category', filters.category.value if hasattr(filters.category, 'value') else filters.category)
                if filters.priority:
                    query = query.eq('priority', filters.priority.value if hasattr(filters.priority, 'value') else filters.priority)
                if filters.search:
                    query = query.ilike('subject', f'%{filters.search}%')
            
            # Toplam kayıt sayısını al
            count_query = self.supabase.table('support_tickets') \
                .select('id') \
                .eq('user_id', user_id)
            
            if filters:
                if filters.status:
                    count_query = count_query.eq('status', filters.status.value if hasattr(filters.status, 'value') else filters.status)
                if filters.category:
                    count_query = count_query.eq('category', filters.category.value if hasattr(filters.category, 'value') else filters.category)
                if filters.priority:
                    count_query = count_query.eq('priority', filters.priority.value if hasattr(filters.priority, 'value') else filters.priority)
                if filters.search:
                    count_query = count_query.ilike('subject', f'%{filters.search}%')
            
            count_response = count_query.execute()
            total_count = len(count_response.data) if count_response.data else 0
            
            # Sayfalama ve sıralama
            offset = (page - 1) * limit
            query = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1)
            
            response = query.execute()
            
            if not response.data:
                return {
                    'success': True,
                    'tickets': [],
                    'total_count': 0,
                    'has_more': False,
                    'page': page,
                    'limit': limit
                }
            
            # Her ticket için mesaj sayısı ve son yanıt tarihini al
            tickets_with_stats = []
            for ticket in response.data:
                # Mesaj istatistikleri
                message_stats = self.supabase.table('support_messages') \
                    .select('id, created_at') \
                    .eq('ticket_id', ticket['id']) \
                    .order('created_at', desc=True) \
                    .execute()
                
                ticket['message_count'] = len(message_stats.data) if message_stats.data else 0
                ticket['last_reply_at'] = message_stats.data[0]['created_at'] if message_stats.data else None
                
                # User profile bilgilerini düzelt
                if ticket.get('user_profiles'):
                    profile = ticket['user_profiles']
                    ticket['user_name'] = profile.get('full_name')
                    ticket['user_email'] = profile.get('email')
                    del ticket['user_profiles']
                
                tickets_with_stats.append(ticket)
            
            has_more = total_count > (page * limit)
            
            return {
                'success': True,
                'tickets': tickets_with_stats,
                'total_count': total_count,
                'has_more': has_more,
                'page': page,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Kullanıcı ticket listesi hatası {user_id}: {e}")
            return {
                'success': False,
                'error': 'Ticketlar yüklenirken hata oluştu'
            }
    
    async def get_ticket_detail(
        self,
        ticket_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Ticket detaylarını ve mesajları getir"""
        try:
            # Ticket bilgilerini getir
            ticket_query = self.supabase.table('support_tickets') \
                .select('''
                    id, ticket_number, user_id, subject, category, priority, status,
                    created_at, updated_at,
                    user_profiles!inner(id, full_name, email)
                ''') \
                .eq('id', ticket_id)
            
            # Yetki kontrolü
            if not is_admin:
                ticket_query = ticket_query.eq('user_id', user_id)
            
            ticket_response = ticket_query.execute()
            
            if not ticket_response.data:
                return {
                    'success': False,
                    'error': 'Ticket bulunamadı veya erişim yetkiniz yok'
                }
            
            ticket = ticket_response.data[0]
            
            # User profile bilgilerini düzelt
            if ticket.get('user_profiles'):
                profile = ticket['user_profiles']
                ticket['user_name'] = profile.get('full_name')
                ticket['user_email'] = profile.get('email')
                del ticket['user_profiles']
            
            # Ticket mesajlarını getir
            messages_response = self.supabase.table('support_messages') \
                .select('''
                    id, ticket_id, sender_id, message, created_at,
                    user_profiles!inner(id, full_name, email, role)
                ''') \
                .eq('ticket_id', ticket_id) \
                .order('created_at', desc=False) \
                .execute()
            
            messages = []
            if messages_response.data:
                for msg in messages_response.data:
                    # Sender bilgilerini düzelt
                    if msg.get('user_profiles'):
                        profile = msg['user_profiles']
                        msg['sender_name'] = profile.get('full_name')
                        msg['sender_email'] = profile.get('email')
                        msg['is_admin'] = profile.get('role') == 'admin'
                        del msg['user_profiles']
                    
                    messages.append(msg)
            
            ticket['messages'] = messages
            ticket['message_count'] = len(messages)
            ticket['last_reply_at'] = messages[-1]['created_at'] if messages else None
            
            return {
                'success': True,
                'ticket': ticket
            }
            
        except Exception as e:
            logger.error(f"Ticket detay hatası {ticket_id}: {e}")
            return {
                'success': False,
                'error': 'Ticket detayları yüklenirken hata oluştu'
            }
    
    async def add_message(
        self,
        ticket_id: str,
        sender_id: str,
        message: str,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """Ticket'a yeni mesaj ekle"""
        try:
            # Önce ticket'ın varlığını ve yetki kontrolü
            ticket_query = self.supabase.table('support_tickets') \
                .select('id, user_id, status') \
                .eq('id', ticket_id)
            
            # Admin değilse sadece kendi ticket'ına mesaj gönderebilir
            if not is_admin:
                ticket_query = ticket_query.eq('user_id', sender_id)
            
            ticket_response = ticket_query.execute()
            
            if not ticket_response.data:
                return {
                    'success': False,
                    'error': 'Ticket bulunamadı veya erişim yetkiniz yok'
                }
            
            ticket = ticket_response.data[0]
            
            # Kapalı ticket'a mesaj engellemesi
            if ticket['status'] == 'kapatildi':
                return {
                    'success': False,
                    'error': 'Kapalı ticketlara mesaj eklenemez'
                }
            
            # Mesaj ekle
            message_data = {
                'ticket_id': ticket_id,
                'sender_id': sender_id,
                'message': message
            }
            
            message_response = self.supabase.table('support_messages') \
                .insert(message_data) \
                .execute()
            
            if not message_response.data:
                return {
                    'success': False,
                    'error': 'Mesaj gönderilemedi'
                }
            
            # Ticket durumunu güncelle
            new_status = 'cevaplandi' if is_admin else 'acik'
            self.supabase.table('support_tickets') \
                .update({'status': new_status, 'updated_at': 'now()'}) \
                .eq('id', ticket_id) \
                .execute()
            
            logger.info(f"Yeni mesaj eklendi: {ticket_id} - {sender_id} - Admin: {is_admin}")
            
            return {
                'success': True,
                'message': 'Mesajınız başarıyla gönderildi',
                'support_message': message_response.data[0]
            }
            
        except Exception as e:
            logger.error(f"Mesaj ekleme hatası {ticket_id}: {e}")
            return {
                'success': False,
                'error': 'Mesaj gönderilirken hata oluştu'
            }
    
    async def update_ticket_status(
        self,
        ticket_id: str,
        new_status: TicketStatus,
        admin_user_id: str
    ) -> Dict[str, Any]:
        """Ticket durumunu güncelle (Sadece Admin)"""
        try:
            # Admin kontrolü
            admin_check = await self._verify_admin(admin_user_id)
            if not admin_check:
                return {
                    'success': False,
                    'error': 'Bu işlem için admin yetkisi gerekli'
                }
            
            # Ticket varlık kontrolü
            ticket_response = self.supabase.table('support_tickets') \
                .select('id, status') \
                .eq('id', ticket_id) \
                .execute()
            
            if not ticket_response.data:
                return {
                    'success': False,
                    'error': 'Ticket bulunamadı'
                }
            
            # Status güncelle
            status_value = new_status.value if hasattr(new_status, 'value') else new_status
            update_response = self.supabase.table('support_tickets') \
                .update({'status': status_value, 'updated_at': 'now()'}) \
                .eq('id', ticket_id) \
                .execute()
            
            if update_response.data:
                logger.info(f"Ticket durumu güncellendi: {ticket_id} -> {status_value}")
                return {
                    'success': True,
                    'message': f'Ticket durumu {status_value} olarak güncellendi'
                }
            else:
                return {
                    'success': False,
                    'error': 'Durum güncellenemedi'
                }
            
        except Exception as e:
            logger.error(f"Ticket durum güncelleme hatası {ticket_id}: {e}")
            return {
                'success': False,
                'error': 'Durum güncellenirken hata oluştu'
            }
    
    async def get_admin_tickets(
        self,
        admin_user_id: str,
        page: int = 1,
        limit: int = 20,
        filters: Optional[TicketFilterParams] = None
    ) -> Dict[str, Any]:
        """Admin için tüm ticket'ları listele"""
        try:
            # Admin kontrolü
            admin_check = await self._verify_admin(admin_user_id)
            if not admin_check:
                return {
                    'success': False,
                    'error': 'Bu işlem için admin yetkisi gerekli'
                }
            
            # Base query
            query = self.supabase.table('support_tickets') \
                .select('''
                    id, ticket_number, user_id, subject, category, priority, status,
                    created_at, updated_at,
                    user_profiles!inner(id, full_name, email)
                ''')
            
            # Filtreler uygula
            if filters:
                if filters.status:
                    query = query.eq('status', filters.status.value if hasattr(filters.status, 'value') else filters.status)
                if filters.category:
                    query = query.eq('category', filters.category.value if hasattr(filters.category, 'value') else filters.category)
                if filters.priority:
                    query = query.eq('priority', filters.priority.value if hasattr(filters.priority, 'value') else filters.priority)
                if filters.user_id:
                    query = query.eq('user_id', filters.user_id)
                if filters.search:
                    query = query.or_(f'subject.ilike.%{filters.search}%,ticket_number.ilike.%{filters.search}%')
            
            # Toplam kayıt sayısını al
            count_query = self.supabase.table('support_tickets').select('id')
            
            if filters:
                if filters.status:
                    count_query = count_query.eq('status', filters.status.value if hasattr(filters.status, 'value') else filters.status)
                if filters.category:
                    count_query = count_query.eq('category', filters.category.value if hasattr(filters.category, 'value') else filters.category)
                if filters.priority:
                    count_query = count_query.eq('priority', filters.priority.value if hasattr(filters.priority, 'value') else filters.priority)
                if filters.user_id:
                    count_query = count_query.eq('user_id', filters.user_id)
                if filters.search:
                    count_query = count_query.or_(f'subject.ilike.%{filters.search}%,ticket_number.ilike.%{filters.search}%')
            
            count_response = count_query.execute()
            total_count = len(count_response.data) if count_response.data else 0
            
            # Sayfalama ve sıralama
            offset = (page - 1) * limit
            query = query.order('created_at', desc=True) \
                .range(offset, offset + limit - 1)
            
            response = query.execute()
            
            tickets_with_stats = []
            if response.data:
                for ticket in response.data:
                    # Mesaj istatistikleri
                    message_stats = self.supabase.table('support_messages') \
                        .select('id, created_at') \
                        .eq('ticket_id', ticket['id']) \
                        .order('created_at', desc=True) \
                        .execute()
                    
                    ticket['message_count'] = len(message_stats.data) if message_stats.data else 0
                    ticket['last_reply_at'] = message_stats.data[0]['created_at'] if message_stats.data else None
                    
                    # User profile bilgilerini düzelt
                    if ticket.get('user_profiles'):
                        profile = ticket['user_profiles']
                        ticket['user_name'] = profile.get('full_name')
                        ticket['user_email'] = profile.get('email')
                        del ticket['user_profiles']
                    
                    tickets_with_stats.append(ticket)
            
            has_more = total_count > (page * limit)
            
            return {
                'success': True,
                'tickets': tickets_with_stats,
                'total_count': total_count,
                'has_more': has_more,
                'page': page,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"Admin ticket listesi hatası {admin_user_id}: {e}")
            return {
                'success': False,
                'error': 'Ticketlar yüklenirken hata oluştu'
            }
    
    async def get_ticket_stats(self, admin_user_id: str) -> Dict[str, Any]:
        """Admin için ticket istatistikleri"""
        try:
            # Admin kontrolü
            admin_check = await self._verify_admin(admin_user_id)
            if not admin_check:
                return {
                    'success': False,
                    'error': 'Bu işlem için admin yetkisi gerekli'
                }
            
            # Genel istatistikler
            all_tickets = self.supabase.table('support_tickets') \
                .select('status, category, priority, created_at') \
                .execute()
            
            if not all_tickets.data:
                return {
                    'success': True,
                    'stats': {
                        'total_tickets': 0,
                        'open_tickets': 0,
                        'answered_tickets': 0,
                        'closed_tickets': 0,
                        'by_category': {},
                        'by_priority': {}
                    }
                }
            
            tickets = all_tickets.data
            total_tickets = len(tickets)
            
            # Durum istatistikleri
            open_tickets = len([t for t in tickets if t['status'] == 'acik'])
            answered_tickets = len([t for t in tickets if t['status'] == 'cevaplandi'])
            closed_tickets = len([t for t in tickets if t['status'] == 'kapatildi'])
            
            # Kategori istatistikleri
            by_category = {}
            for ticket in tickets:
                category = ticket['category']
                by_category[category] = by_category.get(category, 0) + 1
            
            # Öncelik istatistikleri
            by_priority = {}
            for ticket in tickets:
                priority = ticket['priority']
                by_priority[priority] = by_priority.get(priority, 0) + 1
            
            return {
                'success': True,
                'stats': {
                    'total_tickets': total_tickets,
                    'open_tickets': open_tickets,
                    'answered_tickets': answered_tickets,
                    'closed_tickets': closed_tickets,
                    'by_category': by_category,
                    'by_priority': by_priority
                }
            }
            
        except Exception as e:
            logger.error(f"Ticket istatistik hatası {admin_user_id}: {e}")
            return {
                'success': False,
                'error': 'İstatistikler yüklenirken hata oluştu'
            }
    
    async def _verify_admin(self, user_id: str) -> bool:
        """Admin yetkisi kontrol et"""
        try:
            user_response = self.supabase.table('user_profiles') \
                .select('role') \
                .eq('id', user_id) \
                .single() \
                .execute()
            
            return bool(user_response.data and user_response.data.get('role') == 'admin')
        except Exception as e:
            logger.error(f"Admin kontrol hatası {user_id}: {e}")
            return False