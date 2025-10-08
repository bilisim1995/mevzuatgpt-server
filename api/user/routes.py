"""
User routes for document search and retrieval
Accessible by authenticated users with appropriate permissions
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status, File, UploadFile, Form
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from core.database import get_db
from api.dependencies import get_current_user, get_optional_user
from models.supabase_client import supabase_client
from models.schemas import (
    UserResponse, SearchRequest, SearchResponse, 
    DocumentResponse, DocumentListResponse,
    AskRequest, AskResponse, SuggestionsResponse,
    CompareRequest, CompareResponse, ComparisonResult
)
from models.search_history_schemas import SearchHistoryResponse, SearchHistoryFilters
from models.payment_schemas import PurchaseHistoryResponse, PurchaseHistoryItem, PaymentSettingsResponse
from services.search_service import SearchService
from services.document_service import DocumentService
from services.query_service import QueryService
from services.credit_service import credit_service
from services.search_history_service import SearchHistoryService
from services.document_compare_service import DocumentCompareService
from services.file_ocr_service import FileOCRService
from utils.response import success_response
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    search_request: SearchRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Semantic search in document embeddings
    
    This endpoint performs vector similarity search using OpenAI embeddings
    to find relevant document chunks based on the user's query.
    
    Args:
        search_request: Search parameters including query and filters
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Search results with relevant document chunks and similarity scores
    """
    try:
        search_service = SearchService(db)
        
        # Perform semantic search
        results = await search_service.semantic_search(
            query=search_request.query,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold,
            category_filter=search_request.category,
            date_filter=search_request.date_range
        )
        
        logger.info(f"Search performed by user {current_user.id}: '{search_request.query}' - {len(results)} results")
        
        return success_response(
            data={
                "query": search_request.query,
                "results": results,
                "total_results": len(results)
            }
        )
        
    except Exception as e:
        logger.error(f"Search error for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Search operation failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SEARCH_FAILED"
        )

@router.get("/documents", response_model=DocumentListResponse)
async def get_published_documents(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    keyword: Optional[str] = Query(None, description="Search in titles and descriptions"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of published documents (User access)
    
    Returns only successfully processed documents that are available for search.
    Provides pagination and basic filtering capabilities.
    
    Args:
        page: Page number (starts from 1)
        limit: Number of documents per page (max 100)
        category: Filter by document category
        keyword: Search in document titles and descriptions
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Paginated list of published documents
    """
    try:
        document_service = DocumentService(db)
        
        documents, total_count = await document_service.list_published_documents(
            page=page,
            limit=limit,
            category=category,
            keyword=keyword
        )
        
        return success_response(
            data={
                "documents": documents,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing documents for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Failed to retrieve documents",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="LIST_FAILED"
        )

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_details(
    document_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get document details by ID (User access)
    
    Returns detailed information about a specific document if it's published
    and available for access.
    
    Args:
        document_id: Document UUID
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Document details
    """
    try:
        document_service = DocumentService(db)
        document = await document_service.get_published_document_by_id(document_id)
        
        if not document:
            raise AppException(
                message="Document not found or not available",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="DOCUMENT_NOT_FOUND"
            )
        
        return success_response(data=document)
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id} for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Failed to retrieve document",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="GET_FAILED"
        )

