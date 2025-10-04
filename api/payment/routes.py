"""
Payment and iyzico webhook endpoints
Public endpoints (no authentication required)
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import logging
import json
from datetime import datetime
from decimal import Decimal

from models.payment_schemas import (
    OnSiparisCreate, OnSiparisResponse,
    IyzicoWebhook, IyzicoWebhookResponse
)
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
    İlk sipariş kaydı oluştur (on_siparis tablosu)
    
    Bu endpoint ödeme başlatıldığında çağrılır.
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
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
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
        
        logger.info(f"Ön sipariş kaydedildi: {order_record['id']}, payment_id: {order.payment_id}, email: {order.email}")
        
        return OnSiparisResponse(
            success=True,
            message="Sipariş başarıyla kaydedildi",
            order_id=order_record['id'],
            payment_id=order.payment_id,
            conversation_id=order.conversation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sipariş kayıt hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sipariş kaydedilemedi: {str(e)}")


@router.post("/iyzico/webhook", response_model=IyzicoWebhookResponse)
async def iyzico_webhook(
    webhook: IyzicoWebhook,
    request: Request
):
    """
    İyzico webhook endpoint
    
    İyzico'dan ödeme sonucu gelir:
    1. iyzico_siparis tablosuna kaydeder
    2. paymentId ile on_siparis'i eşleştirir
    3. Status=SUCCESS ise email'den kullanıcı bulup kredi ekler
    
    Token koruması YOK - Public webhook endpoint
    
    Args:
        webhook: İyzico webhook verisi
        request: FastAPI request object (URL için)
        
    Returns:
        IyzicoWebhookResponse: Webhook işlem sonucu
    """
    try:
        # Client IP ve request detaylarını yakala
        client_ip = request.client.host if request.client else "unknown"
        headers = dict(request.headers)
        request_url = str(request.url)
        
        # Gelen webhook isteğini konsolda yazdır
        logger.info("=" * 80)
        logger.info("🔔 İYZİCO WEBHOOK ALINDI:")
        logger.info(f"Request URL: {request_url}")
        logger.info(f"Client IP (İyzico): {client_ip}")
        logger.info(f"Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"Webhook Body: {json.dumps(webhook.model_dump(), indent=2, default=str)}")
        logger.info("=" * 80)
        
        logger.info(f"İyzico webhook alındı - paymentId: {webhook.paymentId}, status: {webhook.status}")
        
        # İyzico webhook verilerini kaydet
        webhook_data = {
            "payment_conversation_id": webhook.paymentConversationId,
            "merchant_id": webhook.merchantId,
            "payment_id": webhook.paymentId,
            "status": webhook.status,
            "iyzico_reference_code": webhook.iyziReferenceCode,
            "event_type": webhook.iyziEventType,
            "event_time": webhook.iyziEventTime,
            "iyzico_payment_id": webhook.iyziPaymentId,
            "request_url": request_url
        }
        
        # iyzico_siparis tablosuna kaydet
        webhook_result = supabase_client.supabase.table('iyzico_siparis').insert(webhook_data).execute()
        
        if not webhook_result.data:
            raise HTTPException(status_code=500, detail="Webhook kaydedilemedi")
        
        webhook_record = webhook_result.data[0]
        webhook_id = webhook_record['id']
        
        logger.info(f"Webhook kaydedildi: {webhook_id}")
        
        # paymentId ile on_siparis'i bul
        matched_order = False
        credit_added = False
        credit_amount = 0
        email = ""
        
        if webhook.paymentId:
            order_result = supabase_client.supabase.table('on_siparis') \
                .select('*') \
                .eq('payment_id', webhook.paymentId) \
                .execute()
            
            matched_order = bool(order_result.data)
            
            if matched_order:
                order = order_result.data[0]
                logger.info(f"Sipariş eşleşti: {order['id']}, email: {order['email']}")
                
                # Ödeme başarılı mı kontrol et
                if webhook.status == "SUCCESS":
                    logger.info(f"Ödeme başarılı - kredi ekleme başlıyor")
                    
                    # Email'i paymentConversationId'den çıkar
                    # Format: conv-email@domain.com -> email@domain.com
                    email = webhook.paymentConversationId or ""
                    if email.startswith("conv-"):
                        email = email[5:]  # "conv-" prefix'ini kaldır
                    
                    logger.info(f"Parsed email: {email}")
                    
                    # Email'den kullanıcıyı bul
                    user_result = supabase_client.supabase.table('user_profiles') \
                        .select('*') \
                        .eq('email', email) \
                        .execute()
                    
                    if user_result.data:
                        user = user_result.data[0]
                        user_id = user['id']
                        credit_amount = order['credit_amount']
                        
                        logger.info(f"Kullanıcı bulundu: {user_id}, eklenecek kredi: {credit_amount}")
                        
                        # Kullanıcıya kredi ekle
                        credit_service = CreditService()
                        
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
                                    'description': f'İyzico ödeme - Payment ID: {webhook.paymentId}',
                                    'balance_after': new_balance,
                                    'payment_reference': webhook.paymentId
                                }
                                
                                supabase_client.supabase.table('credit_transactions').insert(transaction_data).execute()
                                
                                logger.info(f"✅ Kredi başarıyla eklendi: {user_id} - {credit_amount} kredi")
                            else:
                                logger.error(f"Kredi bakiyesi güncellenemedi: {user_id}")
                        else:
                            logger.error(f"Kullanıcı kredi bakiyesi bulunamadı: {user_id}")
                    else:
                        logger.warning(f"Email ile kullanıcı bulunamadı: {email}")
                else:
                    logger.info(f"Ödeme başarısız - status: {webhook.status}")
        else:
            logger.warning(f"payment_id ile sipariş bulunamadı: {webhook.paymentId}")
        
        return IyzicoWebhookResponse(
            success=True,
            message="Webhook başarıyla işlendi",
            webhook_id=webhook_id,
            matched_order=matched_order,
            credit_added=credit_added,
            credit_amount=credit_amount if credit_added else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook işlem hatası: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook işlenemedi: {str(e)}")
