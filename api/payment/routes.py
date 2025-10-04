"""
Payment order creation endpoint
Public endpoint (no authentication required)
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import logging
import json
from datetime import datetime
from decimal import Decimal

from models.payment_schemas import OnSiparisCreate, OnSiparisResponse
from models.supabase_client import supabase_client
from services.credit_service import CreditService
from utils.response import success_response, error_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/order/create", response_model=OnSiparisResponse)
async def create_order(
    order: OnSiparisCreate,
    request: Request
):
    """
    Sipariş kaydı oluştur ve kredi ekle
    
    Bu endpoint ödeme tamamlandığında çağrılır.
    - conversation_id'den user_id çıkarılır (conv- prefix kaldırılır)
    - status == "success" VE fraud_status == "ok" ise kredi eklenir
    
    Token koruması YOK - Public endpoint
    
    Args:
        order: Sipariş bilgileri
        request: FastAPI request object (URL için)
        
    Returns:
        OnSiparisResponse: Sipariş kayıt sonucu
    """
    try:
        # Client IP ve request detaylarını yakala
        client_ip = request.client.host if request.client else "unknown"
        headers = dict(request.headers)
        request_url = str(request.url)
        
        # Gelen isteği konsolda yazdır
        logger.info("=" * 80)
        logger.info("📥 YENİ SİPARİŞ İSTEĞİ ALINDI:")
        logger.info(f"Request URL: {request_url}")
        logger.info(f"Client IP: {client_ip}")
        logger.info(f"Request Body: {json.dumps(order.model_dump(), indent=2, default=str)}")
        logger.info("=" * 80)
        
        # Sipariş verilerini hazırla
        order_data = {
            "email": order.email,
            "tarih": order.tarih.isoformat() if order.tarih else datetime.now().isoformat(),
            "user_agent": order.user_agent,
            "referrer": order.referrer,
            "user_ip": order.user_ip,
            "status": order.status,
            "conversation_id": order.conversation_id,
            "price": float(order.price),
            "payment_id": order.payment_id,
            "fraud_status": order.fraud_status,
            "commission_rate": float(order.commission_rate) if order.commission_rate else None,
            "commission_fee": float(order.commission_fee) if order.commission_fee else None,
            "host_reference": order.host_reference,
            "credit_amount": order.credit_amount,
            "system_time": order.system_time.isoformat() if order.system_time else None,
            "request_url": request_url
        }
        
        # Supabase'e kaydet
        result = supabase_client.supabase.table('on_siparis').insert(order_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Sipariş kaydedilemedi")
        
        order_record = result.data[0]
        
        logger.info(f"✅ Sipariş kaydedildi: {order_record['id']}, payment_id: {order.payment_id}")
        
        # Kredi ekleme kontrolü
        credit_added = False
        if order.status == "success" and order.fraud_status == "ok":
            logger.info(f"🎯 Kredi ekleme koşulları sağlandı (status=success, fraud_status=ok)")
            
            # User ID'yi conversation_id'den çıkar
            # Format: conv-550e8400-e29b-41d4-a716-446655440000 -> 550e8400-e29b-41d4-a716-446655440000
            conversation_id = order.conversation_id
            user_id = conversation_id[5:] if conversation_id.startswith("conv-") else conversation_id
            
            logger.info(f"📋 Parsed user_id: {user_id}")
            
            # User ID ile kullanıcıyı bul
            user_result = supabase_client.supabase.table('user_profiles') \
                .select('*') \
                .eq('id', user_id) \
                .execute()
            
            if user_result.data:
                user = user_result.data[0]
                credit_amount = order.credit_amount
                
                logger.info(f"👤 Kullanıcı bulundu: {user_id}, eklenecek kredi: {credit_amount}")
                
                # Kredi bakiyesini al
                balance_result = supabase_client.supabase.table('user_credit_balance') \
                    .select('current_balance') \
                    .eq('user_id', user_id) \
                    .execute()
                
                if balance_result.data:
                    current_balance = balance_result.data[0]['current_balance']
                    new_balance = current_balance + credit_amount
                    
                    # Bakiyeyi güncelle
                    update_result = supabase_client.supabase.table('user_credit_balance') \
                        .update({'current_balance': new_balance}) \
                        .eq('user_id', user_id) \
                        .execute()
                    
                    if update_result.data:
                        credit_added = True
                        
                        # Transaction kaydı ekle
                        transaction_data = {
                            'user_id': user_id,
                            'amount': credit_amount,
                            'transaction_type': 'purchase',
                            'description': f'İyzico ödeme - Payment ID: {order.payment_id}',
                            'balance_after': new_balance,
                            'payment_reference': order.payment_id
                        }
                        
                        supabase_client.supabase.table('credit_transactions').insert(transaction_data).execute()
                        
                        logger.info(f"✅ Kredi başarıyla eklendi: {user_id} - {credit_amount} kredi (yeni bakiye: {new_balance})")
                    else:
                        logger.error(f"❌ Kredi bakiyesi güncellenemedi: {user_id}")
                else:
                    logger.error(f"❌ Kullanıcı kredi bakiyesi bulunamadı: {user_id}")
            else:
                logger.warning(f"⚠️ User ID ile kullanıcı bulunamadı: {user_id}")
        else:
            logger.info(f"⏭️ Kredi eklenmedi - status: {order.status}, fraud_status: {order.fraud_status}")
        
        return OnSiparisResponse(
            success=True,
            message="Sipariş kaydedildi" + (" ve kredi eklendi" if credit_added else ""),
            order_id=order_record['id'],
            payment_id=order.payment_id,
            conversation_id=order.conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sipariş kayıt hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sipariş kaydedilemedi: {str(e)}")