@router.get("/categories")
async def get_document_categories(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of available document categories
    
    Returns all categories that have published documents.
    Useful for filtering and navigation in client applications.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of available categories
    """
    try:
        document_service = DocumentService(db)
        categories = await document_service.get_available_categories()
        
        return success_response(
            data={
                "categories": categories,
                "total_categories": len(categories)
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving categories for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Failed to retrieve categories",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CATEGORIES_FAILED"
        )

@router.post("/ask", response_model=AskResponse)
async def ask_question(
    ask_request: AskRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question and get AI-powered answer with sources
    
    This endpoint performs the complete RAG pipeline:
    1. Check user credit balance and calculate required credits
    2. Generate embeddings for the query (with caching)
    3. Search for relevant document chunks
    4. Generate AI response using Groq
    5. Return answer with sources and confidence score
    
    Features:
    - Credit system integration with automatic deduction
    - Redis caching for performance
    - Rate limiting protection (30 requests/minute)
    - Institution filtering
    - Confidence scoring
    - User search history tracking
    - Admin users have unlimited credits
    
    Args:
        ask_request: Question and search parameters
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        AI-generated answer with sources and metadata
    """
    try:
        user_id = str(current_user.id)
        query = ask_request.query
        
        # 1. Intent classification for all users (needed for routing)
        query_service_temp = QueryService(db)
        query_intent = query_service_temp.classify_query_intent(query)
        
        # 2. Admin kullanıcılar için kredi kontrolü bypass
        is_admin = await credit_service.is_admin_user(user_id)
        required_credits = 0  # Default değer
        
        if not is_admin:
            # 3. Sorgu için gerekli kredi miktarını hesapla (Intent-based)
            required_credits = query_service_temp.calculate_intent_based_credits(query)
            
            # 3. Kullanıcının yeterli kredisi var mı kontrol et
            current_balance = await credit_service.get_user_balance(user_id)
            
            if current_balance < required_credits:
                # Yetersiz kredi durumu
                logger.warning(f"Insufficient credits for user {user_id}: required={required_credits}, balance={current_balance}")
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail={
                        "error": "insufficient_credits",
                        "message": "Krediniz bu sorgu için yeterli değil",
                        "required_credits": required_credits,
                        "current_balance": current_balance,
                        "query": query[:100] + "..." if len(query) > 100 else query
                    }
                )
            
            # 4. Krediyi düş (işlem başlamadan önce)
            deduction_success = await credit_service.deduct_credits(
                user_id=user_id,
                amount=required_credits,
                description=f"Sorgu: '{query[:50]}{'...' if len(query) > 50 else ''}'",
                query_id=None  # Query ID henüz yok, sonra güncellenecek
            )
            
            if not deduction_success:
                logger.error(f"Credit deduction failed for user {user_id}")
                raise HTTPException(
                    status_code=500,
                    detail="Kredi düşüm işlemi başarısız oldu"
                )
            
            logger.info(f"Credits deducted for user {user_id}: {required_credits} credits, balance: {current_balance - required_credits}")
        
        # 5. Normal ask query processing
        query_service = QueryService(db)
        
        result = await query_service.process_ask_query(
            query=ask_request.query,
            user_id=user_id,
            institution_filter=ask_request.institution_filter,
            limit=ask_request.limit,
            similarity_threshold=ask_request.similarity_threshold,
            use_cache=ask_request.use_cache,
            intent=query_intent
        )
        
        # 6. AI cevabını kontrol et - bilgi bulunamadıysa kredi iade et
        ai_answer = result.get("answer", "")
        no_info_phrases = [
            "Verilen belge içeriğinde bu konuda bilgi bulunmamaktadır",
            "belge içeriğinde bu konuda bilgi bulunmamaktadır",
            "bilgi bulunmamaktadır"
        ]
        
        # Bilgi bulunamadığını gösteren ifadeler varsa kredi iade et
        is_no_info_response = any(phrase in ai_answer for phrase in no_info_phrases)
        
        # Debug log
        if is_no_info_response:
            logger.info(f"No info response detected for query '{ask_request.query}' - AI answer: '{ai_answer[:100]}...'")
        else:
            logger.debug(f"Info found for query '{ask_request.query}' - AI answer: '{ai_answer[:100]}...'")
        refund_applied = False
        
        if not is_admin and is_no_info_response and required_credits > 0:
            # Kredi iadesi yap
            search_log_id = result.get("search_log_id")
            refund_success = await credit_service.refund_credits(
                user_id=user_id,
                amount=required_credits,
                query_id=search_log_id if search_log_id else "no_info",
                reason=f"Bilgi bulunamadı: '{ask_request.query[:50]}{'...' if len(ask_request.query) > 50 else ''}'"
            )
            
            if refund_success:
                refund_applied = True
                logger.info(f"Credit refunded for user {user_id}: {required_credits} credits (no info found)")
            else:
                logger.error(f"Credit refund failed for user {user_id}")
        
        # Check for low confidence and refund credits if needed (NEW)
        confidence_score = result.get("confidence_score", 1.0)
        confidence_threshold = 0.4
        is_low_confidence = confidence_score < confidence_threshold
        
        if not is_admin and is_low_confidence and required_credits > 0 and not refund_applied:
            # Kredi iadesi yap - düşük güvenilirlik
            search_log_id = result.get("search_log_id")
            refund_success = await credit_service.refund_credits(
                user_id=user_id,
                amount=required_credits,
                query_id=search_log_id if search_log_id else "low_confidence",
                reason=f"Düşük güvenilirlik (%{int(confidence_score * 100)}): '{ask_request.query[:50]}{'...' if len(ask_request.query) > 50 else ''}'"
            )
            
            if refund_success:
                refund_applied = True
                logger.info(f"Credit refunded for user {user_id}: {required_credits} credits (low confidence: {confidence_score:.2f})")
            else:
                logger.error(f"Credit refund failed for user {user_id} (low confidence)")
        
        # 7. Kredi bilgilerini response'a ekle
        if not is_admin:
            # current_balance variables'ını güvenli şekilde kullan
            balance = locals().get('current_balance', 0)
            final_balance = balance if refund_applied else balance - required_credits
            credits_used = 0 if refund_applied else required_credits
            
            # Determine refund reason
            refund_reason = None
            if refund_applied:
                if is_no_info_response:
                    refund_reason = "Bilgi bulunamadı"
                elif is_low_confidence:
                    refund_reason = f"Düşük güvenilirlik (%{int(confidence_score * 100)})"
            
            result["credit_info"] = {
                "credits_used": credits_used,
                "remaining_balance": final_balance,
                "refund_applied": refund_applied,
                "refund_reason": refund_reason,
                "confidence_score": confidence_score,
                "no_info_detected": is_no_info_response,  # Debug bilgisi
                "low_confidence_detected": is_low_confidence  # Debug bilgisi
            }
        else:
            result["credit_info"] = {
                "credits_used": 0,
                "remaining_balance": "unlimited",
                "admin_user": True,
                "refund_would_apply": is_no_info_response,  # Admin olsaydı kredi iade edilir miydi
                "no_info_detected": is_no_info_response  # Debug bilgisi
            }
        
        logger.info(f"Ask query processed for user {user_id}: '{ask_request.query[:50]}' - confidence: {result['confidence_score']}")
        
        return success_response(data=result)
        
    except HTTPException:
        # HTTPException'ları aynen geçir (kredi yetersizliği gibi)
        raise
    except AppException as e:
        # İşlem hata aldıysa krediyi iade et (admin değilse ve kredi düşüldüyse)
        is_admin_local = locals().get('is_admin', True)  # Default True for safety
        required_credits_local = locals().get('required_credits', 0)
        user_id_local = locals().get('user_id', str(current_user.id))
        
        if not is_admin_local and required_credits_local > 0:
            try:
                await credit_service.refund_credits(
                    user_id=user_id_local,
                    amount=required_credits_local,
                    query_id="failed",
                    reason=f"İşlem hatası: {str(e)}"
                )
                logger.info(f"Credits refunded due to error for user {user_id_local}: {required_credits_local} credits")
            except Exception as refund_error:
                logger.error(f"Credit refund failed for user {user_id_local}: {refund_error}")
        
        if e.status_code == 429:  # Rate limit exceeded
            raise HTTPException(
                status_code=429,
                detail={
                    "message": e.message,
                    "detail": e.detail,
                    "retry_after": 60
                }
            )
        raise e
    except Exception as e:
        # Diğer hatalar için de kredi iadesi (admin değilse ve kredi düşüldüyse)
        is_admin_local = locals().get('is_admin', True)  # Default True for safety
        required_credits_local = locals().get('required_credits', 0)
        user_id_local = locals().get('user_id', str(current_user.id))
        
        if not is_admin_local and required_credits_local > 0:
            try:
                await credit_service.refund_credits(
                    user_id=user_id_local,
                    amount=required_credits_local,
                    query_id="failed",
                    reason=f"Sistem hatası: {str(e)}"
                )
                logger.info(f"Credits refunded due to system error for user {user_id_local}: {required_credits_local} credits")
            except Exception as refund_error:
                logger.error(f"Credit refund failed for user {user_id_local}: {refund_error}")
        
        # Use safe user_id reference  
        user_id_for_log = locals().get('user_id', str(current_user.id))
        logger.error(f"Ask error for user {user_id_for_log}: {str(e)}")
        raise AppException(
            message="Failed to process question",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ASK_FAILED"
        )

@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_user_suggestions(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized suggestions for user
    
    Returns user's recent searches, popular searches, available institutions,
    and suggested queries based on search history and trends.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Personalized suggestions and search options
    """
    try:
        query_service = QueryService(db)
        
        suggestions = await query_service.get_user_suggestions(str(current_user.id))
        
        return success_response(data=suggestions)
        
    except Exception as e:
        logger.warning(f"Failed to get suggestions for user {current_user.id}: {str(e)}")
        # Return empty suggestions on error
        return success_response(data={
            "recent_searches": [],
            "popular_searches": [],
            "available_institutions": [],
            "suggestions": []
        })


@router.get("/search-history", response_model=SearchHistoryResponse)
async def get_search_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    institution: Optional[str] = Query(None, description="Filter by institution"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    min_reliability: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum reliability score"),
    search_query: Optional[str] = Query(None, description="Search within queries"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's search history with pagination and filtering
    
    Returns paginated list of user's previous searches with:
    - Original query
    - AI response
    - Source documents
    - Reliability scores
    - Credits used
    - Search date and time
    
    Args:
        page: Page number (1-based)
        limit: Items per page (max 100)
        institution: Filter by institution name
        date_from: Filter searches from this date
        date_to: Filter searches until this date
        min_reliability: Minimum reliability score filter
        search_query: Search within user's queries
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Paginated search history with statistics
    """
    try:
        search_history_service = SearchHistoryService(db)
        
        # Build filters
        filters = None
        if any([institution, date_from, date_to, min_reliability, search_query]):
            filters = SearchHistoryFilters(
                institution=institution,
                date_from=date_from,
                date_to=date_to,
                min_reliability=min_reliability,
                search_query=search_query
            )
        
        # Get search history
        history = await search_history_service.get_user_search_history(
            user_id=str(current_user.id),
            page=page,
            limit=limit,
            filters=filters
        )
        
        logger.info(f"Search history retrieved for user {current_user.id}: {len(history.items)} items")
        
        return success_response(data=history.model_dump(mode='json'))
        
    except Exception as e:
        logger.error(f"Error retrieving search history for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Search history retrieval failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/search-history/stats")
async def get_search_statistics(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's search statistics
    
    Returns summary statistics about user's search activity:
    - Total number of searches
    - Total credits used
    - Average reliability score
    - Most used institution
    - Search counts for today and this month
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Search statistics summary
    """
    try:
        search_history_service = SearchHistoryService(db)
        
        stats = await search_history_service.get_search_statistics(str(current_user.id))
        
        logger.info(f"Search statistics retrieved for user {current_user.id}")
        
        return success_response(data=stats)
        
    except Exception as e:
        logger.error(f"Error retrieving search statistics for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Search statistics retrieval failed", 
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@router.get("/recent-documents")
async def get_recent_documents(
    limit: int = Query(10, ge=1, le=50, description="Number of recent documents"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recently added documents
    
    Returns the most recently published documents, useful for
    showing updates and new content to users.
    
    Args:
        limit: Number of recent documents to return
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of recently added documents
    """
    try:
        document_service = DocumentService(db)
        documents = await document_service.get_recent_documents(limit)
        
        return success_response(
            data={
                "documents": documents,
                "total_documents": len(documents)
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving recent documents for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Failed to retrieve recent documents",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="RECENT_FAILED"
        )


@router.get("/purchases", response_model=PurchaseHistoryResponse)
async def get_user_purchases(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Kullanıcının kendi satın alım geçmişini görüntüle
    
    Kullanıcı token'ından UUID alınır ve on_siparis tablosunda
    conversation_id'si conv-{UUID} formatında olan kayıtlar listelenir.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Kullanıcının satın alım geçmişi
    """
    try:
        user_id = str(current_user.id)
        
        # conversation_id formatı: conv-{UUID}
        conversation_id_filter = f"conv-{user_id}"
        
        # Supabase'den satın alımları çek
        response = supabase_client.supabase.table('on_siparis').select(
            'created_at, status, price, payment_id, credit_amount'
        ).eq('conversation_id', conversation_id_filter).order('created_at', desc=True).execute()
        
        purchases = []
        if response.data:
            for item in response.data:
                purchases.append(PurchaseHistoryItem(
                    created_at=item['created_at'],
                    status=item['status'],
                    price=item['price'],
                    payment_id=item.get('payment_id'),
                    credit_amount=item['credit_amount']
                ))
        
        logger.info(f"Purchase history retrieved for user {user_id}: {len(purchases)} items")
        
        return PurchaseHistoryResponse(
            success=True,
            data=purchases,
            total=len(purchases)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving purchases for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Satın alım geçmişi alınamadı",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PURCHASE_HISTORY_FAILED"
        )


@router.get("/payment-settings", response_model=PaymentSettingsResponse)
async def get_payment_settings(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Ödeme ayarlarını görüntüle (User Token Gerekli)
    
    İyzico ödeme modunu (sandbox/production) ve ödeme sisteminin
    aktif/pasif durumunu döndürür.
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Ödeme modu ve aktiflik durumu
    """
    try:
        # Supabase'den payment_settings tablosunu çek
        response = supabase_client.supabase.table('payment_settings').select('payment_mode, is_active, description').limit(1).execute()
        
        if not response.data or len(response.data) == 0:
            # Varsayılan değerler
            logger.warning("Payment settings not found in database, using defaults")
            return PaymentSettingsResponse(
                success=True,
                payment_mode="sandbox",
                is_active=False,
                description="Ödeme ayarları bulunamadı"
            )
        
        settings = response.data[0]
        
        logger.info(f"Payment settings retrieved for user {current_user.id}: mode={settings['payment_mode']}, active={settings['is_active']}")
        
        return PaymentSettingsResponse(
            success=True,
            payment_mode=settings['payment_mode'],
            is_active=settings['is_active'],
            description=settings.get('description')
        )
        
    except Exception as e:
        logger.error(f"Error retrieving payment settings for user {current_user.id}: {str(e)}")
        raise AppException(
            message="Ödeme ayarları alınamadı",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PAYMENT_SETTINGS_FAILED"
        )

@router.post("/compare-documents", response_model=CompareResponse)
async def compare_documents(
    compare_request: CompareRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    İki mevzuat belgesini karşılaştır ve farklılıkları AI ile analiz et
    
    Bu endpoint iki mevzuat metnini alır ve aralarındaki farklılıkları
    AI kullanarak analiz eder. 3 farklı detay seviyesinde analiz yapılabilir:
    
    - **yuzeysel**: Sadece ana değişiklikleri listeler (5-10 madde)
    - **normal**: Tüm önemli değişiklikleri açıklar (varsayılan)
    - **detayli**: Her değişikliği derinlemesine inceler (madde madde)
    
    Sonuçlar Markdown formatında döndürülür ve frontend'de formatlı
    bir şekilde gösterilebilir.
    
    Features:
    - 3 seviyeli analiz (yüzeysel, normal, detaylı)
    - Markdown formatında çıktı
    - Eklenen, çıkarılan, değiştirilen maddeleri tespit eder
    - Hukuki etki analizi yapar
    - Groq (hızlı) ve OpenAI (yedek) AI provider desteği
    
    Args:
        compare_request: Karşılaştırma parametreleri
        current_user: Kimliği doğrulanmış kullanıcı
    
    Returns:
        Markdown formatında karşılaştırma sonuçları
    """
    try:
        user_id = str(current_user.id)
        logger.info(f"Document comparison requested by user {user_id} - Analysis level: {compare_request.analysis_level}")
        
        # Servis başlat
        compare_service = DocumentCompareService()
        
        # Belgeleri karşılaştır
        result = await compare_service.compare_documents(
            old_content=compare_request.old_document_content,
            new_content=compare_request.new_document_content,
            analysis_level=compare_request.analysis_level,
            old_title=compare_request.old_document_title,
            new_title=compare_request.new_document_title
        )
        
        # Değişiklik sayısını hesapla
        changes_count = compare_service.count_changes(result["comparison_markdown"])
        
        # Özet çıkar
        summary = compare_service.generate_summary(
            result["comparison_markdown"],
            compare_request.analysis_level
        )
        
        # Response oluştur
        comparison_result = ComparisonResult(
            analysis_level=compare_request.analysis_level,
            comparison_markdown=result["comparison_markdown"],
            summary=summary,
            changes_count=changes_count,
            generation_time_ms=result["generation_time_ms"]
        )
        
        logger.info(
            f"Document comparison completed for user {user_id} - "
            f"Changes: {changes_count}, Time: {result['generation_time_ms']}ms, "
            f"Provider: {result.get('provider', 'unknown')}"
        )
        
        return CompareResponse(
            success=True,
            result=comparison_result,
            old_document_info={
                "title": compare_request.old_document_title or "Eski Mevzuat",
                "content_length": len(compare_request.old_document_content)
            },
            new_document_info={
                "title": compare_request.new_document_title or "Yeni Mevzuat",
                "content_length": len(compare_request.new_document_content)
            },
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Document comparison failed for user {user_id}: {str(e)}")
        raise AppException(
            message="Belge karşılaştırma işlemi başarısız oldu",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="COMPARE_FAILED"
        )

@router.post("/compare-documents-upload", response_model=CompareResponse)
async def compare_documents_upload(
    old_file: UploadFile = File(..., description="Eski mevzuat dosyası"),
    new_file: UploadFile = File(..., description="Yeni mevzuat dosyası"),
    analysis_level: str = Form(default="normal", description="yuzeysel, normal, detayli"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Dosya yükleyerek mevzuat karşılaştırma (OCR + NLP Destekli)
    
    Bu endpoint iki dosyayı alır, içeriklerini okur (OCR ile) ve AI ile karşılaştırır.
    
    Desteklenen Formatlar:
    - **PDF**: PDF belgeler (.pdf)
    - **Word**: Word belgeleri (.docx, .doc)
    - **Resim**: OCR ile metin çıkarma (.jpg, .png, .jpeg, .bmp, .tiff, .webp)
    - **Text**: Düz metin dosyaları (.txt, .md)
    
    OCR Özellikleri:
    - **OpenAI Vision API**: Gelişmiş OCR (resimler için)
    - **NLP Destekli**: Metin temizleme ve normalizasyon
    - **Türkçe Karakter Desteği**: Tam Türkçe dil desteği
    
    Analiz Seviyeleri:
    - **yuzeysel**: Hızlı özet (5-10 madde)
    - **normal**: Standart analiz (varsayılan)
    - **detayli**: Kapsamlı inceleme
    
    Args:
        old_file: Eski mevzuat dosyası (max 10MB)
        new_file: Yeni mevzuat dosyası (max 10MB)
        analysis_level: Analiz detay seviyesi
        current_user: Kimliği doğrulanmış kullanıcı
    
    Returns:
        Markdown formatında karşılaştırma sonuçları
    """
    try:
        user_id = str(current_user.id)
        logger.info(
            f"File comparison requested by user {user_id} - "
            f"Old: {old_file.filename}, New: {new_file.filename}, Level: {analysis_level}"
        )
        
        # Analiz seviyesi validasyonu - normalize et
        analysis_level = analysis_level.strip().lower()
        if analysis_level not in ['yuzeysel', 'normal', 'detayli']:
            raise HTTPException(
                status_code=400,
                detail=f"analysis_level '{analysis_level}' geçersiz. 'yuzeysel', 'normal' veya 'detayli' olmalıdır"
            )
        
        # Dosya boyutu kontrolü
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
        
        old_content = await old_file.read()
        new_content = await new_file.read()
        
        if len(old_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Eski dosya çok büyük ({len(old_content)/(1024*1024):.1f} MB). Maksimum 10 MB."
            )
        
        if len(new_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Yeni dosya çok büyük ({len(new_content)/(1024*1024):.1f} MB). Maksimum 10 MB."
            )
        
        # OCR servisi başlat
        ocr_service = FileOCRService()
        
        # Eski dosyadan metin çıkar
        logger.info(f"Extracting text from old file: {old_file.filename}")
        old_extraction = await ocr_service.extract_text_from_file(
            file_content=old_content,
            filename=old_file.filename,
            use_nlp=True
        )
        
        # Yeni dosyadan metin çıkar
        logger.info(f"Extracting text from new file: {new_file.filename}")
        new_extraction = await ocr_service.extract_text_from_file(
            file_content=new_content,
            filename=new_file.filename,
            use_nlp=True
        )
        
        logger.info(
            f"Text extraction completed - "
            f"Old: {old_extraction['method']} (confidence: {old_extraction['confidence']}), "
            f"New: {new_extraction['method']} (confidence: {new_extraction['confidence']})"
        )
        
        # Karşılaştırma servisi başlat
        compare_service = DocumentCompareService()
        
        # Belgeleri karşılaştır
        result = await compare_service.compare_documents(
            old_content=old_extraction['text'],
            new_content=new_extraction['text'],
            analysis_level=analysis_level,
            old_title=old_file.filename,
            new_title=new_file.filename
        )
        
        # Değişiklik sayısını hesapla
        changes_count = compare_service.count_changes(result["comparison_markdown"])
        
        # Özet çıkar
        summary = compare_service.generate_summary(
            result["comparison_markdown"],
            analysis_level
        )
        
        # Response oluştur
        comparison_result = ComparisonResult(
            analysis_level=analysis_level,
            comparison_markdown=result["comparison_markdown"],
            summary=summary,
            changes_count=changes_count,
            generation_time_ms=result["generation_time_ms"]
        )
        
        logger.info(
            f"File comparison completed for user {user_id} - "
            f"Changes: {changes_count}, Time: {result['generation_time_ms']}ms, "
            f"Provider: {result.get('provider', 'unknown')}"
        )
        
        return CompareResponse(
            success=True,
            result=comparison_result,
            old_document_info={
                "title": old_file.filename,
                "content_length": len(old_extraction['text']),
                "format": old_extraction['format'],
                "extraction_method": old_extraction['method'],
                "confidence": old_extraction['confidence']
            },
            new_document_info={
                "title": new_file.filename,
                "content_length": len(new_extraction['text']),
                "format": new_extraction['format'],
                "extraction_method": new_extraction['method'],
                "confidence": new_extraction['confidence']
            },
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File comparison failed for user {user_id}: {str(e)}")
        raise AppException(
            message="Dosya karşılaştırma işlemi başarısız oldu",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="FILE_COMPARE_FAILED"
        )
