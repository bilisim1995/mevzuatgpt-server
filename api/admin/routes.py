"""
Admin routes for document management and system administration
Only accessible by users with 'admin' role
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import logging
import asyncio
import json
import uuid
from datetime import datetime

from core.database import get_db
from api.dependencies import get_admin_user
from models.schemas import (
    UserResponse, DocumentResponse, DocumentCreate, 
    DocumentUpdate, DocumentListResponse, UploadResponse,
    AdminUserUpdate, AdminUserResponse, AdminUserListResponse,
    UserCreditUpdate, UserBanRequest
)
from models.payment_schemas import PaymentSettingsResponse, PaymentSettingsUpdate
from models.supabase_client import supabase_client
from services.storage_service import StorageService
from services.redis_service import RedisService
from tasks.document_processor import process_document_task
from tasks.yargitay_document_processor import process_yargitay_document_task
from services.yargitay_mongo_service import yargitay_mongo_service
from utils.response import success_response, error_response
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    belge_adi: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    source_institution: Optional[str] = Form(None),
    publish_date: Optional[str] = Form(None),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Upload a PDF document (Admin only)
    
    This endpoint handles:
    1. File validation and upload to Bunny.net
    2. Metadata storage in database
    3. Triggering background processing for embeddings
    
    Args:
        file: PDF file to upload
        title: Document title
        belge_adi: Document name/identifier
        category: Document category
        description: Document description
        keywords: Comma-separated keywords
        source_institution: Source institution
        publish_date: Publication date (YYYY-MM-DD)
        current_user: Current admin user
        db: Database session
    
    Returns:
        Upload response with document ID and processing status
    """
    try:
        # Debug logging
        logger.info(f"Upload request received - file: {file.filename if file else 'None'}, title: {title}")
        logger.info(f"File content type: {file.content_type if file else 'None'}")
        
        # Validate file type and size
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise AppException(
                message="Only PDF files are allowed",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_FILE_TYPE"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Initialize services
        storage_service = StorageService()
        
        # Upload file to Bunny.net
        filename = file.filename or "untitled.pdf"
        logger.info(f"Uploading file {filename} to storage")
        file_url = await storage_service.upload_file(
            file_content=file_content,
            filename=filename,
            content_type="application/pdf"
        )
        
        # Prepare document data for Supabase
        keywords_list = [k.strip() for k in keywords.split(",")] if keywords else []
        
        document_data = {
            'title': title,
            'belge_adi': belge_adi,
            'filename': filename,
            'file_url': file_url,
            'file_size': len(file_content),
            'content_preview': f"{title} - {description or ''}"[:500],
            'uploaded_by': str(current_user.id),
            'status': 'processing',
            'institution': source_institution or 'Belirtilmemiş',
            'metadata': {
                'belge_adi': belge_adi,
                'category': category,
                'description': description,
                'keywords': keywords_list,
                'source_institution': source_institution,
                'publish_date': publish_date,
                'original_filename': filename
            }
        }
        
        # Save document metadata to Supabase
        logger.info(f"Saving document metadata for {file.filename}")
        document_id = await supabase_client.create_document(document_data)
        
        # Trigger background processing
        logger.info(f"Triggering background processing for document {document_id}")
        try:
            task = process_document_task.delay(str(document_id))
            task_id = task.id
        except Exception as task_error:
            logger.error(f"Celery task creation failed: {task_error}")
            task_id = None
        
        # Initialize progress tracking immediately 
        from services.progress_service import progress_service
        await progress_service.initialize_task_progress(
            task_id=task_id,
            document_id=str(document_id),
            document_title=title,
            total_steps=5
        )
        logger.info(f"Progress tracking initialized for task {task_id}")
        
        return success_response(
            data={
                "document_id": str(document_id),
                "task_id": task_id,  # Progress tracking için gerekli
                "message": "Document uploaded successfully and queued for processing",
                "file_url": file_url,
                "processing_status": "pending"
            }
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {str(e)}")
        # If database insert succeeded but task failed, we should handle cleanup
        raise AppException(
            message="Failed to upload document",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="UPLOAD_FAILED"
        )

@router.get("/elasticsearch/health", response_model=Dict[str, Any])
async def elasticsearch_health(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Check Elasticsearch cluster health (Admin only)"""
    try:
        from services.elasticsearch_service import ElasticsearchService
        
        async with ElasticsearchService() as elasticsearch_service:
            health_data = await elasticsearch_service.health_check()
        
        return {
            "success": True,
            "data": health_data
        }
        
    except Exception as e:
        logger.error(f"Elasticsearch health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check Elasticsearch health: {str(e)}"
        )

@router.get("/institutions", response_model=Dict[str, Any])
async def get_institutions(
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Get list of unique institution names from documents (Admin only)
    
    Returns:
        List of unique institution names from mevzuat_documents table
    """
    try:
        logger.info(f"Admin {current_user.id} requesting institution list")
        
        # Query distinct institutions from Supabase
        response = supabase_client.supabase.table('mevzuat_documents')\
            .select('institution')\
            .execute()
        
        # Extract unique institutions and filter out None/empty values
        institutions = set()
        if response.data:
            for doc in response.data:
                institution = doc.get('institution')
                if institution and institution.strip():
                    institutions.add(institution.strip())
        
        # Sort institutions alphabetically
        institutions_list = sorted(list(institutions))
        
        logger.info(f"Found {len(institutions_list)} unique institutions")
        
        return success_response(
            data={
                "institutions": institutions_list,
                "total_count": len(institutions_list)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to fetch institutions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch institutions: {str(e)}"
        )

# ===============================
# ANNOUNCEMENTS CRUD ENDPOINTS
# ===============================

@router.post("/announcements", response_model=Dict[str, Any])
async def create_announcement(
    title: str = Form(...),
    content: str = Form(...),
    priority: str = Form(default="normal"),
    publish_date: Optional[str] = Form(None),
    is_active: bool = Form(default=True),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Yeni duyuru oluştur (Admin only)
    
    Args:
        title: Duyuru başlığı
        content: Duyuru içeriği  
        priority: Önem durumu (low, normal, high, urgent)
        publish_date: Yayın tarihi (ISO format)
        is_active: Aktif durumu
    """
    try:
        from datetime import datetime
        
        logger.info(f"Creating announcement by admin {current_user.id}: {title}")
        
        # Validate priority
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if priority not in valid_priorities:
            raise HTTPException(
                status_code=400,
                detail=f"Priority must be one of: {', '.join(valid_priorities)}"
            )
        
        # Parse publish_date if provided
        parsed_publish_date = None
        if publish_date:
            try:
                parsed_publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00')).isoformat()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid publish_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
                )
        
        # Create announcement data
        announcement_data = {
            'title': title,
            'content': content,
            'priority': priority,
            'publish_date': parsed_publish_date or datetime.utcnow().isoformat(),
            'is_active': is_active,
            'created_by': str(current_user.id)
        }
        
        # Insert into database
        response = supabase_client.supabase.table('announcements').insert(announcement_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create announcement")
        
        created_announcement = response.data[0]
        
        return {
            "success": True,
            "data": {
                "id": created_announcement['id'],
                "title": created_announcement['title'],
                "content": created_announcement['content'],
                "priority": created_announcement['priority'],
                "publish_date": created_announcement['publish_date'],
                "is_active": created_announcement['is_active'],
                "created_by": created_announcement['created_by'],
                "created_at": created_announcement['created_at']
            },
            "message": "Announcement created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create announcement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create announcement: {str(e)}")

@router.get("/announcements", response_model=Dict[str, Any])
async def list_announcements(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    priority: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Duyuruları listele (Admin only)
    
    Args:
        page: Sayfa numarası
        limit: Sayfa başına öğe sayısı
        priority: Öncelik filtresi
        is_active: Aktiflik durumu filtresi
    """
    try:
        logger.info(f"Admin {current_user.id} listing announcements - page: {page}, limit: {limit}")
        
        offset = (page - 1) * limit
        
        # Build query
        query = supabase_client.supabase.table('announcements').select('*')
        
        # Apply filters
        if priority:
            query = query.eq('priority', priority)
        if is_active is not None:
            query = query.eq('is_active', is_active)
            
        # Get total count
        count_query = supabase_client.supabase.table('announcements').select('id')
        if priority:
            count_query = count_query.eq('priority', priority)
        if is_active is not None:
            count_query = count_query.eq('is_active', is_active)
            
        count_result = count_query.execute()
        total_count = len(count_result.data) if count_result.data else 0
        
        # Get paginated results
        announcements_result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        announcements = []
        if announcements_result.data:
            for announcement in announcements_result.data:
                announcements.append({
                    "id": announcement['id'],
                    "title": announcement['title'],
                    "content": announcement['content'],
                    "priority": announcement['priority'],
                    "publish_date": announcement['publish_date'],
                    "is_active": announcement['is_active'],
                    "created_by": announcement['created_by'],
                    "created_at": announcement['created_at'],
                    "updated_at": announcement.get('updated_at')
                })
        
        return {
            "success": True,
            "data": {
                "announcements": announcements,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit,
                    "has_next": offset + limit < total_count,
                    "has_previous": page > 1
                },
                "filters": {
                    "priority": priority,
                    "is_active": is_active
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list announcements: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list announcements: {str(e)}")

@router.get("/announcements/{announcement_id}", response_model=Dict[str, Any])
async def get_announcement(
    announcement_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Belirli bir duyuru detayını getir (Admin only)
    """
    try:
        logger.info(f"Admin {current_user.id} getting announcement: {announcement_id}")
        
        response = supabase_client.supabase.table('announcements').select('*').eq('id', announcement_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        announcement = response.data[0]
        
        return {
            "success": True,
            "data": {
                "id": announcement['id'],
                "title": announcement['title'],
                "content": announcement['content'],
                "priority": announcement['priority'],
                "publish_date": announcement['publish_date'],
                "is_active": announcement['is_active'],
                "created_by": announcement['created_by'],
                "created_at": announcement['created_at'],
                "updated_at": announcement.get('updated_at')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get announcement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get announcement: {str(e)}")

@router.put("/announcements/{announcement_id}", response_model=Dict[str, Any])
async def update_announcement(
    announcement_id: str,
    title: str = Form(...),
    content: str = Form(...),
    priority: str = Form(default="normal"),
    publish_date: Optional[str] = Form(None),
    is_active: bool = Form(default=True),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Duyuru güncelle (Admin only)
    """
    try:
        from datetime import datetime
        
        logger.info(f"Admin {current_user.id} updating announcement: {announcement_id}")
        
        # Check if announcement exists
        existing = supabase_client.supabase.table('announcements').select('id').eq('id', announcement_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        # Validate priority
        valid_priorities = ['low', 'normal', 'high', 'urgent']
        if priority not in valid_priorities:
            raise HTTPException(
                status_code=400,
                detail=f"Priority must be one of: {', '.join(valid_priorities)}"
            )
        
        # Parse publish_date if provided
        parsed_publish_date = None
        if publish_date:
            try:
                parsed_publish_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00')).isoformat()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid publish_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"
                )
        
        # Update data
        update_data = {
            'title': title,
            'content': content,
            'priority': priority,
            'is_active': is_active,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if parsed_publish_date:
            update_data['publish_date'] = parsed_publish_date
        
        # Update in database
        response = supabase_client.supabase.table('announcements').update(update_data).eq('id', announcement_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update announcement")
        
        updated_announcement = response.data[0]
        
        return {
            "success": True,
            "data": {
                "id": updated_announcement['id'],
                "title": updated_announcement['title'],
                "content": updated_announcement['content'],
                "priority": updated_announcement['priority'],
                "publish_date": updated_announcement['publish_date'],
                "is_active": updated_announcement['is_active'],
                "created_by": updated_announcement['created_by'],
                "created_at": updated_announcement['created_at'],
                "updated_at": updated_announcement.get('updated_at')
            },
            "message": "Announcement updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update announcement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update announcement: {str(e)}")

@router.delete("/announcements/{announcement_id}", response_model=Dict[str, Any])
async def delete_announcement(
    announcement_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Duyuru sil (Admin only)
    """
    try:
        logger.info(f"Admin {current_user.id} deleting announcement: {announcement_id}")
        
        # Check if announcement exists
        existing = supabase_client.supabase.table('announcements').select('id, title').eq('id', announcement_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        announcement_title = existing.data[0]['title']
        
        # Delete from database
        response = supabase_client.supabase.table('announcements').delete().eq('id', announcement_id).execute()
        
        return {
            "success": True,
            "data": {
                "id": announcement_id,
                "title": announcement_title
            },
            "message": "Announcement deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete announcement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete announcement: {str(e)}")

@router.get("/dashboard/stats", response_model=Dict[str, Any])
async def dashboard_statistics(
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Ana sayfa için genel istatistikler (Admin only)
    
    Frontend ana sayfasında gösterilecek:
    - Toplam üye sayısı
    - Toplam doküman sayısı
    - Toplam sorgu sayısı
    - Son 24 saatteki aktivite
    - Sistem performance metrikleri
    """
    try:
        from datetime import datetime, timedelta
        import time
        
        start_time = time.time()
        logger.info(f"Dashboard statistics requested by admin {current_user.id}")
        
        # Tarih hesaplamaları
        now = datetime.utcnow()
        last_24h = (now - timedelta(hours=24)).isoformat()
        last_30d = (now - timedelta(days=30)).isoformat()
        
        # Paralel veri toplama
        stats = {}
        
        # 1. Toplam kullanıcı sayısı
        try:
            users_result = supabase_client.supabase.table('user_profiles').select('id').execute()
            stats['total_users'] = len(users_result.data) if users_result.data else 0
        except Exception as e:
            logger.warning(f"Failed to get user count: {e}")
            stats['total_users'] = 0
            
        # 2. Toplam doküman sayısı
        try:
            docs_result = supabase_client.supabase.table('mevzuat_documents').select('id').execute()
            stats['total_documents'] = len(docs_result.data) if docs_result.data else 0
        except Exception as e:
            logger.warning(f"Failed to get document count: {e}")
            stats['total_documents'] = 0
            
        # 3. Toplam sorgu sayısı
        try:
            queries_result = supabase_client.supabase.table('search_logs').select('id').execute()
            stats['total_queries'] = len(queries_result.data) if queries_result.data else 0
        except Exception as e:
            logger.warning(f"Failed to get query count: {e}")
            stats['total_queries'] = 0
            
        # 4. Son 24 saatteki sorgular
        try:
            recent_queries = supabase_client.supabase.table('search_logs')\
                .select('id')\
                .gte('created_at', last_24h)\
                .execute()
            stats['queries_last_24h'] = len(recent_queries.data) if recent_queries.data else 0
        except Exception as e:
            logger.warning(f"Failed to get recent queries: {e}")
            stats['queries_last_24h'] = 0
            
        # 5. Aktif kullanıcılar (son 30 gün)
        try:
            active_users = supabase_client.supabase.table('search_logs')\
                .select('user_id')\
                .gte('created_at', last_30d)\
                .execute()
            unique_users = set()
            if active_users.data:
                for log in active_users.data:
                    if log.get('user_id'):
                        unique_users.add(log['user_id'])
            stats['active_users_30d'] = len(unique_users)
        except Exception as e:
            logger.warning(f"Failed to get active users: {e}")
            stats['active_users_30d'] = 0
            
        # 6. Ortalama güvenilirlik skoru
        try:
            reliability_result = supabase_client.supabase.table('search_logs')\
                .select('reliability_score')\
                .gte('created_at', last_30d)\
                .execute()
            
            scores = []
            if reliability_result.data:
                for log in reliability_result.data:
                    score = log.get('reliability_score')
                    if score and isinstance(score, (int, float)):
                        scores.append(score)
            
            stats['avg_reliability_score'] = round(sum(scores) / len(scores), 2) if scores else 0
        except Exception as e:
            logger.warning(f"Failed to get reliability scores: {e}")
            stats['avg_reliability_score'] = 0
            
        # 7. Kredi işlemleri
        try:
            credit_result = supabase_client.supabase.table('credit_transactions').select('id').execute()
            stats['total_credit_transactions'] = len(credit_result.data) if credit_result.data else 0
        except Exception as e:
            logger.warning(f"Failed to get credit transactions: {e}")
            stats['total_credit_transactions'] = 0
            
        # 8. Doküman kategorileri (Top 5)
        try:
            categories_result = supabase_client.supabase.table('mevzuat_documents')\
                .select('category')\
                .execute()
            
            category_count = {}
            if categories_result.data:
                for doc in categories_result.data:
                    category = doc.get('category') or 'Belirtilmemiş'
                    category_count[category] = category_count.get(category, 0) + 1
            
            # En çok kullanılan 5 kategori
            top_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:5]
            stats['top_categories'] = [
                {"name": cat, "count": count} for cat, count in top_categories
            ]
        except Exception as e:
            logger.warning(f"Failed to get categories: {e}")
            stats['top_categories'] = []
            
        # 9. Son yüklenen dokümanlar (5 adet)
        try:
            recent_docs = supabase_client.supabase.table('mevzuat_documents')\
                .select('id, title, category, created_at')\
                .order('created_at', desc=True)\
                .limit(5)\
                .execute()
            
            stats['recent_documents'] = recent_docs.data if recent_docs.data else []
        except Exception as e:
            logger.warning(f"Failed to get recent documents: {e}")
            stats['recent_documents'] = []
            
        # 10. Sistem performance
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Redis durumu (basit ping)
        redis_status = "healthy"
        try:
            from services.redis_service import RedisService
            redis_service = RedisService()
            await redis_service.ping()
        except Exception:
            redis_status = "warning"
            
        # Elasticsearch durumu
        es_status = "healthy"
        try:
            from services.elasticsearch_service import ElasticsearchService
            async with ElasticsearchService() as es_service:
                health_data = await es_service.health_check()
                if health_data.get("health") != "ok":
                    es_status = "warning"
        except Exception:
            es_status = "error"
            
        # Final response
        return {
            "success": True,
            "data": {
                "overview": {
                    "total_users": stats['total_users'],
                    "total_documents": stats['total_documents'],
                    "total_queries": stats['total_queries'],
                    "active_users_30d": stats['active_users_30d']
                },
                "activity": {
                    "queries_last_24h": stats['queries_last_24h'],
                    "avg_reliability_score": stats['avg_reliability_score'],
                    "total_credit_transactions": stats['total_credit_transactions']
                },
                "content": {
                    "top_categories": stats['top_categories'],
                    "recent_documents": stats['recent_documents']
                },
                "system": {
                    "response_time_ms": response_time,
                    "redis_status": redis_status,
                    "elasticsearch_status": es_status,
                    "timestamp": now.isoformat()
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Dashboard statistics error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard statistics: {str(e)}"
        )

@router.get("/system/health", response_model=Dict[str, Any])
async def system_health(
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Comprehensive system health check (Admin only)
    
    Returns detailed health information for all system components:
    - Database (Supabase) 
    - Redis cache
    - Elasticsearch
    - Celery workers
    - Email service (SMTP)
    - AI services (OpenAI, Groq)
    - Storage (Bunny.net)
    - API performance metrics
    """
    try:
        from services.health_service import HealthService
        
        health_service = HealthService(db)
        health_data = await health_service.get_comprehensive_health()
        
        logger.info(f"System health check requested by admin {current_user.id}")
        
        return {
            "success": True,
            "data": health_data
        }
        
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check system health: {str(e)}"
        )

@router.get("/embeddings/count", response_model=Dict[str, Any])
async def embeddings_count(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    current_user: UserResponse = Depends(get_admin_user)
):
    """Get total embeddings count from Elasticsearch (Admin only)"""
    try:
        from services.embedding_service import EmbeddingService
        
        embedding_service = EmbeddingService()
        count = await embedding_service.get_embeddings_count(document_id)
        
        return {
            "success": True,
            "data": {
                "total_embeddings": count,
                "document_id": document_id,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get embeddings count: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get embeddings count: {str(e)}"
        )

@router.get("/documents")
async def list_documents(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    search: Optional[str] = Query(None, description="Search in title or filename"),
    esasNo: Optional[str] = Query(None, description="Filter by esasNo (metadata)"),
    kararNo: Optional[str] = Query(None, description="Filter by kararNo (metadata)"),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    List all documents with enhanced admin features
    
    Returns:
    - Paginated document list with metadata
    - Bunny.net URLs for each document
    - Processing status and error info
    - File sizes and creation dates
    """
    try:
        if esasNo and kararNo:
            response = supabase_client.supabase.table('yargitay_documents').select(
                'id, esas_no, karar_no'
            ).eq('esas_no', esasNo).eq('karar_no', kararNo).execute()

            data = []
            for doc in response.data or []:
                data.append({
                    "id": doc.get("id"),
                    "esasNo": doc.get("esas_no"),
                    "kararNo": doc.get("karar_no")
                })

            return {"data": data}

        logger.info(f"Admin listing documents - page: {page}, limit: {limit}, filters: category={category}, status={status}")
        
        # Build query
        query = supabase_client.supabase.table('mevzuat_documents').select(
            'id, title, belge_adi, filename, file_url, category, institution, processing_status, file_size, created_at, updated_at, uploaded_by, content_preview'
        )
        
        # Apply filters
        if category:
            query = query.eq('category', category)
        if status:
            query = query.eq('processing_status', status)
        if search:
            query = query.or_(f'title.ilike.%{search}%,filename.ilike.%{search}%')
        
        # Get total count for pagination
        count_response = supabase_client.supabase.table('mevzuat_documents').select('id', count='exact')
        if category:
            count_response = count_response.eq('category', category)
        if status:
            count_response = count_response.eq('processing_status', status)
        if search:
            count_response = count_response.or_(f'title.ilike.%{search}%,filename.ilike.%{search}%')
        
        count_result = count_response.execute()
        total_count = count_result.count
        
        # Get paginated results
        offset = (page - 1) * limit
        documents_response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        # Process documents to add Bunny URLs
        processed_documents = []
        for doc in documents_response.data:
            # Generate Bunny.net URL (3-tier fallback)
            bunny_url = None
            if doc.get('file_url'):
                bunny_url = doc['file_url']
            elif doc.get('filename'):
                bunny_url = f"https://cdn.mevzuatgpt.org/documents/{doc['filename']}"
            else:
                title_filename = f"{doc.get('title', 'unknown')}.pdf"
                bunny_url = f"https://cdn.mevzuatgpt.org/documents/{title_filename}"
            
            processed_documents.append({
                "id": doc['id'],
                "title": doc.get('title'),
                "belge_adi": doc.get('belge_adi'),
                "filename": doc.get('filename'),
                "bunny_url": bunny_url,
                "category": doc.get('category'),
                "institution": doc.get('institution'),
                "processing_status": doc.get('processing_status'),
                "file_size_mb": round(doc.get('file_size', 0) / (1024 * 1024), 2) if doc.get('file_size') else 0,
                "created_at": doc.get('created_at'),
                "updated_at": doc.get('updated_at'),
                "uploaded_by": doc.get('uploaded_by'),
                "has_error": doc.get('processing_status') == 'failed',
                "preview": doc.get('content_preview', '')[:100] + '...' if doc.get('content_preview') else None
            })
        
        return {
            "success": True,
            "data": {
                "documents": processed_documents,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit,
                    "has_next": offset + limit < total_count,
                    "has_previous": page > 1
                },
                "filters": {
                    "category": category,
                    "status": status,
                    "search": search
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/documents/{document_id}")
async def get_document_details(
    document_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Get comprehensive document details (Admin only)
    
    Returns:
    - Document metadata from database
    - Full Bunny.net URL
    - Elasticsearch embedding count  
    - File size and storage info
    - Creation/update timestamps
    """
    try:
        logger.info(f"Getting document details for: {document_id}")
        
        # Step 1: Get document from database
        document_response = supabase_client.supabase.table('mevzuat_documents').select('*').eq('id', document_id).execute()
        if not document_response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = document_response.data[0]
        

        
        # Step 2: Get detailed vector information from Elasticsearch
        from services.embedding_service import EmbeddingService
        from services.elasticsearch_service import ElasticsearchService
        
        embedding_service = EmbeddingService()
        
        # Get embedding count and additional vector info
        try:
            embedding_count = await embedding_service.get_embeddings_count(document_id)
        except Exception as e:
            logger.warning(f"Could not get embedding count for {document_id}: {e}")
            embedding_count = 0
        
        # Get chunk information and vector statistics
        logger.info(f"Attempting to get vector stats for document {document_id}")
        try:
            async with ElasticsearchService() as es_service:
                vector_stats = await es_service.get_document_vector_stats(document_id)
                logger.info(f"Vector stats result: {vector_stats}")
        except Exception as e:
            logger.error(f"Could not get vector stats for {document_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Use embedding count as fallback for all fields
            vector_stats = {"total_vectors": embedding_count, "unique_chunks": embedding_count, "index_name": "mevzuat_embeddings"}
        
        # Step 3: Generate full Bunny.net URL (3-tier fallback system)
        full_url = None
        if document.get('file_url'):
            # Primary: Use existing file_url
            full_url = document['file_url']
        elif document.get('filename'):
            # Fallback: Generate from filename  
            full_url = f"https://cdn.mevzuatgpt.org/documents/{document['filename']}"
        else:
            # Final fallback: Use title as filename
            title_as_filename = f"{document.get('title', 'unknown')}.pdf"
            full_url = f"https://cdn.mevzuatgpt.org/documents/{title_as_filename}"
        
        # Step 4: Calculate storage size from actual vector stats
        file_size_mb = round(document.get('file_size', 0) / (1024 * 1024), 2) if document.get('file_size') else 0
        
        return {
            "success": True,
            "data": {
                "document_info": {
                    "id": document['id'],
                    "title": document.get('title'),
                    "filename": document.get('filename'),
                    "category": document.get('category'),
                    "institution": document.get('institution'),
                    "description": document.get('content_preview'),
                    "processing_status": document.get('processing_status'),
                    "created_at": document.get('created_at'),
                    "updated_at": document.get('updated_at'),
                    "uploaded_by": document.get('uploaded_by')
                },
                "storage_info": {
                    "bunny_url": full_url,
                    "file_size_bytes": document.get('file_size', 0),
                    "file_size_mb": file_size_mb
                },
                "vector_analytics": {
                    "total_vectors": vector_stats.get("total_vectors", embedding_count),
                    "chunk_count": vector_stats.get("unique_chunks", embedding_count),
                    "elasticsearch_index": vector_stats.get("index_name", "mevzuat_embeddings")
                },
                "processing_metrics": {
                    "embeddings_created": embedding_count,
                    "processing_status": document.get('processing_status'),
                    "has_vectors": vector_stats.get("total_vectors", embedding_count) > 0,
                    "vectorization_complete": vector_stats.get("total_vectors", embedding_count) > 0 and document.get('processing_status') == 'completed'
                },
                "metadata": {
                    "document_id": document['id'],
                    "original_filename": document.get('filename'),
                    "category": document.get('category'),
                    "processing_status": document.get('processing_status'),
                    "file_size_bytes": document.get('file_size', 0),
                    "uploaded_by": document.get('uploaded_by'),
                    "upload_date": document.get('created_at'),
                    "last_updated": document.get('updated_at'),
                    "content_preview": document.get('content_preview'),
                    "bunny_cdn_url": document.get('file_url'),
                    "processing_notes": f"Status: {document.get('processing_status', 'unknown')}"
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document details {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document details: {str(e)}")


@router.delete("/documents/bulk-delete")
async def bulk_delete_documents(
    institution: Optional[str] = None,
    document_name: Optional[str] = None,
    creation_date: Optional[str] = None,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Toplu belge silme (Admin only) - Filtrelere göre hem Supabase hem Elasticsearch'ten siler
    
    Filtreler (tümü optional, en az biri gerekli):
    - institution: Kurum adı (exact match)
    - document_name: Belge adı (contains - içerir araması)
    - creation_date: Oluşturma tarihi (YYYY-MM-DD format, saat göz ardı edilir)
    
    Örnek:
    - DELETE /api/admin/documents/bulk-delete?institution=TBB
    - DELETE /api/admin/documents/bulk-delete?document_name=kanun&creation_date=2024-10-19
    - DELETE /api/admin/documents/bulk-delete?institution=UYAP&document_name=tüzük
    """
    try:
        # En az bir filtre gerekli
        if not institution and not document_name and not creation_date:
            raise HTTPException(
                status_code=400, 
                detail="En az bir filtre gereklidir (institution, document_name veya creation_date)"
            )
        
        logger.warning(
            f"Admin {current_user.email} toplu silme başlatıyor - "
            f"Filtreler: institution={institution}, document_name={document_name}, creation_date={creation_date}"
        )
        
        # Supabase query oluştur
        query = supabase_client.supabase.table('mevzuat_documents').select('*')
        
        # Filtreleri uygula
        if institution:
            query = query.eq('institution', institution)
        
        if document_name:
            query = query.ilike('belge_adi', f'%{document_name}%')
        
        if creation_date:
            # Tarih validasyonu
            from datetime import datetime as dt
            try:
                date_obj = dt.strptime(creation_date, '%Y-%m-%d')
                # Başlangıç ve bitiş tarihleri (gün bazlı)
                start_date = f"{creation_date}T00:00:00"
                end_date = f"{creation_date}T23:59:59"
                query = query.gte('created_at', start_date).lte('created_at', end_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Geçersiz tarih formatı. YYYY-MM-DD formatını kullanın (örn: 2024-10-19)"
                )
        
        # Belgeleri getir
        documents_response = query.execute()
        
        if not documents_response.data:
            return {
                "success": True,
                "message": "Filtreye uyan belge bulunamadı",
                "data": {
                    "filters": {
                        "institution": institution,
                        "document_name": document_name,
                        "creation_date": creation_date
                    },
                    "total_found": 0,
                    "total_deleted": 0,
                    "deleted_documents": []
                }
            }
        
        documents = documents_response.data
        total_found = len(documents)
        
        logger.info(f"Toplam {total_found} belge bulundu, silme işlemi başlatılıyor...")
        
        # Silme işlemleri için sonuç listesi
        deletion_results = []
        total_embeddings_deleted = 0
        successful_deletions = 0
        failed_deletions = 0
        
        # Her belge için silme işlemi
        from services.elasticsearch_service import ElasticsearchService
        from services.storage_service import StorageService
        
        storage_service = StorageService()
        
        for document in documents:
            document_id = document['id']
            document_title = document.get('document_title', 'Unknown')
            
            try:
                logger.info(f"Siliniyor: {document_id} - {document_title}")
                
                # 1. Elasticsearch'ten embedding'leri sil
                es_deleted_count = 0
                try:
                    async with ElasticsearchService() as es_service:
                        es_deleted_count = await es_service.delete_document_embeddings(document_id)
                        total_embeddings_deleted += es_deleted_count
                        logger.info(f"{document_id}: {es_deleted_count} embedding silindi")
                except Exception as es_error:
                    logger.error(f"{document_id}: Elasticsearch silme hatası: {es_error}")
                
                # 2. Bunny.net'ten fiziksel dosyayı sil (optional)
                physical_deleted = False
                bunny_url = None
                
                if document.get('file_url'):
                    bunny_url = document['file_url']
                elif document.get('filename'):
                    bunny_url = f"https://cdn.mevzuatgpt.org/documents/{document['filename']}"
                
                if bunny_url:
                    try:
                        await storage_service.delete_file(bunny_url)
                        physical_deleted = True
                        logger.info(f"{document_id}: Fiziksel dosya silindi")
                    except Exception as bunny_error:
                        logger.warning(f"{document_id}: Bunny.net silme hatası: {bunny_error}")
                
                # 3. Supabase'den belge kaydını sil
                supabase_client.supabase.table('mevzuat_documents').delete().eq('id', document_id).execute()
                logger.info(f"{document_id}: Veritabanı kaydı silindi")
                
                successful_deletions += 1
                deletion_results.append({
                    "document_id": document_id,
                    "document_title": document_title,
                    "institution": document.get('institution'),
                    "status": "success",
                    "embeddings_deleted": es_deleted_count,
                    "physical_file_deleted": physical_deleted,
                    "bunny_url": bunny_url
                })
                
            except Exception as doc_error:
                failed_deletions += 1
                logger.error(f"{document_id} silme hatası: {doc_error}")
                deletion_results.append({
                    "document_id": document_id,
                    "document_title": document_title,
                    "institution": document.get('institution'),
                    "status": "failed",
                    "error": str(doc_error)
                })
        
        logger.warning(
            f"Toplu silme tamamlandı - Toplam: {total_found}, "
            f"Başarılı: {successful_deletions}, Başarısız: {failed_deletions}, "
            f"Toplam embedding silindi: {total_embeddings_deleted}"
        )
        
        return {
            "success": True,
            "message": f"{successful_deletions}/{total_found} belge başarıyla silindi",
            "data": {
                "filters": {
                    "institution": institution,
                    "document_name": document_name,
                    "creation_date": creation_date
                },
                "summary": {
                    "total_found": total_found,
                    "successful_deletions": successful_deletions,
                    "failed_deletions": failed_deletions,
                    "total_embeddings_deleted": total_embeddings_deleted
                },
                "deleted_documents": deletion_results,
                "deleted_by": current_user.email,
                "deletion_timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Toplu silme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Toplu silme işlemi başarısız: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Complete document deletion (Admin only)
    
    Deletes:
    1. Document record from Supabase database
    2. Physical PDF file from Bunny.net CDN
    3. All embeddings from Elasticsearch
    
    Returns detailed deletion report.
    """
    try:
        logger.info(f"Admin {current_user.email} starting complete deletion for document: {document_id}")
        
        # Step 1: Get document info first
        document_response = supabase_client.supabase.table('mevzuat_documents').select('*').eq('id', document_id).execute()
        if not document_response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        document = document_response.data[0]
        document_title = document.get('title', 'Unknown Document')
        
        # Step 2: Get embedding count before deletion
        from services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        embedding_count_before = await embedding_service.get_embeddings_count(document_id)
        
        # Step 3: Delete embeddings from Elasticsearch
        logger.info(f"Deleting {embedding_count_before} embeddings from Elasticsearch for document: {document_id}")
        from services.elasticsearch_service import ElasticsearchService
        async with ElasticsearchService() as es_service:
            es_deleted_count = await es_service.delete_document_embeddings(document_id)
            logger.info(f"Deleted {es_deleted_count} embeddings from Elasticsearch")
        
        # Step 4: Delete physical file from Bunny.net
        physical_deleted = False
        bunny_deletion_error = None
        bunny_url = None
        
        # Generate Bunny.net URL for deletion
        if document.get('file_url'):
            bunny_url = document['file_url']
        elif document.get('filename'):
            bunny_url = f"https://cdn.mevzuatgpt.org/documents/{document['filename']}"
        
        if bunny_url:
            try:
                logger.info(f"Deleting physical file from Bunny.net: {bunny_url}")
                from services.storage_service import StorageService
                storage_service = StorageService()
                await storage_service.delete_file(bunny_url)
                physical_deleted = True
                logger.info("Physical file deleted from Bunny.net successfully")
            except Exception as e:
                bunny_deletion_error = str(e)
                logger.warning(f"Failed to delete physical file from Bunny.net: {e}")
        else:
            logger.warning("No file URL found, skipping Bunny.net deletion")
        
        # Step 5: Delete document record from database
        logger.info(f"Deleting document record from database: {document_id}")
        supabase_client.supabase.table('mevzuat_documents').delete().eq('id', document_id).execute()
        logger.info("Document record deleted from database successfully")
        
        # Step 6: Return detailed deletion report
        return {
            "success": True,
            "message": "Document deleted completely",
            "data": {
                "document_id": document_id,
                "document_title": document_title,
                "deletion_summary": {
                    "database_deleted": True,
                    "embeddings_deleted": es_deleted_count,
                    "physical_file_deleted": physical_deleted,
                    "bunny_url": bunny_url
                },
                "details": {
                    "embeddings_count_before": embedding_count_before,
                    "embeddings_deleted": es_deleted_count,
                    "file_size_mb": round(document.get('file_size', 0) / (1024 * 1024), 2) if document.get('file_size') else 0,
                    "bunny_deletion_error": bunny_deletion_error,
                    "deleted_by": current_user.email,
                    "deletion_timestamp": datetime.now().isoformat()
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.put("/documents/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    document_update: DocumentUpdate,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update document metadata (Admin only)
    
    Args:
        document_id: Document UUID
        document_update: Updated document data
        current_user: Current admin user
        db: Database session
    
    Returns:
        Updated document details
    """
    try:
        document_service = DocumentService(db)
        
        document = await document_service.update_document(document_id, document_update)
        
        if not document:
            raise AppException(
                message="Document not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="DOCUMENT_NOT_FOUND"
            )
        
        return success_response(data=document)
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {str(e)}")
        raise AppException(
            message="Failed to update document",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="UPDATE_FAILED"
        )


        
        # Delete from database (will cascade to embeddings)
        await document_service.delete_document(document_id)
        
        return success_response(
            data={"message": "Document deleted successfully"}
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise AppException(
            message="Failed to delete document",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DELETE_FAILED"
        )

# ========================= USER MANAGEMENT ENDPOINTS =========================

async def get_auth_user_info(user_id: str):
    """Get user info from auth.users table"""
    try:
        auth_response = supabase_client.supabase.auth.admin.get_user_by_id(user_id)
        if auth_response.user:
            user = auth_response.user
            
            # Supabase Auth'da ban durumu kontrol etmek için alternatif yöntemler
            is_banned = False
            banned_until = None
            
            # Debug: User objesinin tüm raw içeriğini görelim
            user_dict = user.__dict__ if hasattr(user, '__dict__') else {}
            logger.info(f"Debug {user_id} - Full user object: {user_dict}")
            
            # Tüm mümkün ban field'larını kontrol edelim
            potential_ban_fields = [
                'banned_until', 'banned_at', 'ban_duration', 'is_banned', 'banned',
                'disabled_until', 'disabled_at', 'is_disabled', 'disabled',
                'locked_until', 'locked_at', 'is_locked', 'locked',
                'blocked_until', 'blocked_at', 'is_blocked', 'blocked'
            ]
            
            for field in potential_ban_fields:
                value = getattr(user, field, None)
                if value:
                    logger.info(f"Debug {user_id} - {field}: {value}")
                    is_banned = True
                    if field.endswith('_until'):
                        banned_until = value
            
            # 1. app_metadata'da ban bilgisi kontrol et
            app_metadata = getattr(user, 'app_metadata', {}) or {}
            logger.info(f"Debug {user_id} - app_metadata: {app_metadata}")
            
            if app_metadata.get('banned') or app_metadata.get('is_banned'):
                is_banned = True
                banned_until = app_metadata.get('banned_until')
                logger.info(f"Debug {user_id} - Ban bulundu app_metadata'da!")
            
            # 2. user_metadata'da ban bilgisi kontrol et  
            user_metadata = getattr(user, 'user_metadata', {}) or {}
            logger.info(f"Debug {user_id} - user_metadata: {user_metadata}")
            
            if user_metadata.get('banned') or user_metadata.get('is_banned'):
                is_banned = True
                banned_until = user_metadata.get('banned_until')
                logger.info(f"Debug {user_id} - Ban bulundu user_metadata'da!")
            
            # 3. Role-based ban kontrolü (role 'banned' ise)
            user_role = getattr(user, 'role', 'authenticated')
            logger.info(f"Debug {user_id} - user_role: {user_role}")
            
            if user_role == 'banned' or user_role == 'disabled':
                is_banned = True
                logger.info(f"Debug {user_id} - Ban bulundu role'da!")
            
            # 4. Direct SQL sorgusu ile auth.users tablosundan ban durumu kontrol et
            try:
                # Supabase'de raw SQL ile auth.users tablosunu kontrol edelim
                ban_check_response = supabase_client.supabase.rpc('check_user_ban_status', {'user_id': user_id}).execute()
                if ban_check_response.data:
                    ban_data = ban_check_response.data
                    is_banned = ban_data.get('is_banned', False)
                    banned_until = ban_data.get('banned_until')
            except Exception as sql_error:
                logger.info(f"RPC ban kontrolü çalışmadı (normal): {sql_error}")
            
            
            return {
                "email_confirmed_at": getattr(user, 'email_confirmed_at', None),
                "last_sign_in_at": getattr(user, 'last_sign_in_at', None),
                "is_banned": is_banned,
                "banned_until": banned_until
            }
    except Exception as e:
        logger.warning(f"Auth user info alınamadı {user_id}: {e}")
    return {
        "email_confirmed_at": None,
        "last_sign_in_at": None,
        "is_banned": False,
        "banned_until": None
    }

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına kullanıcı sayısı"),
    role: Optional[str] = Query(None, description="Role göre filtrele (user/admin)"),
    search: Optional[str] = Query(None, description="Email veya ad soyad ile ara"),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Tüm kullanıcıları listele (Admin only)
    
    Returns:
    - Sayfalanmış kullanıcı listesi
    - Kredi bilgileri
    - Son giriş tarihleri
    - İstatistikler
    """
    try:
        logger.info(f"Admin {current_user.email} kullanıcıları listeli - sayfa: {page}, limit: {limit}")
        
        # Supabase Auth'dan RAW database response alacağız (banned_until field için)
        import httpx
        import os
        
        # Environment'dan Supabase URL ve key'i al
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        # Supabase service key ile direct API çağrısı
        headers = {
            'Authorization': f'Bearer {supabase_service_key}',
            'apikey': supabase_service_key,
            'Content-Type': 'application/json'
        }
        
        # Raw auth.users verilerini al
        auth_api_url = f"{supabase_url}/auth/v1/admin/users"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(auth_api_url, headers=headers)
            auth_users_raw = response.json()
            
        logger.info(f"Debug - Raw API ile {len(auth_users_raw.get('users', []))} kullanıcı bulundu")
        
        # Auth users'ı dictionary'e çevir
        auth_users = {user['id']: user for user in auth_users_raw.get('users', [])}
        
        # İlk kullanıcının banned_until field'ını kontrol et
        if auth_users:
            first_user = next(iter(auth_users.values()))
            banned_until = first_user.get('banned_until')
        
        # Base query
        query = supabase_client.supabase.table('user_profiles').select(
            'id, email, full_name, ad, soyad, meslek, calistigi_yer, role, created_at, updated_at'
        )
        
        # Filtreleme
        if role:
            query = query.eq('role', role)
        if search:
            search_term = f'%{search}%'
            query = query.or_(f'email.ilike.{search_term},full_name.ilike.{search_term},ad.ilike.{search_term},soyad.ilike.{search_term}')
        
        # Toplam sayı
        count_query = supabase_client.supabase.table('user_profiles').select('id', count='exact')
        if role:
            count_query = count_query.eq('role', role)
        if search:
            search_term = f'%{search}%'
            count_query = count_query.or_(f'email.ilike.{search_term},full_name.ilike.{search_term},ad.ilike.{search_term},soyad.ilike.{search_term}')
        
        count_result = count_query.execute()
        total_count = count_result.count
        
        # Sayfalanmış sonuçlar
        offset = (page - 1) * limit
        users_response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        # Kullanıcı detaylarını zenginleştir (listUsers() verileri kullan)
        enriched_users = []
        for user in users_response.data:
            user_id = user['id']
            
            # Auth kullanıcısından ban bilgilerini al  
            auth_user = auth_users.get(user_id)
            auth_info = {
                "email_confirmed_at": None,
                "last_sign_in_at": None,
                "is_banned": False,
                "banned_until": None
            }
            
            if auth_user:
                # app_metadata'dan ban bilgilerini kontrol et
                app_metadata = auth_user.get('app_metadata', {})
                banned_until_str = app_metadata.get('banned_until')
                is_banned = app_metadata.get('is_banned', False) or app_metadata.get('banned', False)
                banned_until = None
                
                if banned_until_str:
                    # Tarih string'ini parse et
                    from datetime import datetime
                    try:
                        banned_until_datetime = datetime.fromisoformat(banned_until_str.replace('Z', '+00:00'))
                        current_time = datetime.now(banned_until_datetime.tzinfo)
                        
                        # Ban süresi hala aktif mi?
                        if banned_until_datetime > current_time:
                            is_banned = True
                            banned_until = banned_until_str
                        # else: Ban süresi dolmuş, is_banned=False kalır
                    except Exception as date_error:
                        logger.warning(f"Banned_until tarihi parse edilemedi: {date_error}")
                
                # Email confirmed ve last sign in al
                email_confirmed_at = auth_user.get('email_confirmed_at')
                last_sign_in_at = auth_user.get('last_sign_in_at')
                
                auth_info = {
                    "email_confirmed_at": email_confirmed_at,
                    "last_sign_in_at": last_sign_in_at,
                    "is_banned": is_banned,
                    "banned_until": banned_until
                }
            
            # Kredi bilgilerini al
            credit_response = supabase_client.supabase.table('user_credit_balance').select('current_balance, total_used').eq('user_id', user['id']).execute()
            
            # Basit null kontrolü - kaydı yoksa 0 değerler döndür
            if credit_response.data and len(credit_response.data) > 0:
                credit_data = credit_response.data[0]
                current_balance = credit_data.get('current_balance') if credit_data.get('current_balance') is not None else 0
                total_used = credit_data.get('total_used') if credit_data.get('total_used') is not None else 0
            else:
                # Kredi kaydı yok, 0 değerler döndür
                current_balance = 0
                total_used = 0
            
            # Toplam satın alınan krediyi hesapla
            try:
                # user_credits tablosundan pozitif tutarları topla (satın alma işlemleri)
                purchase_response = supabase_client.supabase.table('user_credits').select('amount').eq('user_id', user['id']).gt('amount', 0).execute()
                total_purchased = sum(item['amount'] for item in purchase_response.data) if purchase_response.data else 0
            except Exception as e:
                logger.warning(f"Toplam satın alınan kredi hesaplanamadı {user['id']}: {e}")
                total_purchased = 0
            
            # Arama sayısı
            search_response = supabase_client.supabase.table('search_logs').select('id', count='exact').eq('user_id', user['id']).execute()
            search_count = search_response.count
            
            enriched_users.append({
                "id": user['id'],
                "email": user['email'],
                "full_name": user.get('full_name'),
                "ad": user.get('ad'),
                "soyad": user.get('soyad'),
                "meslek": user.get('meslek'),
                "calistigi_yer": user.get('calistigi_yer'),
                "role": user['role'],
                "created_at": user['created_at'],
                "updated_at": user.get('updated_at'),
                # Kredi bilgileri (flat format - eski uyumluluk için)
                "current_balance": current_balance,        # Mevcut kredi
                "total_used": total_used,                 # Kullanılan kredi  
                "total_purchased": total_purchased,       # Toplam satın alınan
                "search_count": search_count,
                # listUsers() ile alınan auth bilgileri
                "email_confirmed_at": auth_info["email_confirmed_at"],
                "last_sign_in_at": auth_info["last_sign_in_at"],
                "is_banned": auth_info["is_banned"],
                "banned_until": auth_info["banned_until"]
            })
        
        return {
            "users": enriched_users,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit,
                "has_next": offset + limit < total_count,
                "has_previous": page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"Kullanıcıları listelerken hata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kullanıcıları listeleme başarısız: {str(e)}")

@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_details(
    user_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Kullanıcı detaylarını getir (Admin only)
    
    Returns:
    - Tam kullanıcı bilgileri
    - Kredi geçmişi
    - Aktivite istatistikleri
    """
    try:
        logger.info(f"Admin {current_user.email} kullanıcı detaylarını görüntülüyor: {user_id}")
        
        # Kullanıcı bilgilerini al
        user_response = supabase_client.supabase.table('user_profiles').select('*').eq('id', user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        user = user_response.data[0]
        
        # Auth.users bilgileri
        auth_info = await get_auth_user_info(user_id)
        
        # Kredi bilgilerini al
        credit_response = supabase_client.supabase.table('user_credit_balance').select('current_balance, total_used').eq('user_id', user_id).execute()
        
        # Basit null kontrolü - kaydı yoksa 0 değerler döndür
        if credit_response.data and len(credit_response.data) > 0:
            credit_data = credit_response.data[0]
            current_balance = credit_data.get('current_balance') if credit_data.get('current_balance') is not None else 0
            total_used = credit_data.get('total_used') if credit_data.get('total_used') is not None else 0
        else:
            # Kredi kaydı yok, 0 değerler döndür
            current_balance = 0
            total_used = 0
        
        # Toplam satın alınan krediyi hesapla
        try:
            # user_credits tablosundan pozitif tutarları topla (satın alma işlemleri)
            purchase_response = supabase_client.supabase.table('user_credits').select('amount').eq('user_id', user_id).gt('amount', 0).execute()
            total_purchased = sum(item['amount'] for item in purchase_response.data) if purchase_response.data else 0
        except Exception as e:
            logger.warning(f"Toplam satın alınan kredi hesaplanamadı {user_id}: {e}")
            total_purchased = 0
        
        # Arama sayısı
        search_response = supabase_client.supabase.table('search_logs').select('id', count='exact').eq('user_id', user_id).execute()
        search_count = search_response.count
        
        return {
            "id": user['id'],
            "email": user['email'],
            "full_name": user.get('full_name'),
            "ad": user.get('ad'),
            "soyad": user.get('soyad'),
            "meslek": user.get('meslek'),
            "calistigi_yer": user.get('calistigi_yer'),
            "role": user['role'],
            "created_at": user['created_at'],
            "updated_at": user.get('updated_at'),
            # Kredi bilgileri (flat format)
            "current_balance": current_balance,        # Mevcut kredi
            "total_used": total_used,                 # Kullanılan kredi
            "total_purchased": total_purchased,       # Toplam satın alınan
            "search_count": search_count,
            # Auth.users bilgileri
            "email_confirmed_at": auth_info["email_confirmed_at"],
            "last_sign_in_at": auth_info["last_sign_in_at"],
            "is_banned": auth_info["is_banned"],
            "banned_until": auth_info["banned_until"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı detaylarını getirirken hata {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kullanıcı detaylarını getirme başarısız: {str(e)}")

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_update: AdminUserUpdate,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Kullanıcı bilgilerini güncelle (Admin only)
    
    Güncellenebilir alanlar:
    - Email, ad, soyad, meslek, çalıştığı yer
    - Role (user/admin)
    - Aktif durumu
    """
    try:
        logger.info(f"Admin {current_user.email} kullanıcıyı güncelliyor: {user_id}")
        
        # Kullanıcının varlığını kontrol et
        existing_user = supabase_client.supabase.table('user_profiles').select('*').eq('id', user_id).execute()
        if not existing_user.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Güncelleme verilerini hazırla
        update_data = {}
        if user_update.email is not None:
            update_data['email'] = user_update.email
        if user_update.full_name is not None:
            update_data['full_name'] = user_update.full_name
        if user_update.ad is not None:
            update_data['ad'] = user_update.ad
        if user_update.soyad is not None:
            update_data['soyad'] = user_update.soyad
        if user_update.meslek is not None:
            update_data['meslek'] = user_update.meslek
        if user_update.calistigi_yer is not None:
            update_data['calistigi_yer'] = user_update.calistigi_yer
        if user_update.role is not None:
            update_data['role'] = user_update.role
        
        if not update_data:
            raise HTTPException(status_code=400, detail="Güncellenecek veri bulunamadı")
        
        update_data['updated_at'] = datetime.now().isoformat()
        
        # user_profiles tablosunu güncelle
        result = supabase_client.supabase.table('user_profiles').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Kullanıcı güncellenemedi")
        
        # auth.users tablosunu da güncelle (email değişikliği için)
        auth_update_data = {}
        if user_update.email is not None:
            auth_update_data['email'] = user_update.email
        
        if auth_update_data:
            try:
                import os
                import httpx
                
                supabase_url = os.getenv('SUPABASE_URL')
                supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
                
                headers = {
                    'Authorization': f'Bearer {supabase_service_key}',
                    'apikey': supabase_service_key,
                    'Content-Type': 'application/json'
                }
                
                # auth.users tablosunu da güncelle
                auth_api_url = f"{supabase_url}/auth/v1/admin/users/{user_id}"
                
                async with httpx.AsyncClient() as client:
                    auth_response = await client.put(auth_api_url, headers=headers, json=auth_update_data)
                    
                if auth_response.status_code == 200:
                    logger.info(f"Auth.users tablosu da güncellendi: {user_id}")
                else:
                    logger.warning(f"Auth.users güncelleme başarısız: {auth_response.text}")
                    
            except Exception as auth_error:
                logger.error(f"Auth.users güncelleme hatası: {auth_error}")
                # user_profiles güncellemesi başarılı, auth hatası kritik değil
        
        return {
            "success": True,
            "message": "Kullanıcı başarıyla güncellendi",
            "data": {
                "user_id": user_id,
                "updated_fields": list(update_data.keys()),
                "updated_by": current_user.email,
                "timestamp": datetime.now().isoformat(),
                "auth_updated": len(auth_update_data) > 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı güncelleme hatası {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kullanıcı güncelleme başarısız: {str(e)}")

# Note: Ban/unban functionality removed because is_active column doesn't exist in user_profiles table
# If ban functionality is needed, consider using role changes or a separate banned_users table

@router.put("/users/{user_id}/credits")
async def update_user_credits(
    user_id: str,
    credit_update: UserCreditUpdate,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Kullanıcı kredisini güncelle (Admin only)
    
    Pozitif değer: Kredi ekle
    Negatif değer: Kredi düş
    """
    try:
        logger.info(f"Admin {current_user.email} kullanıcı kredisini güncelliyor: {user_id}, miktar: {credit_update.amount}")
        
        # Kullanıcının varlığını kontrol et
        existing_user = supabase_client.supabase.table('user_profiles').select('email').eq('id', user_id).execute()
        if not existing_user.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        user_email = existing_user.data[0]['email']
        
        # Mevcut kredi bakiyesini al
        credit_response = supabase_client.supabase.table('user_credit_balance').select('current_balance, total_used').eq('user_id', user_id).execute()
        
        if credit_response.data:
            # Mevcut bakiye varsa güncelle
            current_balance = credit_response.data[0]['current_balance']
            total_used = credit_response.data[0]['total_used']
            new_balance = current_balance + credit_update.amount
            
            if new_balance < 0:
                raise HTTPException(status_code=400, detail="Kredi bakiyesi 0'ın altına düşemez")
            
            # Eğer kredi ekliyorsak total_purchased da güncellenir, çıkarıyorsak total_used güncellenir
            update_data = {
                'current_balance': new_balance,
                'updated_at': datetime.now().isoformat()
            }
            
            if credit_update.amount > 0:
                # Kredi ekleme
                current_total_purchased = current_balance + total_used  # Toplam satın alınmış
                update_data['total_purchased'] = current_total_purchased + credit_update.amount
            else:
                # Kredi çıkarma
                update_data['total_used'] = total_used + abs(credit_update.amount)
            
            # Bakiyeyi güncelle
            supabase_client.supabase.table('user_credit_balance').update(update_data).eq('user_id', user_id).execute()
        else:
            # İlk kredi kaydı oluştur
            if credit_update.amount < 0:
                raise HTTPException(status_code=400, detail="Kullanıcının kredi kaydı yok, negatif miktar eklenemez")
            
            supabase_client.supabase.table('user_credit_balance').insert({
                'user_id': user_id,
                'current_balance': credit_update.amount,
                'total_purchased': credit_update.amount,
                'total_used': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
            new_balance = credit_update.amount
        
        # Kredi transaction kaydı
        transaction_type = 'credit' if credit_update.amount > 0 else 'debit'
        supabase_client.supabase.table('credit_transactions').insert({
            'user_id': user_id,
            'amount': abs(credit_update.amount),
            'transaction_type': transaction_type,
            'description': f"Admin tarafından manuel {transaction_type}: {credit_update.reason} (Yapan: {current_user.email})",
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return {
            "success": True,
            "message": "Kullanıcı kredisi başarıyla güncellendi",
            "data": {
                "user_id": user_id,
                "user_email": user_email,
                "amount_changed": credit_update.amount,
                "new_balance": new_balance,
                "reason": credit_update.reason,
                "updated_by": current_user.email,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı kredi güncelleme hatası {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kullanıcı kredi güncelleme başarısız: {str(e)}")

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Kullanıcıyı tamamen sil (Admin only)
    
    UYARI: Bu işlem geri alınamaz!
    Kullanıcıyı ve tüm ilişkili verilerini siler:
    - User profile
    - Credit records
    - Search logs
    - Uploaded documents (opsiyonel)
    """
    try:
        logger.info(f"Admin {current_user.email} kullanıcıyı siliyor: {user_id}")
        
        # Kullanıcının varlığını kontrol et
        existing_user = supabase_client.supabase.table('user_profiles').select('email').eq('id', user_id).execute()
        if not existing_user.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        user_email = existing_user.data[0]['email']
        
        # Admin kendini silemez
        if str(current_user.id) == user_id:
            raise HTTPException(status_code=400, detail="Kendi hesabınızı silemezsiniz")
        
        # İlişkili verileri sil - TÜM KULLANICI VERİLERİ TEMİZLENİR!
        deletion_stats = {
            "credit_balance_deleted": 0,
            "user_credits_deleted": 0,
            "transactions_deleted": 0,
            "search_logs_deleted": 0,
            "support_tickets_deleted": 0,
            "user_feedback_deleted": 0,
            "documents_found": 0
        }
        
        # 1. İlişkili verileri sil (foreign key constraints nedeniyle)
        # Kredi bakiye kayıtlarını sil
        credit_balance_result = supabase_client.supabase.table('user_credit_balance').delete().eq('user_id', user_id).execute()
        deletion_stats["credit_balance_deleted"] = len(credit_balance_result.data) if credit_balance_result.data else 0
        
        # Kredi tarihi kayıtlarını sil (user_credits tablosu)
        user_credits_result = supabase_client.supabase.table('user_credits').delete().eq('user_id', user_id).execute()
        deletion_stats["user_credits_deleted"] = len(user_credits_result.data) if user_credits_result.data else 0
        
        # Kredi transaction kayıtlarını sil
        transactions_result = supabase_client.supabase.table('credit_transactions').delete().eq('user_id', user_id).execute()
        deletion_stats["transactions_deleted"] = len(transactions_result.data) if transactions_result.data else 0
        
        # Arama loglarını sil
        search_logs_result = supabase_client.supabase.table('search_logs').delete().eq('user_id', user_id).execute()
        deletion_stats["search_logs_deleted"] = len(search_logs_result.data) if search_logs_result.data else 0
        
        # Destek biletlerini sil
        support_tickets_result = supabase_client.supabase.table('support_tickets').delete().eq('user_id', user_id).execute()
        deletion_stats["support_tickets_deleted"] = len(support_tickets_result.data) if support_tickets_result.data else 0
        
        # Kullanıcı geri bildirimlerini sil
        user_feedback_result = supabase_client.supabase.table('user_feedback').delete().eq('user_id', user_id).execute()
        deletion_stats["user_feedback_deleted"] = len(user_feedback_result.data) if user_feedback_result.data else 0
        
        # Kullanıcının yüklediği dökümanları kontrol et (silmek yerine uyarı ver)
        documents_result = supabase_client.supabase.table('mevzuat_documents').select('id, title').eq('uploaded_by', user_id).execute()
        deletion_stats["documents_found"] = len(documents_result.data) if documents_result.data else 0
        
        # 2. User_profiles'dan sil
        user_delete_result = supabase_client.supabase.table('user_profiles').delete().eq('id', user_id).execute()
        
        if not user_delete_result.data:
            raise HTTPException(status_code=400, detail="Kullanıcı profilinden silinemedi")
        
        # 3. Auth.users'dan sil
        try:
            supabase_client.supabase.auth.admin.delete_user(user_id)
            logger.info(f"Kullanıcı auth.users'dan silindi: {user_id}")
        except Exception as auth_error:
            logger.warning(f"Auth.users'dan silme hatası (profil zaten silindi): {auth_error}")
        
        logger.warning(f"Kullanıcı silindi: {user_email} - Admin: {current_user.email} - Stats: {deletion_stats}")
        
        return {
            "success": True,
            "message": "Kullanıcı her iki tablodan da (auth.users + user_profiles) başarıyla silindi",
            "data": {
                "user_id": user_id,
                "user_email": user_email,
                "deletion_stats": deletion_stats,
                "deleted_by": current_user.email,
                "timestamp": datetime.now().isoformat(),
                "warning": f"{deletion_stats['documents_found']} döküman bulundu ama silinmedi. Gerekirse ayrıca silin." if deletion_stats["documents_found"] > 0 else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı silme hatası {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Kullanıcı silme başarısız: {str(e)}")

# ========================= BAN/UNBAN ENDPOINTS =========================

@router.put("/users/{user_id}/ban")
async def ban_user(
    user_id: str,
    ban_request: UserBanRequest,
    current_user: UserResponse = Depends(get_admin_user)
):
    """Ban user by setting banned_until in auth.users (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} kullanıcıyı banladı: {user_id}")
        
        # Kullanıcının var olduğunu kontrol et
        user_response = supabase_client.supabase.table('user_profiles').select('email').eq('id', user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Admin'in kendisini banlamasını engelle
        if user_id == str(current_user.id):
            raise HTTPException(status_code=400, detail="Kendi hesabınızı banlayamazsınız")
        
        # Datetime'ı import et (her durumda gerekli)
        from datetime import datetime, timedelta
        
        # Ban süresi hesapla
        ban_until = None
        if ban_request.ban_duration_hours:
            ban_until = (datetime.now() + timedelta(hours=ban_request.ban_duration_hours)).isoformat()
        
        # Auth.users'da ban işlemi - metadata ile yapacağız
        try:
            # Ban bilgisini app_metadata'ya kaydet
            ban_data = {
                "app_metadata": {
                    "banned": True,
                    "is_banned": True,
                    "banned_at": datetime.now().isoformat(),
                    "banned_by": str(current_user.id),
                    "ban_reason": ban_request.reason or "Admin tarafından banlandı"
                }
            }
            
            if ban_request.ban_duration_hours:
                ban_until = (datetime.now() + timedelta(hours=ban_request.ban_duration_hours)).isoformat()
                ban_data["app_metadata"]["banned_until"] = ban_until
                ban_data["app_metadata"]["ban_duration_hours"] = ban_request.ban_duration_hours
            
            # User metadata'yı güncelle
            supabase_client.supabase.auth.admin.update_user_by_id(user_id, ban_data)
            
            logger.info(f"Kullanıcı metadata ile banlandı: {user_id}, süre: {ban_request.ban_duration_hours} saat")
            
            return success_response(
                f"Kullanıcı başarıyla banlandı" + 
                (f" ({ban_request.ban_duration_hours} saat)" if ban_request.ban_duration_hours else " (kalıcı)")
            )
            
        except Exception as auth_error:
            logger.error(f"Auth ban işlemi başarısız: {auth_error}")
            raise HTTPException(status_code=500, detail=f"Ban işlemi başarısız: {auth_error}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı banlanırken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Ban işlemi sırasında hata: {e}")

@router.put("/users/{user_id}/unban")
async def unban_user(
    user_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """Unban user by removing ban from auth.users (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} kullanıcının banını kaldırdı: {user_id}")
        
        # Kullanıcının var olduğunu kontrol et
        user_response = supabase_client.supabase.table('user_profiles').select('email').eq('id', user_id).execute()
        if not user_response.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Auth.users'da unban işlemi - metadata'yı temizle
        try:
            # Datetime import et
            from datetime import datetime
            
            # Ban bilgilerini app_metadata'dan kaldır
            unban_data = {
                "app_metadata": {
                    "banned": False,
                    "is_banned": False,
                    "banned_until": None,  # ✅ Ban süresini temizle
                    "ban_reason": None,    # ✅ Ban sebebini temizle
                    "ban_duration_hours": None,  # ✅ Ban süresini temizle
                    "unbanned_at": datetime.now().isoformat(),
                    "unbanned_by": str(current_user.id)
                }
            }
            
            # User metadata'yı güncelle
            supabase_client.supabase.auth.admin.update_user_by_id(user_id, unban_data)
            
            logger.info(f"Kullanıcı metadata'dan unbanlandı: {user_id}")
            
            return success_response("Kullanıcı banı başarıyla kaldırıldı")
            
        except Exception as auth_error:
            logger.error(f"Auth unban işlemi başarısız: {auth_error}")
            raise HTTPException(status_code=500, detail=f"Ban kaldırma işlemi başarısız: {auth_error}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ban kaldırılırken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Ban kaldırma sırasında hata: {e}")

# ========================= AI PROMPTS MANAGEMENT =========================

@router.get("/prompts")
async def list_prompts(
    current_user: UserResponse = Depends(get_admin_user),
    provider: Optional[str] = Query(None, description="Provider filter (groq, openai, claude)"),
    is_active: Optional[bool] = Query(None, description="Active status filter")
):
    """AI prompt'larını listele (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} AI prompt'larını listeli")
        
        # Base query
        query = supabase_client.supabase.table('ai_prompts').select('*')
        
        # Filters
        if provider:
            query = query.eq('provider', provider)
        if is_active is not None:
            query = query.eq('is_active', is_active)
            
        # Order by update date
        query = query.order('updated_at', desc=True)
        
        response = query.execute()
        
        return {
            "success": True,
            "data": {
                "prompts": response.data,
                "total": len(response.data) if response.data else 0
            }
        }
        
    except Exception as e:
        logger.error(f"AI prompt'ları listelenirken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt'lar listelenemedi: {e}")

@router.get("/prompts/{prompt_id}")
async def get_prompt(
    prompt_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """Specific AI prompt detayını getir (Admin only)"""
    try:
        response = supabase_client.supabase.table('ai_prompts').select('*').eq('id', prompt_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Prompt bulunamadı")
            
        return success_response("Prompt detayı getirildi", response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prompt detayı getirilirken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt detayı getirilemedi: {e}")

@router.post("/prompts")
async def create_prompt(
    prompt_data: dict,
    current_user: UserResponse = Depends(get_admin_user)
):
    """Yeni AI prompt oluştur (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} yeni AI prompt oluşturuyor")
        
        # Required fields validation
        required_fields = ['provider', 'prompt_type', 'prompt_content']
        for field in required_fields:
            if field not in prompt_data:
                raise HTTPException(status_code=400, detail=f"'{field}' alanı gereklidir")
        
        # Provider validation
        valid_providers = ['groq', 'openai', 'claude']
        if prompt_data['provider'] not in valid_providers:
            raise HTTPException(status_code=400, detail=f"Provider '{valid_providers}' listesinden olmalıdır")
            
        # Prompt type validation  
        valid_types = ['system', 'user', 'assistant']
        if prompt_data['prompt_type'] not in valid_types:
            raise HTTPException(status_code=400, detail=f"Prompt type '{valid_types}' listesinden olmalıdır")
        
        # Prepare data
        new_prompt = {
            'provider': prompt_data['provider'],
            'prompt_type': prompt_data['prompt_type'], 
            'prompt_content': prompt_data['prompt_content'],
            'description': prompt_data.get('description'),
            'version': prompt_data.get('version', '1.0'),
            'is_active': prompt_data.get('is_active', True),
            'created_by': str(current_user.id),
            'updated_by': str(current_user.id),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Insert to database
        response = supabase_client.supabase.table('ai_prompts').insert(new_prompt).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Prompt oluşturulamadı")
            
        return success_response("AI prompt başarıyla oluşturuldu", response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI prompt oluşturulurken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt oluşturulamadı: {e}")

@router.put("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    prompt_data: dict,
    current_user: UserResponse = Depends(get_admin_user)
):
    """AI prompt güncelle (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} AI prompt güncelliyor: {prompt_id}")
        
        # Check if prompt exists
        existing = supabase_client.supabase.table('ai_prompts').select('*').eq('id', prompt_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Prompt bulunamadı")
        
        # Prepare update data
        update_data = {
            'updated_by': str(current_user.id),
            'updated_at': datetime.now().isoformat()
        }
        
        # Update allowed fields
        allowed_fields = ['provider', 'prompt_type', 'prompt_content', 'description', 'version', 'is_active']
        for field in allowed_fields:
            if field in prompt_data:
                update_data[field] = prompt_data[field]
        
        # Validate provider if being updated
        if 'provider' in update_data:
            valid_providers = ['groq', 'openai', 'claude']
            if update_data['provider'] not in valid_providers:
                raise HTTPException(status_code=400, detail=f"Provider '{valid_providers}' listesinden olmalıdır")
                
        # Validate prompt_type if being updated
        if 'prompt_type' in update_data:
            valid_types = ['system', 'user', 'assistant']
            if update_data['prompt_type'] not in valid_types:
                raise HTTPException(status_code=400, detail=f"Prompt type '{valid_types}' listesinden olmalıdır")
        
        # Update in database
        response = supabase_client.supabase.table('ai_prompts').update(update_data).eq('id', prompt_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Prompt güncellenemedi")
            
        return success_response("AI prompt başarıyla güncellendi", response.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI prompt güncellenirken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt güncellenemedi: {e}")

@router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """AI prompt sil (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} AI prompt siliyor: {prompt_id}")
        
        # Check if prompt exists
        existing = supabase_client.supabase.table('ai_prompts').select('*').eq('id', prompt_id).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Prompt bulunamadı")
        
        prompt_data = existing.data[0]
        
        # Delete from database
        response = supabase_client.supabase.table('ai_prompts').delete().eq('id', prompt_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Prompt silinemedi")
            
        logger.warning(f"AI prompt silindi: {prompt_data.get('provider')}/{prompt_data.get('prompt_type')} - Admin: {current_user.email}")
        
        return success_response("AI prompt başarıyla silindi", {
            "deleted_prompt": {
                "id": prompt_id,
                "provider": prompt_data.get('provider'),
                "prompt_type": prompt_data.get('prompt_type'),
                "description": prompt_data.get('description')
            },
            "deleted_by": current_user.email,
            "timestamp": datetime.now().isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI prompt silinirken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Prompt silinemedi: {e}")

@router.post("/prompts/refresh-cache")
async def refresh_prompt_cache(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Prompt cache'ini manuel refresh et (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} prompt cache'ini yeniliyor")
        
        # Import PromptService
        from services.prompt_service import prompt_service
        
        # Clear cache
        prompt_service._cached_prompts = {}
        prompt_service._cache_timestamp = None
        
        return success_response("Prompt cache başarıyla temizlendi", {
            "cache_cleared": True,
            "cleared_by": current_user.email,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Prompt cache temizlenirken hata: {e}")
        raise HTTPException(status_code=500, detail=f"Cache temizlenemedi: {e}")

@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    current_user: UserResponse = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess document embeddings (Admin only)
    
    Args:
        document_id: Document UUID
        current_user: Current admin user
        db: Database session
    
    Returns:
        Processing status message
    """
    try:
        document_service = DocumentService(db)
        
        # Check if document exists
        document = await document_service.get_document_by_id(document_id)
        
        if not document:
            raise AppException(
                message="Document not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="DOCUMENT_NOT_FOUND"
            )
        
        # Update status to pending
        await document_service.update_processing_status(document_id, "pending")
        
        # Trigger reprocessing
        process_document_task.delay(document_id)
        
        return success_response(
            data={"message": "Document reprocessing initiated"}
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {str(e)}")
        raise AppException(
            message="Failed to initiate reprocessing",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="REPROCESS_FAILED"
        )


# ============ SEARCH LOGS ADMIN ENDPOINTS ============

@router.get("/search-logs", response_model=Dict[str, Any])
async def get_search_logs(
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt"),
    user_id: Optional[str] = Query(None, description="Kullanıcı ID filtresi"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Tüm arama loglarını listele (Admin)
    """
    try:
        # Base query
        query = supabase_client.supabase.table('search_logs').select('*')
        
        # Kullanıcı filtresi
        if user_id:
            query = query.eq('user_id', user_id)
        
        # Toplam sayı
        count_response = query.execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # Sayfalama
        offset = (page - 1) * limit
        response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        # Kullanıcı bilgilerini ekle
        logs_with_user = []
        if response.data:
            for log in response.data:
                if log.get('user_id'):
                    user_response = supabase_client.supabase.table('user_profiles') \
                        .select('full_name, email') \
                        .eq('id', log['user_id']) \
                        .single() \
                        .execute()
                    
                    log_with_user = log.copy()
                    if user_response.data:
                        log_with_user['user_name'] = user_response.data.get('full_name', 'Bilinmiyor')
                        log_with_user['user_email'] = user_response.data.get('email', 'Bilinmiyor')
                    else:
                        log_with_user['user_name'] = 'Silinmiş Kullanıcı'
                        log_with_user['user_email'] = 'Silinmiş'
                else:
                    log_with_user = log.copy()
                    log_with_user['user_name'] = 'Anonim'
                    log_with_user['user_email'] = 'Anonim'
                
                logs_with_user.append(log_with_user)
        
        return {
            "success": True,
            "data": {
                "search_logs": logs_with_user,
                "total_count": total_count,
                "has_more": total_count > offset + limit,
                "page": page,
                "limit": limit,
                "filters": {
                    "user_id": user_id
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Arama logları alınırken hata: {e}")
        raise HTTPException(
            status_code=500,
            detail="Arama logları alınamadı"
        )

@router.get("/search-logs/stats", response_model=Dict[str, Any])
async def get_search_logs_stats(
    current_user: dict = Depends(get_admin_user)
):
    """
    Arama logları istatistikleri (Admin)
    """
    try:
        # Tüm search logs
        all_logs = supabase_client.supabase.table('search_logs') \
            .select('*') \
            .execute()
        
        stats = {
            "total_searches": 0,
            "total_users": 0,
            "avg_execution_time": 0,
            "avg_results_count": 0,
            "avg_credits_used": 0,
            "avg_reliability_score": 0,
            "top_queries": [],
            "today_searches": 0,
            "successful_searches": 0,  # results_count > 0
            "failed_searches": 0       # results_count = 0
        }
        
        if all_logs.data:
            stats["total_searches"] = len(all_logs.data)
            
            # Unique users
            unique_users = set()
            execution_times = []
            results_counts = []
            credits_used_list = []
            reliability_scores = []
            query_counts = {}
            today_count = 0
            successful = 0
            failed = 0
            
            from datetime import datetime, timezone
            today = datetime.now(timezone.utc).date()
            
            for log in all_logs.data:
                # Unique users
                if log.get('user_id'):
                    unique_users.add(log['user_id'])
                
                # Execution time
                if log.get('execution_time'):
                    execution_times.append(log['execution_time'])
                
                # Results count
                results_count = log.get('results_count', 0)
                results_counts.append(results_count)
                
                if results_count > 0:
                    successful += 1
                else:
                    failed += 1
                
                # Credits
                if log.get('credits_used'):
                    credits_used_list.append(log['credits_used'])
                
                # Reliability
                if log.get('reliability_score'):
                    reliability_scores.append(log['reliability_score'])
                
                # Top queries
                query = log.get('query', '').strip()
                if query:
                    query_counts[query] = query_counts.get(query, 0) + 1
                
                # Today's searches
                if log.get('created_at'):
                    try:
                        log_date = datetime.fromisoformat(log['created_at'].replace('Z', '+00:00')).date()
                        if log_date == today:
                            today_count += 1
                    except:
                        pass
            
            # Calculations
            stats["total_users"] = len(unique_users)
            stats["today_searches"] = today_count
            stats["successful_searches"] = successful
            stats["failed_searches"] = failed
            
            if execution_times:
                stats["avg_execution_time"] = sum(execution_times) / len(execution_times)
            
            if results_counts:
                stats["avg_results_count"] = sum(results_counts) / len(results_counts)
            
            if credits_used_list:
                stats["avg_credits_used"] = sum(credits_used_list) / len(credits_used_list)
            
            if reliability_scores:
                stats["avg_reliability_score"] = sum(reliability_scores) / len(reliability_scores)
            
            # Top 10 queries
            sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
            stats["top_queries"] = [{"query": q, "count": c} for q, c in sorted_queries[:10]]
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Arama istatistikleri alınırken hata: {e}")
        raise HTTPException(
            status_code=500,
            detail="İstatistikler alınamadı"
        )

@router.get("/search-logs/user/{user_id}", response_model=Dict[str, Any])
async def get_user_search_logs(
    user_id: str,
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Belirli kullanıcının arama logları (Admin)
    """
    try:
        # Kullanıcı varlığını kontrol et
        user_check = supabase_client.supabase.table('user_profiles') \
            .select('full_name, email') \
            .eq('id', user_id) \
            .single() \
            .execute()
        
        if not user_check.data:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
        
        # Search logs
        query = supabase_client.supabase.table('search_logs') \
            .select('*') \
            .eq('user_id', user_id)
        
        # Toplam sayı
        count_response = query.execute()
        total_count = len(count_response.data) if count_response.data else 0
        
        # Sayfalama
        offset = (page - 1) * limit
        response = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "success": True,
            "data": {
                "user_info": {
                    "user_id": user_id,
                    "user_name": user_check.data.get('full_name', 'Bilinmiyor'),
                    "user_email": user_check.data.get('email', 'Bilinmiyor')
                },
                "search_logs": response.data or [],
                "total_count": total_count,
                "has_more": total_count > offset + limit,
                "page": page,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Kullanıcı arama logları alınırken hata {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Kullanıcı arama logları alınamadı"
        )

@router.delete("/tasks/clear-all")
async def clear_all_active_tasks(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Clear all active task progress data (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} clearing all active tasks")
        
        from services.progress_service import progress_service
        cleared_count = await progress_service.clear_all_active_tasks()
        
        logger.info(f"Cleared {cleared_count} active tasks")
        
        return {
            "success": True,
            "message": f"{cleared_count} aktif task temizlendi",
            "data": {
                "cleared_count": cleared_count
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to clear active tasks: {e}")
        return {
            "success": False,
            "message": f"Task temizleme başarısız: {str(e)}"
        }

# =====================================
# ELASTICSEARCH ADMIN ENDPOINTS
# =====================================

@router.get("/elasticsearch/status")
async def get_elasticsearch_status(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Elasticsearch durumu ve detaylı bilgileri getir (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} Elasticsearch durumunu sorguluyor")
        
        from services.elasticsearch_service import ElasticsearchService
        
        async with ElasticsearchService() as es_service:
            # Cluster health
            health_data = await es_service.health_check()
            
            # Session for additional queries
            session = await es_service._get_session()
            
            # Get detailed cluster info
            cluster_info = {}
            try:
                async with session.get(f"{es_service.elasticsearch_url}/_cluster/stats") as response:
                    if response.status == 200:
                        stats_data = await response.json()
                        cluster_info = {
                            "total_nodes": stats_data.get("nodes", {}).get("count", {}).get("total", 0),
                            "data_nodes": stats_data.get("nodes", {}).get("count", {}).get("data", 0),
                            "indices_count": stats_data.get("indices", {}).get("count", 0),
                            "total_shards": stats_data.get("indices", {}).get("shards", {}).get("total", 0),
                            "docs_count": stats_data.get("indices", {}).get("docs", {}).get("count", 0),
                            "store_size": stats_data.get("indices", {}).get("store", {}).get("size_in_bytes", 0)
                        }
            except Exception:
                cluster_info = {"error": "Cluster stats unavailable"}
            
            # Get index-specific information
            index_info = {}
            try:
                async with session.get(f"{es_service.elasticsearch_url}/{es_service.index_name}/_stats") as response:
                    if response.status == 200:
                        index_data = await response.json()
                        indices = index_data.get("indices", {})
                        if es_service.index_name in indices:
                            idx_stats = indices[es_service.index_name]
                            index_info = {
                                "index_name": es_service.index_name,
                                "total_docs": idx_stats.get("total", {}).get("docs", {}).get("count", 0),
                                "deleted_docs": idx_stats.get("total", {}).get("docs", {}).get("deleted", 0),
                                "store_size_bytes": idx_stats.get("total", {}).get("store", {}).get("size_in_bytes", 0),
                                "store_size_human": f"{idx_stats.get('total', {}).get('store', {}).get('size_in_bytes', 0) / (1024*1024):.2f} MB"
                            }
            except Exception:
                index_info = {"error": "Index stats unavailable"}
            
            # Document type breakdown
            doc_breakdown = {}
            try:
                # Get unique document IDs count
                agg_query = {
                    "size": 0,
                    "aggs": {
                        "unique_documents": {
                            "cardinality": {"field": "document_id.keyword"}
                        },
                        "institutions": {
                            "terms": {"field": "source_institution.keyword", "size": 20}
                        }
                    }
                }
                
                async with session.post(
                    f"{es_service.elasticsearch_url}/{es_service.index_name}/_search",
                    json=agg_query
                ) as response:
                    if response.status == 200:
                        agg_data = await response.json()
                        aggs = agg_data.get("aggregations", {})
                        doc_breakdown = {
                            "unique_documents": aggs.get("unique_documents", {}).get("value", 0),
                            "total_chunks": agg_data.get("hits", {}).get("total", {}).get("value", 0),
                            "institutions": [
                                {"name": bucket["key"], "chunk_count": bucket["doc_count"]}
                                for bucket in aggs.get("institutions", {}).get("buckets", [])
                            ]
                        }
            except Exception:
                doc_breakdown = {"error": "Document breakdown unavailable"}
        
        return {
            "success": True,
            "data": {
                "connection": "healthy" if health_data.get("health") == "ok" else "error",
                "cluster_health": health_data,
                "cluster_info": cluster_info,
                "index_info": index_info,
                "document_breakdown": doc_breakdown,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Elasticsearch durumu sorgulanırken hata: {e}")
        return {
            "success": False,
            "message": f"Elasticsearch durumu alınamadı: {str(e)}"
        }

@router.delete("/elasticsearch/clear-all")
async def clear_elasticsearch_completely(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Elasticsearch'i tamamen temizle - TÜM VEKTÖR VERİLERİ SİLİNECEK! (Admin only)"""
    try:
        logger.warning(f"CRITICAL: Admin {current_user.email} Elasticsearch tamamen temizleniyor!")
        
        from services.elasticsearch_service import ElasticsearchService
        
        async with ElasticsearchService() as es_service:
            session = await es_service._get_session()
            
            # Get current document count
            docs_before = 0
            try:
                async with session.get(f"{es_service.elasticsearch_url}/{es_service.index_name}/_count") as response:
                    if response.status == 200:
                        count_data = await response.json()
                        docs_before = count_data.get("count", 0)
            except Exception:
                docs_before = 0
            
            # Delete all documents in the index
            delete_query = {"query": {"match_all": {}}}
            
            async with session.post(
                f"{es_service.elasticsearch_url}/{es_service.index_name}/_delete_by_query",
                json=delete_query
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    deleted_count = result.get("deleted", 0)
                    
                    # Get final document count
                    docs_after = 0
                    try:
                        async with session.get(f"{es_service.elasticsearch_url}/{es_service.index_name}/_count") as count_response:
                            if count_response.status == 200:
                                count_data = await count_response.json()
                                docs_after = count_data.get("count", 0)
                    except Exception:
                        docs_after = 0
                    
                    logger.warning(f"Elasticsearch completely cleared: {deleted_count} documents deleted")
                    
                    return {
                        "success": True,
                        "message": "Elasticsearch tamamen temizlendi",
                        "data": {
                            "docs_before": docs_before,
                            "docs_deleted": deleted_count,
                            "docs_after": docs_after,
                            "index_name": es_service.index_name,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Elasticsearch clear failed: HTTP {response.status}, {error_text}")
                    return {
                        "success": False,
                        "message": f"Elasticsearch temizleme başarısız: HTTP {response.status}"
                    }
        
    except Exception as e:
        logger.error(f"Elasticsearch temizleme hatası: {e}")
        return {
            "success": False,
            "message": f"Elasticsearch temizleme başarısız: {str(e)}"
        }

@router.delete("/elasticsearch/clear-document/{document_id}")
async def clear_document_from_elasticsearch(
    document_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """Belirli bir dökümanın tüm vektör verilerini Elasticsearch'ten sil (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} doküman {document_id} Elasticsearch'ten siliniyor")
        
        from services.elasticsearch_service import ElasticsearchService
        
        async with ElasticsearchService() as es_service:
            # Get document stats before deletion
            doc_stats = await es_service.get_document_vector_stats(document_id)
            vectors_before = doc_stats.get("total_vectors", 0)
            chunks_before = doc_stats.get("unique_chunks", 0)
            
            # Delete document embeddings
            deleted_count = await es_service.delete_document_embeddings(document_id)
            
            # Get stats after deletion
            doc_stats_after = await es_service.get_document_vector_stats(document_id)
            vectors_after = doc_stats_after.get("total_vectors", 0)
            
            return {
                "success": True,
                "message": f"Doküman {document_id} Elasticsearch'ten silindi",
                "data": {
                    "document_id": document_id,
                    "vectors_before": vectors_before,
                    "chunks_before": chunks_before,
                    "vectors_deleted": deleted_count,
                    "vectors_after": vectors_after,
                    "index_name": es_service.index_name,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
    except Exception as e:
        logger.error(f"Doküman silme hatası: {e}")
        return {
            "success": False,
            "message": f"Doküman silme başarısız: {str(e)}"
        }

@router.post("/elasticsearch/clear-documents")
async def clear_multiple_documents_from_elasticsearch(
    document_ids: List[str],
    current_user: UserResponse = Depends(get_admin_user)
):
    """Birden fazla dökümanın vektör verilerini Elasticsearch'ten sil (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} {len(document_ids)} doküman Elasticsearch'ten siliniyor")
        
        from services.elasticsearch_service import ElasticsearchService
        
        deletion_results = []
        total_deleted = 0
        
        async with ElasticsearchService() as es_service:
            for document_id in document_ids:
                try:
                    # Get stats before deletion
                    doc_stats = await es_service.get_document_vector_stats(document_id)
                    vectors_before = doc_stats.get("total_vectors", 0)
                    
                    # Delete document embeddings
                    deleted_count = await es_service.delete_document_embeddings(document_id)
                    total_deleted += deleted_count
                    
                    deletion_results.append({
                        "document_id": document_id,
                        "vectors_deleted": deleted_count,
                        "vectors_before": vectors_before,
                        "status": "success"
                    })
                    
                except Exception as doc_error:
                    deletion_results.append({
                        "document_id": document_id,
                        "vectors_deleted": 0,
                        "vectors_before": 0,
                        "status": "error",
                        "error": str(doc_error)
                    })
            
            return {
                "success": True,
                "message": f"{len(document_ids)} doküman işlendi, toplam {total_deleted} vektör silindi",
                "data": {
                    "total_documents": len(document_ids),
                    "total_vectors_deleted": total_deleted,
                    "results": deletion_results,
                    "index_name": es_service.index_name,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
    except Exception as e:
        logger.error(f"Çoklu doküman silme hatası: {e}")
        return {
            "success": False,
            "message": f"Çoklu doküman silme başarısız: {str(e)}"
        }

@router.get("/system/status")
async def get_system_status(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Redis ve Celery sistem durumunu göster (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} sistem durumunu sorguluyor")
        
        # Redis durumu
        redis_status = {}
        redis_service = None
        try:
            # Redis operations with timeout
            redis_service = RedisService()
            
            # Ping test with short timeout
            ping_task = asyncio.create_task(redis_service.ping())
            await asyncio.wait_for(ping_task, timeout=3.0)
            redis_status["connection"] = "healthy"
            
            # Redis bilgileri al - with timeout
            info_task = asyncio.create_task(redis_service.get_info())
            redis_info = await asyncio.wait_for(info_task, timeout=3.0)
            
            # DB size - with timeout  
            size_task = asyncio.create_task(redis_service.get_db_size())
            total_keys = await asyncio.wait_for(size_task, timeout=3.0)
            
            redis_status["info"] = {
                "used_memory": redis_info.get("used_memory_human", "N/A"),
                "connected_clients": redis_info.get("connected_clients", "N/A"),
                "total_keys": total_keys,
                "uptime": redis_info.get("uptime_in_seconds", "N/A")
            }
            
            # Task progress key'lerini say - with timeout
            try:
                progress_task = asyncio.create_task(redis_service.get_keys_pattern("task_progress:*"))
                progress_keys = await asyncio.wait_for(progress_task, timeout=2.0)
                redis_status["active_task_progress"] = len(progress_keys) if progress_keys else 0
            except asyncio.TimeoutError:
                redis_status["active_task_progress"] = "timeout"
            
            # User history key'lerini say - with timeout
            try:
                history_task = asyncio.create_task(redis_service.get_keys_pattern("user_history:*"))
                history_keys = await asyncio.wait_for(history_task, timeout=2.0)
                redis_status["user_histories"] = len(history_keys) if history_keys else 0
            except asyncio.TimeoutError:
                redis_status["user_histories"] = "timeout"
            
            # Connection pool automatically manages connections
            
        except asyncio.TimeoutError:
            redis_status = {
                "connection": "timeout",
                "error": "Redis operations timed out"
            }
            # Connection pool automatically manages connections
        except Exception as redis_error:
            redis_status = {
                "connection": "error",
                "error": str(redis_error)
            }
            # Connection pool automatically manages connections
        
        # Celery durumu - Redis üzerinden kontrol
        celery_status = {}
        try:
            # Redis üzerinden Celery worker durumunu kontrol et
            try:
                # Check for celery workers in Redis
                if redis_service:
                    client = await redis_service._get_client()
                else:
                    raise Exception("Redis service not available")
                
                # Celery worker key'lerini kontrol et
                worker_keys = await client.keys("_kombu.binding.*")
                active_workers = await client.keys("celery@*")
                
                # Basic status
                if worker_keys or active_workers:
                    celery_status = {
                        "connection": "healthy",
                        "worker_count": len(active_workers) if active_workers else 1,
                        "worker_keys": len(worker_keys),
                        "status": "workers_detected"
                    }
                else:
                    celery_status = {
                        "connection": "no_workers",
                        "worker_count": 0,
                        "worker_keys": 0,
                        "status": "no_workers_detected"
                    }
                    
            except Exception as redis_check_error:
                # Fallback: try direct celery check with short timeout
                try:
                    from tasks.celery_app import celery_app
                    inspect = celery_app.control.inspect(timeout=0.5)
                    ping_result = inspect.ping()
                    
                    if ping_result:
                        celery_status = {
                            "connection": "healthy",
                            "worker_count": len(ping_result),
                            "workers": list(ping_result.keys()),
                            "status": "ping_successful"
                        }
                    else:
                        raise Exception("No ping response")
                        
                except Exception:
                    celery_status = {
                        "connection": "error",
                        "error": f"Redis check failed: {str(redis_check_error)}",
                        "worker_count": 0,
                        "status": "connection_failed"
                    }
                    
        except Exception as celery_error:
            celery_status = {
                "connection": "error",
                "error": str(celery_error),
                "worker_count": 0,
                "status": "check_failed"
            }
        
        return {
            "success": True,
            "data": {
                "redis": redis_status,
                "celery": celery_status,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Sistem durumu sorgulama hatası: {e}")
        return {
            "success": False,
            "message": f"Sistem durumu alınamadı: {str(e)}"
        }

@router.delete("/redis/clear-all")
async def clear_redis_completely(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Redis'i tamamen temizle - TÜM DATALAR SİLİNECEK! (Admin only)"""
    try:
        logger.warning(f"CRITICAL: Admin {current_user.email} Redis tamamen temizleniyor!")
        
        from services.redis_service import RedisService
        import asyncio
        redis_service = RedisService()
        
        # Önce mevcut key sayısını al - with timeout
        size_task = asyncio.create_task(redis_service.get_db_size())
        total_keys_before = await asyncio.wait_for(size_task, timeout=5.0)
        
        # Redis database'i tamamen temizle - with timeout
        flush_task = asyncio.create_task(redis_service.flush_db())
        await asyncio.wait_for(flush_task, timeout=10.0)
        
        # Temizlik sonrası kontrol - with timeout
        size_task2 = asyncio.create_task(redis_service.get_db_size())
        total_keys_after = await asyncio.wait_for(size_task2, timeout=5.0)
        
        logger.warning(f"Redis completely flushed: {total_keys_before} keys deleted")
        
        return {
            "success": True,
            "message": "Redis tamamen temizlendi",
            "data": {
                "keys_deleted": total_keys_before,
                "keys_remaining": total_keys_after,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Redis temizleme hatası: {e}")
        return {
            "success": False,
            "message": f"Redis temizleme başarısız: {str(e)}"
        }

@router.delete("/redis/clear-tasks")
async def clear_redis_tasks_only(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Sadece task ile ilgili Redis key'lerini temizle (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} Redis task key'lerini temizliyor")
        
        from services.redis_service import RedisService
        import asyncio
        redis_service = RedisService()
        
        # Task progress key'lerini temizle - with timeout
        progress_task = asyncio.create_task(redis_service.get_keys_pattern("task_progress:*"))
        progress_keys = await asyncio.wait_for(progress_task, timeout=5.0)
        progress_deleted = 0
        if progress_keys:
            delete_task = asyncio.create_task(redis_service.delete_keys(progress_keys))
            await asyncio.wait_for(delete_task, timeout=5.0)
            progress_deleted = len(progress_keys)
        
        # Celery task key'lerini temizle - with timeout
        celery_task = asyncio.create_task(redis_service.get_keys_pattern("celery-task-meta-*"))
        celery_keys = await asyncio.wait_for(celery_task, timeout=5.0)
        celery_deleted = 0
        if celery_keys:
            delete_task2 = asyncio.create_task(redis_service.delete_keys(celery_keys))
            await asyncio.wait_for(delete_task2, timeout=5.0)
            celery_deleted = len(celery_keys)
        
        # Kombu binding key'lerini temizle - with timeout
        kombu_task = asyncio.create_task(redis_service.get_keys_pattern("_kombu.*"))
        kombu_keys = await asyncio.wait_for(kombu_task, timeout=5.0)
        kombu_deleted = 0
        if kombu_keys:
            delete_task3 = asyncio.create_task(redis_service.delete_keys(kombu_keys))
            await asyncio.wait_for(delete_task3, timeout=5.0)
            kombu_deleted = len(kombu_keys)
        
        total_deleted = progress_deleted + celery_deleted + kombu_deleted
        
        logger.info(f"Task keys cleared: {total_deleted} total")
        
        return {
            "success": True,
            "message": f"{total_deleted} task ilişkili key temizlendi",
            "data": {
                "progress_keys_deleted": progress_deleted,
                "celery_keys_deleted": celery_deleted,
                "kombu_keys_deleted": kombu_deleted,
                "total_deleted": total_deleted,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Redis task temizleme hatası: {e}")
        return {
            "success": False,
            "message": f"Redis task temizleme başarısız: {str(e)}"
        }

@router.post("/celery/purge-queue")
async def purge_celery_queue(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Celery queue'larını temizle (Admin only)"""
    try:
        logger.warning(f"Admin {current_user.email} Celery queue'ları temizleniyor")
        
        # Redis connection pool'dan doğrudan temizle
        from services.redis_service import RedisService
        redis_service = RedisService()
        
        # Celery queue key'lerini temizle
        async with RedisService() as client:
            # Celery queue pattern'leri
            queue_keys = await client.keys("celery*")
            unacked_keys = await client.keys("unacked*")
            
            all_keys = list(set(queue_keys + unacked_keys))
            
            if all_keys:
                deleted = await client.delete(*all_keys)
                logger.info(f"Celery queue keys cleared: {deleted}")
                
                return {
                    "success": True,
                    "message": f"Celery queue temizlendi",
                    "data": {
                        "purged_tasks": deleted,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            else:
                return {
                    "success": True,
                    "message": "Queue'da task bulunamadı",
                    "data": {
                        "purged_tasks": 0,
                        "timestamp": datetime.now().isoformat()
                    }
                }
        
    except Exception as e:
        logger.error(f"Celery queue temizleme hatası: {e}")
        return {
            "success": False,
            "message": f"Redis connection hatası - Lütfen tekrar deneyin"
        }

@router.delete("/celery/clear-active")
async def clear_active_tasks(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Aktif çalışan task'ları iptal et (Admin only)"""
    try:
        logger.warning(f"Admin {current_user.email} aktif task'ları iptal ediyor")
        
        # Redis'ten aktif task metadata'larını temizle
        from services.redis_service import RedisService
        
        async with RedisService() as client:
            # Celery task metadata key'lerini bul
            task_meta_keys = await client.keys("celery-task-meta-*")
            
            if not task_meta_keys:
                return {
                    "success": True,
                    "message": "Aktif task bulunamadı",
                    "data": {
                        "revoked_count": 0,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            
            # Task metadata key'lerini sil
            deleted = await client.delete(*task_meta_keys)
            logger.info(f"Active task metadata cleared: {deleted} keys")
            
            return {
                "success": True,
                "message": f"{deleted} aktif task metadata temizlendi",
                "data": {
                    "revoked_count": deleted,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
    except Exception as e:
        logger.error(f"Aktif task temizleme hatası: {e}")
        return {
            "success": False,
            "message": f"Redis connection hatası - Lütfen tekrar deneyin"
        }

@router.get("/celery/status")
async def get_celery_status(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Celery worker durumunu kontrol et (Admin only) - Redis connection safe"""
    try:
        logger.info(f"Admin {current_user.email} Celery worker durumunu sorguluyor")
        
        import subprocess
        
        # Celery process'ini kontrol et
        try:
            # pgrep ile celery worker process'ini ara
            check_result = subprocess.run(
                ["pgrep", "-f", "celery.*worker"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            is_running = check_result.returncode == 0
            process_ids = check_result.stdout.strip().split('\n') if is_running else []
            
            # Redis'ten task istatistikleri al (connection pool safe)
            task_stats = {"note": "Task istatistikleri için Redis gerekiyor"}
            try:
                async with RedisService() as redis:
                    # Sadece basit sayımlar al
                    celery_keys_task = asyncio.create_task(redis.get_keys_pattern("celery-task-meta-*"))
                    celery_keys = await asyncio.wait_for(celery_keys_task, timeout=2.0)
                    task_stats = {
                        "total_tasks_in_redis": len(celery_keys) if celery_keys else 0
                    }
            except asyncio.TimeoutError:
                task_stats = {"error": "timeout"}
            except Exception as redis_error:
                task_stats = {"error": str(redis_error)}
            
            return {
                "success": True,
                "message": "Celery worker " + ("çalışıyor" if is_running else "durmuş"),
                "data": {
                    "worker_status": "running" if is_running else "stopped",
                    "process_count": len([pid for pid in process_ids if pid]),
                    "process_ids": [pid for pid in process_ids if pid],
                    "task_stats": task_stats,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Worker durum kontrolü timeout",
                "data": {"error": "timeout"}
            }
            
    except Exception as e:
        logger.error(f"Celery status hatası: {e}")
        return {
            "success": False,
            "message": "Celery durumu kontrol edilemedi",
            "data": {"error": str(e)}
        }

@router.post("/celery/start")
async def start_celery_worker(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Celery worker'ı başlat (Admin only) - Durmuşsa başlatır"""
    try:
        logger.warning(f"Admin {current_user.email} Celery worker başlatma işlemi başlatıyor")
        
        import subprocess
        import asyncio
        
        # Önce worker'ın zaten çalışıp çalışmadığını kontrol et
        check_result = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if check_result.returncode == 0:
            # Worker zaten çalışıyor
            running_pids = [pid for pid in check_result.stdout.strip().split('\n') if pid]
            logger.info(f"Celery worker zaten çalışıyor: {running_pids}")
            return {
                "success": True,
                "message": "Celery worker zaten çalışıyor",
                "data": {
                    "status": "already_running",
                    "process_ids": running_pids,
                    "timestamp": datetime.now().isoformat()
                }
            }
        
        # Worker durmuş, başlat
        logger.info("Celery worker durmuş, başlatılıyor...")
        
        try:
            # Celery worker'ı arka planda başlat
            start_result = subprocess.Popen(
                ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--concurrency=1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Worker'ın başlaması için bekle
            await asyncio.sleep(3)
            
            # Başladığını doğrula
            verify_result = subprocess.run(
                ["pgrep", "-f", "celery.*worker"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if verify_result.returncode == 0:
                new_pids = [pid for pid in verify_result.stdout.strip().split('\n') if pid]
                logger.info(f"Celery worker başarıyla başlatıldı: {new_pids}")
                return {
                    "success": True,
                    "message": "Celery worker başarıyla başlatıldı",
                    "data": {
                        "status": "started",
                        "process_ids": new_pids,
                        "timestamp": datetime.now().isoformat(),
                        "note": "Worker durumunu /api/admin/celery/status endpoint'inden kontrol edebilirsiniz"
                    }
                }
            else:
                logger.error("Celery worker başlatıldı ama doğrulanamadı")
                return {
                    "success": False,
                    "message": "Worker başlatıldı ama doğrulanamadı",
                    "data": {"status": "verification_failed"}
                }
                
        except Exception as start_error:
            logger.error(f"Worker başlatma hatası: {start_error}")
            return {
                "success": False,
                "message": f"Worker başlatılamadı: {str(start_error)}",
                "data": {"error": str(start_error)}
            }
            
    except Exception as e:
        logger.error(f"Celery worker start hatası: {e}")
        return {
            "success": False,
            "message": "Worker başlatma işlemi başarısız",
            "data": {"error": str(e)}
        }

@router.post("/celery/restart")
async def restart_celery_worker(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Celery worker'ı yeniden başlat (Admin only) - Durdur ve başlat"""
    try:
        logger.warning(f"Admin {current_user.email} Celery worker yeniden başlatma işlemi başlatıyor")
        
        import subprocess
        import asyncio
        
        restart_info = {
            "stopped": False,
            "started": False,
            "old_pids": [],
            "new_pids": []
        }
        
        # 1. Mevcut worker'ları kontrol et
        check_result = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if check_result.returncode == 0:
            restart_info["old_pids"] = [pid for pid in check_result.stdout.strip().split('\n') if pid]
            logger.info(f"Mevcut worker'lar bulundu: {restart_info['old_pids']}")
            
            # 2. Worker'ları durdur
            try:
                kill_result = subprocess.run(
                    ["pkill", "-f", "celery.*worker"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                logger.info(f"Worker'lar durduruldu. Return code: {kill_result.returncode}")
                restart_info["stopped"] = True
                
                # Durması için bekle
                await asyncio.sleep(2)
                
            except Exception as kill_error:
                logger.error(f"Worker durdurma hatası: {kill_error}")
                return {
                    "success": False,
                    "message": f"Worker durdurulamadı: {str(kill_error)}",
                    "data": restart_info
                }
        else:
            logger.info("Hiç worker çalışmıyor, sadece başlatılacak")
            restart_info["stopped"] = True
        
        # 3. Worker'ı başlat
        try:
            start_result = subprocess.Popen(
                ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--concurrency=1"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            
            # Başlaması için bekle
            await asyncio.sleep(3)
            
            # Başladığını doğrula
            verify_result = subprocess.run(
                ["pgrep", "-f", "celery.*worker"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if verify_result.returncode == 0:
                restart_info["new_pids"] = [pid for pid in verify_result.stdout.strip().split('\n') if pid]
                restart_info["started"] = True
                logger.info(f"Worker yeniden başlatıldı: {restart_info['new_pids']}")
                
                return {
                    "success": True,
                    "message": "Celery worker başarıyla yeniden başlatıldı",
                    "data": {
                        **restart_info,
                        "timestamp": datetime.now().isoformat(),
                        "note": "Worker durumunu /api/admin/celery/status endpoint'inden kontrol edebilirsiniz"
                    }
                }
            else:
                logger.error("Worker başlatıldı ama doğrulanamadı")
                return {
                    "success": False,
                    "message": "Worker başlatıldı ama doğrulanamadı",
                    "data": restart_info
                }
                
        except Exception as start_error:
            logger.error(f"Worker başlatma hatası: {start_error}")
            return {
                "success": False,
                "message": f"Worker başlatılamadı: {str(start_error)}",
                "data": restart_info
            }
            
    except Exception as e:
        logger.error(f"Celery worker restart hatası: {e}")
        return {
            "success": False,
            "message": "Worker yeniden başlatma işlemi başarısız",
            "data": {"error": str(e)}
        }

@router.delete("/celery/worker/{pid}")
async def kill_celery_worker_by_pid(
    pid: int,
    force: bool = False,
    current_user: UserResponse = Depends(get_admin_user)
):
    """Belirli bir PID'e sahip Celery worker'ı kapat (Admin only)
    
    Args:
        pid: Process ID
        force: True ise SIGKILL (kill -9), False ise SIGTERM (kill -15) kullanır
    """
    try:
        logger.warning(f"Admin {current_user.email} PID {pid} ile Celery worker kapatma işlemi başlatıyor (force={force})")
        
        import subprocess
        import signal
        import os
        
        # Önce PID'in gerçekten celery worker'a ait olup olmadığını kontrol et
        try:
            check_cmd = f"ps -p {pid} -o cmd="
            check_result = subprocess.run(
                check_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if check_result.returncode != 0:
                return {
                    "success": False,
                    "message": f"PID {pid} bulunamadı",
                    "data": {"error": "process_not_found"}
                }
            
            process_cmd = check_result.stdout.strip()
            
            # Celery worker olup olmadığını kontrol et
            if "celery" not in process_cmd.lower() or "worker" not in process_cmd.lower():
                logger.warning(f"PID {pid} bir Celery worker değil: {process_cmd}")
                return {
                    "success": False,
                    "message": f"PID {pid} bir Celery worker değil",
                    "data": {
                        "error": "not_celery_worker",
                        "process_command": process_cmd
                    }
                }
            
            logger.info(f"PID {pid} doğrulandı: {process_cmd}")
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Process kontrolü timeout",
                "data": {"error": "timeout"}
            }
        except Exception as check_error:
            logger.error(f"PID kontrol hatası: {check_error}")
            return {
                "success": False,
                "message": "Process kontrol edilemedi",
                "data": {"error": str(check_error)}
            }
        
        # Worker'ı kapat
        try:
            if force:
                # SIGKILL (kill -9) - Force kill
                os.kill(pid, signal.SIGKILL)
                kill_method = "SIGKILL (force kill)"
            else:
                # SIGTERM (kill -15) - Graceful shutdown
                os.kill(pid, signal.SIGTERM)
                kill_method = "SIGTERM (graceful shutdown)"
            
            logger.info(f"PID {pid} kapatıldı ({kill_method})")
            
            return {
                "success": True,
                "message": f"Celery worker (PID {pid}) başarıyla kapatıldı",
                "data": {
                    "pid": pid,
                    "kill_method": kill_method,
                    "process_command": process_cmd,
                    "timestamp": datetime.now().isoformat(),
                    "note": "Workflow otomatik olarak yeni worker başlatacak. Durumu /api/admin/celery/status'dan kontrol edebilirsiniz."
                }
            }
            
        except ProcessLookupError:
            return {
                "success": False,
                "message": f"PID {pid} bulunamadı veya zaten kapatılmış",
                "data": {"error": "process_already_dead"}
            }
        except PermissionError:
            return {
                "success": False,
                "message": f"PID {pid} kapatma izni yok",
                "data": {"error": "permission_denied"}
            }
        except Exception as kill_error:
            logger.error(f"Worker kapatma hatası: {kill_error}")
            return {
                "success": False,
                "message": f"Worker kapatılamadı: {str(kill_error)}",
                "data": {"error": str(kill_error)}
            }
            
    except Exception as e:
        logger.error(f"Celery worker PID kill hatası: {e}")
        return {
            "success": False,
            "message": "Worker kapatma işlemi başarısız",
            "data": {"error": str(e)}
        }

@router.get("/redis/connections")
async def get_redis_connections(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Redis connection detaylarını getir (Admin only)"""
    try:
        logger.info(f"Admin {current_user.email} Redis connection bilgilerini sorguluyor")
        
        redis_service = RedisService()
        connection_info = {}
        
        try:
            # Temel connection test
            ping_task = asyncio.create_task(redis_service.ping())
            await asyncio.wait_for(ping_task, timeout=5.0)
            connection_info["connection_status"] = "healthy"
            
            # Detaylı Redis info
            info_task = asyncio.create_task(redis_service.get_info())
            redis_info = await asyncio.wait_for(info_task, timeout=5.0)
            
            # Connection pool bilgileri - global pool kullan
            from services.redis_service import get_redis_pool
            connection_pool = await get_redis_pool()
            
            logger.info(f"Redis info keys: {list(redis_info.keys())}")
            logger.info(f"Redis version: {redis_info.get('redis_version', 'N/A')}")
            
            connection_info.update({
                "server_info": {
                    "redis_version": redis_info.get("redis_version", "N/A"),
                    "uptime_seconds": redis_info.get("uptime_in_seconds", 0),
                    "uptime_days": round(redis_info.get("uptime_in_seconds", 0) / 86400, 2)
                },
                "memory_info": {
                    "used_memory_human": redis_info.get("used_memory_human", "N/A"),
                    "used_memory_peak_human": redis_info.get("used_memory_peak_human", "N/A"),
                    "used_memory_rss_human": redis_info.get("used_memory_rss_human", "N/A"),
                    "maxmemory_human": redis_info.get("maxmemory_human", "N/A")
                },
                "connection_info": {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "client_recent_max_input_buffer": redis_info.get("client_recent_max_input_buffer", 0),
                    "client_recent_max_output_buffer": redis_info.get("client_recent_max_output_buffer", 0),
                    "blocked_clients": redis_info.get("blocked_clients", 0)
                },
                "network_info": {
                    "total_connections_received": redis_info.get("total_connections_received", 0),
                    "total_commands_processed": redis_info.get("total_commands_processed", 0),
                    "rejected_connections": redis_info.get("rejected_connections", 0),
                    "sync_full": redis_info.get("sync_full", 0),
                    "sync_partial_ok": redis_info.get("sync_partial_ok", 0)
                },
                "keyspace_info": {
                    "total_keys": 0,
                    "databases": {}
                }
            })
            
            # Keyspace bilgileri
            for key, value in redis_info.items():
                if key.startswith("db"):
                    # db0 bilgisi farklı formatlarda gelebilir
                    db_info = {}
                    try:
                        if isinstance(value, dict):
                            # Eğer value zaten dict ise direkt kullan
                            db_info = value
                        elif isinstance(value, str):
                            # db0:keys=123,expires=45,avg_ttl=678 formatındaki string'i parse et
                            for part in value.split(","):
                                if "=" in part:
                                    k, v = part.split("=", 1)
                                    db_info[k] = int(v) if v.isdigit() else v
                        else:
                            # Diğer durumlar için raw değer
                            db_info = {"raw_value": value, "type": str(type(value))}
                        
                        connection_info["keyspace_info"]["databases"][key] = db_info
                        # keys alanı varsa toplama ekle
                        keys_count = db_info.get("keys", 0)
                        if isinstance(keys_count, (int, str)) and str(keys_count).isdigit():
                            connection_info["keyspace_info"]["total_keys"] += int(keys_count)
                            
                    except Exception as parse_error:
                        logger.error(f"Keyspace parsing error for {key}: {parse_error}")
                        connection_info["keyspace_info"]["databases"][key] = {
                            "error": str(parse_error), 
                            "raw_value": value,
                            "value_type": str(type(value))
                        }
            
            # Connection pool detayları
            try:
                logger.info("Getting connection pool info...")
                connection_info["pool_info"] = {
                    "created_connections": getattr(connection_pool, "_created_connections", "N/A"),
                    "max_connections": getattr(connection_pool, "max_connections", "N/A"),
                    "available_connections": len(getattr(connection_pool, "_available_connections", []))
                }
                logger.info(f"Pool info: {connection_info['pool_info']}")
            except Exception as pool_error:
                logger.error(f"Pool info error: {pool_error}")
                connection_info["pool_info"] = {
                    "error": "Connection pool bilgileri alınamadı"
                }
            
            # Celery ile ilgili key'leri say
            try:
                logger.info("Getting Celery keys...")
                celery_tasks = asyncio.create_task(redis_service.get_keys_pattern("celery-task-meta-*"))
                celery_keys = await asyncio.wait_for(celery_tasks, timeout=3.0)
                
                logger.info("Getting Kombu keys...")
                kombu_tasks = asyncio.create_task(redis_service.get_keys_pattern("_kombu.*"))
                kombu_keys = await asyncio.wait_for(kombu_tasks, timeout=3.0)
                
                logger.info("Getting progress keys...")
                progress_tasks = asyncio.create_task(redis_service.get_keys_pattern("task_progress:*"))
                progress_keys = await asyncio.wait_for(progress_tasks, timeout=3.0)
                
                connection_info["application_keys"] = {
                    "celery_task_keys": len(celery_keys) if celery_keys else 0,
                    "kombu_keys": len(kombu_keys) if kombu_keys else 0,
                    "progress_keys": len(progress_keys) if progress_keys else 0
                }
                logger.info(f"Application keys: {connection_info['application_keys']}")
                
            except Exception as keys_error:
                logger.error(f"Keys gathering error: {keys_error}")
                connection_info["application_keys"] = {
                    "error": str(keys_error)
                }
            
            # Connection pool automatically manages connections
            logger.info(f"Final connection_info keys: {list(connection_info.keys())}")
            logger.info(f"Connection status: {connection_info.get('connection_status', 'NOT SET')}")
            
        except Exception as redis_error:
            logger.error(f"Redis connection info error: {redis_error}")
            connection_info = {
                "connection_status": "error",
                "error": str(redis_error),
                "timestamp": datetime.now().isoformat()
            }
            # Connection pool automatically manages connections
        
        return {
            "success": connection_info.get("connection_status") == "healthy",
            "message": "Redis connection bilgileri",
            "data": connection_info
        }
        
    except Exception as e:
        logger.error(f"Redis connection bilgileri alma hatası: {e}")
        return {
            "success": False,
            "message": f"Redis connection bilgileri alınamadı: {str(e)}"
        }


@router.get("/redis/connection-details")
async def get_redis_connection_details(
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Redis connection detaylarını ve kaynaklarını göster (Admin only)
    
    26/30 connection kullanılıyorsa, bu endpoint bunların nereden geldiğini gösterir:
    - FastAPI RedisService Pool
    - Celery Worker(s)
    - Celery Backend connections
    """
    try:
        logger.info(f"Admin {current_user.email} Redis connection detaylarını sorguluyor")
        
        redis_service = RedisService()
        
        # Temel bilgiler
        async with redis_service as client:
            info = await client.info()
            total_connections = info.get("connected_clients", 0)
        
        # Celery worker sayısı
        import subprocess
        celery_processes = subprocess.run(
            ["pgrep", "-f", "celery.*worker"],
            capture_output=True,
            text=True
        )
        celery_worker_count = len(celery_processes.stdout.strip().split('\n')) if celery_processes.stdout.strip() else 0
        
        # Connection pool bilgisi
        from services.redis_service import get_redis_pool
        connection_pool = await get_redis_pool()
        pool_max = getattr(connection_pool, "max_connections", 20)
        pool_created = getattr(connection_pool, "_created_connections", 0)
        
        # Connection dağılımı tahmini
        estimated_breakdown = {
            "fastapi_pool": {
                "max_connections": pool_max,
                "created_connections": pool_created,
                "description": "FastAPI RedisService global connection pool"
            },
            "celery_workers": {
                "worker_count": celery_worker_count,
                "estimated_connections_per_worker": 3,  # broker + backend + control
                "total_estimated": celery_worker_count * 3,
                "description": "Celery worker Redis broker/backend connections"
            },
            "other": {
                "estimated": max(0, total_connections - pool_created - (celery_worker_count * 3)),
                "description": "Diğer client'lar veya geçici bağlantılar"
            }
        }
        
        # Öneriler
        recommendations = []
        
        if total_connections > 25:
            recommendations.append({
                "severity": "warning",
                "message": f"Redis Cloud Free Plan limiti (30) dolmak üzere! ({total_connections}/30)",
                "action": "Connection'ları temizlemek için POST /api/admin/redis/cleanup-connections endpoint'ini kullanın"
            })
        
        if celery_worker_count > 2:
            recommendations.append({
                "severity": "info",
                "message": f"Çok fazla Celery worker çalışıyor ({celery_worker_count} adet)",
                "action": "Worker sayısını azaltmayı düşünün (her worker ~3 connection kullanır)"
            })
        
        if pool_created > 15:
            recommendations.append({
                "severity": "info",
                "message": f"FastAPI pool çok fazla connection oluşturmuş ({pool_created}/{pool_max})",
                "action": "Yüksek trafik durumu. Normal koşullarda server restart ile temizlenebilir."
            })
        
        return {
            "success": True,
            "message": "Redis connection detayları",
            "data": {
                "summary": {
                    "total_connections": total_connections,
                    "max_allowed": 30,
                    "usage_percentage": round((total_connections / 30) * 100, 1),
                    "available": 30 - total_connections
                },
                "breakdown": estimated_breakdown,
                "recommendations": recommendations,
                "timestamp": datetime.now().isoformat(),
                "note": "Tahminler yaklaşık değerlerdir. Kesin detaylar için Redis CLIENT LIST komutu kullanılabilir."
            }
        }
        
    except Exception as e:
        logger.error(f"Redis connection detayları hatası: {e}")
        return {
            "success": False,
            "message": f"Connection detayları alınamadı: {str(e)}"
        }

@router.post("/redis/cleanup-connections")
async def cleanup_redis_connections(
    restart_celery: bool = True,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Redis connection'ları temizle (Admin only)
    
    NOT: Bu işlem aktif task'ları etkileyebilir!
    
    Args:
        restart_celery: Celery worker'ları restart etsin mi? (default: True)
    
    Connection Kaynakları:
    - FastAPI RedisService Pool: max 20 connection
    - Celery Worker(s): Her worker ~3-5 connection (broker + backend)
    
    Temizleme Stratejisi:
    1. Celery worker restart → Celery Redis connection'larını temizler
    2. FastAPI server manuel restart → RedisService pool'u temizler
    """
    try:
        logger.warning(f"Admin {current_user.email} Redis connection cleanup başlatıyor (restart_celery={restart_celery})")
        
        cleanup_results = {
            "celery_restarted": False,
            "connections_before": 0,
            "connections_after": 0,
            "action_taken": []
        }
        
        # Önce mevcut connection sayısını al
        try:
            redis_service = RedisService()
            async with redis_service as client:
                info = await client.info()
                cleanup_results["connections_before"] = info.get("connected_clients", 0)
        except Exception as info_error:
            logger.error(f"Connection info alınamadı: {info_error}")
        
        # 1. Celery worker'ları restart et
        if restart_celery:
            import subprocess
            import asyncio
            
            try:
                # Celery worker'ları durdur
                kill_result = subprocess.run(
                    ["pkill", "-f", "celery.*worker"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                logger.info(f"Celery worker'lar durduruldu")
                
                # Durması için bekle
                await asyncio.sleep(2)
                
                # Yeni worker başlat
                start_result = subprocess.Popen(
                    ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--concurrency=1"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
                
                # Başlaması için bekle
                await asyncio.sleep(3)
                
                cleanup_results["celery_restarted"] = True
                cleanup_results["action_taken"].append("Celery worker restart edildi")
                logger.info("Celery worker yeniden başlatıldı")
                
            except Exception as celery_error:
                logger.error(f"Celery restart hatası: {celery_error}")
                cleanup_results["action_taken"].append(f"Celery restart başarısız: {str(celery_error)}")
        
        # Sonra güncel connection sayısını al
        try:
            async with redis_service as client:
                info = await client.info()
                cleanup_results["connections_after"] = info.get("connected_clients", 0)
        except Exception as info_error:
            logger.error(f"Connection info alınamadı: {info_error}")
        
        # Temizlik önerisi
        recommendations = []
        
        if cleanup_results["connections_after"] > 20:
            recommendations.append({
                "issue": "Hala çok fazla connection var",
                "current": cleanup_results["connections_after"],
                "recommendation": "FastAPI server'ı restart etmeyi düşünün: POST /api/admin/system/restart (dikkat: tüm aktif istekler kesintiye uğrayacak)"
            })
        
        if not restart_celery:
            recommendations.append({
                "issue": "Celery worker restart edilmedi",
                "recommendation": "Celery connection'larını temizlemek için restart_celery=true parametresini kullanın"
            })
        
        cleanup_results["recommendations"] = recommendations
        cleanup_results["freed_connections"] = cleanup_results["connections_before"] - cleanup_results["connections_after"]
        
        logger.warning(
            f"Redis cleanup tamamlandı - Önce: {cleanup_results['connections_before']}, "
            f"Sonra: {cleanup_results['connections_after']}, "
            f"Temizlenen: {cleanup_results['freed_connections']}"
        )
        
        return {
            "success": True,
            "message": f"{cleanup_results['freed_connections']} connection temizlendi",
            "data": {
                **cleanup_results,
                "timestamp": datetime.now().isoformat(),
                "note": "Connection'lar otomatik olarak yeniden oluşturulacak. Sorun devam ederse FastAPI server restart gerekebilir."
            }
        }
        
    except Exception as e:
        logger.error(f"Redis cleanup hatası: {e}")
        return {
            "success": False,
            "message": f"Connection cleanup başarısız: {str(e)}"
        }

@router.get("/purchases")
async def get_all_purchases(
    current_admin: UserResponse = Depends(get_admin_user)
):
    """
    Tüm kullanıcıların satın alım geçmişini görüntüle (Admin Only)
    
    Admin kullanıcılar on_siparis tablosundaki tüm kayıtları görüntüleyebilir.
    
    Args:
        current_admin: Current authenticated admin user
    
    Returns:
        Tüm satın alım kayıtları
    """
    try:
        # Tüm on_siparis tablosunu çek - TÜM KOLONLAR
        response = supabase_client.supabase.table('on_siparis').select('*').order('created_at', desc=True).execute()
        
        total_count = len(response.data) if response.data else 0
        
        # Debug: İlk kayıttaki tüm kolonları logla
        if response.data and len(response.data) > 0:
            first_item_keys = list(response.data[0].keys())
            logger.info(f"Admin {current_admin.id} - Tablodaki kolonlar: {first_item_keys}")
        
        logger.info(f"Admin {current_admin.id} retrieved all purchases: {total_count} items with ALL columns")
        
        return success_response(
            data={
                "purchases": response.data or [],
                "total": total_count
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving all purchases for admin {current_admin.id}: {str(e)}")
        raise AppException(
            message="Satın alım verileri alınamadı",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ADMIN_PURCHASE_HISTORY_FAILED"
        )


@router.get("/payment-settings", response_model=PaymentSettingsResponse)
async def get_payment_settings_admin(
    current_admin: UserResponse = Depends(get_admin_user)
):
    """
    Ödeme ayarlarını görüntüle (Admin Only)
    
    İyzico ödeme modunu (sandbox/production) ve ödeme sisteminin
    aktif/pasif durumunu döndürür.
    
    Args:
        current_admin: Current authenticated admin user
    
    Returns:
        Ödeme modu ve aktiflik durumu
    """
    try:
        # Supabase'den payment_settings tablosunu çek
        response = supabase_client.supabase.table('payment_settings').select('*').limit(1).execute()
        
        if not response.data or len(response.data) == 0:
            logger.warning("Payment settings not found in database")
            raise AppException(
                message="Ödeme ayarları bulunamadı",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="PAYMENT_SETTINGS_NOT_FOUND"
            )
        
        settings = response.data[0]
        
        logger.info(f"Admin {current_admin.id} retrieved payment settings: mode={settings['payment_mode']}, active={settings['is_active']}")
        
        return PaymentSettingsResponse(
            success=True,
            payment_mode=settings['payment_mode'],
            is_active=settings['is_active'],
            description=settings.get('description')
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving payment settings for admin {current_admin.id}: {str(e)}")
        raise AppException(
            message="Ödeme ayarları alınamadı",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ADMIN_PAYMENT_SETTINGS_FAILED"
        )


@router.put("/payment-settings", response_model=PaymentSettingsResponse)
async def update_payment_settings(
    settings_update: PaymentSettingsUpdate,
    current_admin: UserResponse = Depends(get_admin_user)
):
    """
    Ödeme ayarlarını güncelle (Admin Only)
    
    İyzico ödeme modunu (sandbox/production) ve ödeme sisteminin
    aktif/pasif durumunu günceller.
    
    Args:
        settings_update: Güncellenecek ayarlar
        current_admin: Current authenticated admin user
    
    Returns:
        Güncellenmiş ödeme ayarları
    """
    try:
        # En az bir değer gönderilmiş mi kontrol et
        if not any([settings_update.payment_mode, settings_update.is_active is not None, settings_update.description]):
            raise AppException(
                message="En az bir alan güncellenmelidir",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="NO_UPDATE_DATA"
            )
        
        # Mevcut ayarları al
        current_settings = supabase_client.supabase.table('payment_settings').select('*').limit(1).execute()
        
        if not current_settings.data or len(current_settings.data) == 0:
            raise AppException(
                message="Ödeme ayarları bulunamadı",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="PAYMENT_SETTINGS_NOT_FOUND"
            )
        
        current_id = current_settings.data[0]['id']
        
        # Güncellenecek veriyi hazırla
        update_data = {}
        if settings_update.payment_mode:
            update_data['payment_mode'] = settings_update.payment_mode
        if settings_update.is_active is not None:
            update_data['is_active'] = settings_update.is_active
        if settings_update.description is not None:
            update_data['description'] = settings_update.description
        
        # Güncelleme yap
        response = supabase_client.supabase.table('payment_settings').update(update_data).eq('id', current_id).execute()
        
        if not response.data or len(response.data) == 0:
            raise AppException(
                message="Ödeme ayarları güncellenemedi",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code="UPDATE_FAILED"
            )
        
        updated_settings = response.data[0]
        
        logger.info(f"Admin {current_admin.id} updated payment settings: mode={updated_settings['payment_mode']}, active={updated_settings['is_active']}")
        
        return PaymentSettingsResponse(
            success=True,
            payment_mode=updated_settings['payment_mode'],
            is_active=updated_settings['is_active'],
            description=updated_settings.get('description')
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Error updating payment settings for admin {current_admin.id}: {str(e)}")
        raise AppException(
            message="Ödeme ayarları güncellenemedi",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="ADMIN_PAYMENT_UPDATE_FAILED"
        )

@router.post("/documents/bulk-upload")
async def bulk_upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    metadata: str = Form(...),
    category: str = Form(...),
    institution: str = Form(...),
    belge_adi: str = Form(...),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Bulk upload multiple PDF documents with JSON metadata
    
    Workflow:
    1. Validate files are PDFs
    2. Parse and validate metadata JSON
    3. Match PDFs to JSON entries by filename
    4. Upload all PDFs to Bunny CDN
    5. Create Supabase metadata records
    6. Initialize Redis progress tracking
    7. Queue Celery bulk processing task
    
    Args:
        files: List of PDF files to upload
        metadata: JSON string with metadata array (title, description, keywords, output_filename for each PDF)
        category: Document category (from form)
        institution: Source institution (from form)
        belge_adi: Document name (from form)
        current_user: Current admin user
    
    Returns:
        Task ID for progress tracking and summary
    """
    try:
        logger.info(f"Bulk upload request from admin {current_user.id}: {len(files)} files")
        
        # Validate files
        if not files or len(files) == 0:
            raise AppException(
                message="No files uploaded",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="NO_FILES"
            )
        
        # Validate all files are PDFs
        for file in files:
            if not file.filename or not file.filename.lower().endswith('.pdf'):
                raise AppException(
                    message=f"File {file.filename} is not a PDF",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="INVALID_FILE_TYPE"
                )
        
        # Parse metadata JSON
        try:
            metadata_obj = json.loads(metadata)
            if "pdf_sections" not in metadata_obj:
                raise ValueError("JSON must contain 'pdf_sections' array")
            
            pdf_sections = metadata_obj["pdf_sections"]
            
            if not isinstance(pdf_sections, list):
                raise ValueError("pdf_sections must be an array")
            
        except json.JSONDecodeError as e:
            raise AppException(
                message="Invalid JSON metadata format",
                detail=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_JSON"
            )
        except ValueError as e:
            raise AppException(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="INVALID_METADATA_STRUCTURE"
            )
        
        # Validate counts match
        if len(files) != len(pdf_sections):
            raise AppException(
                message=f"File count ({len(files)}) does not match metadata entries ({len(pdf_sections)})",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="COUNT_MISMATCH"
            )
        
        # Match files to metadata by filename
        file_metadata_map = {}
        unmatched_files = []
        
        for file in files:
            matched = False
            for section in pdf_sections:
                output_filename = section.get("output_filename", "")
                
                # Case-insensitive filename match
                if file.filename.lower() == output_filename.lower():
                    file_metadata_map[file.filename] = section
                    matched = True
                    break
            
            if not matched:
                unmatched_files.append(file.filename)
        
        if unmatched_files:
            raise AppException(
                message=f"Files without matching metadata: {', '.join(unmatched_files)}",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="UNMATCHED_FILES"
            )
        
        logger.info(f"Validation passed: {len(files)} files matched with metadata")
        
        # Initialize services
        storage_service = StorageService()
        redis_service = RedisService()
        
        # Upload PDFs and create database records
        uploaded_documents = []
        
        for file in files:
            try:
                # Read file content
                file_content = await file.read()
                
                # Upload to Bunny CDN
                logger.info(f"Uploading {file.filename} to CDN")
                file_url = await storage_service.upload_file(
                    file_content=file_content,
                    filename=file.filename,
                    content_type="application/pdf"
                )
                
                # Get metadata for this file
                section_metadata = file_metadata_map[file.filename]
                
                # Prepare document data
                keywords_list = []
                if section_metadata.get("keywords"):
                    keywords_list = [k.strip() for k in section_metadata["keywords"].split(",")]
                
                document_data = {
                    'title': section_metadata.get("title", file.filename),
                    'belge_adi': belge_adi,
                    'filename': file.filename,
                    'file_url': file_url,
                    'file_size': len(file_content),
                    'content_preview': section_metadata.get("description", "")[:500],
                    'uploaded_by': str(current_user.id),
                    'status': 'pending',
                    'institution': institution,
                    'metadata': {
                        'belge_adi': belge_adi,
                        'category': category,
                        'description': section_metadata.get("description"),
                        'keywords': keywords_list,
                        'source_institution': institution,
                        'start_page': section_metadata.get("start_page"),
                        'end_page': section_metadata.get("end_page"),
                        'original_filename': file.filename,
                        'section_title': section_metadata.get("title"),
                        'bulk_upload': True
                    }
                }
                
                # Save to Supabase
                logger.info(f"Saving metadata for {file.filename}")
                document_id = await supabase_client.create_document(document_data)
                
                uploaded_documents.append({
                    "filename": file.filename,
                    "document_id": str(document_id),
                    "file_url": file_url,
                    "metadata": section_metadata
                })
                
                logger.info(f"Document {file.filename} uploaded successfully: {document_id}")
                
            except Exception as upload_error:
                logger.error(f"Failed to upload {file.filename}: {str(upload_error)}")
                raise AppException(
                    message=f"Failed to upload {file.filename}",
                    detail=str(upload_error),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    error_code="UPLOAD_FAILED"
                )
        
        # Generate batch ID for grouping tasks
        batch_id = str(uuid.uuid4())
        
        logger.info(f"Created batch {batch_id} for {len(uploaded_documents)} documents")
        
        # Initialize batch progress tracking
        from services.progress_service import progress_service
        await progress_service.initialize_batch_progress(
            batch_id=batch_id,
            total_files=len(uploaded_documents),
            admin_id=str(current_user.id)
        )
        
        # Queue individual Celery tasks for each PDF
        from tasks.document_processor import process_document_task
        
        task_list = []
        
        for doc in uploaded_documents:
            try:
                # Create individual task for this document
                celery_task = process_document_task.delay(doc["document_id"])
                task_id = celery_task.id
                
                # Initialize progress tracking for this task
                await progress_service.initialize_task_progress(
                    task_id=task_id,
                    document_id=doc["document_id"],
                    document_title=doc["metadata"].get("title", doc["filename"]),
                    batch_id=batch_id,
                    filename=doc["filename"]
                )
                
                task_list.append({
                    "task_id": task_id,
                    "document_id": doc["document_id"],
                    "filename": doc["filename"],
                    "status": "queued"
                })
                
                logger.info(f"Queued task {task_id} for document {doc['document_id']}")
                
            except Exception as task_error:
                logger.error(f"Failed to queue task for {doc['filename']}: {str(task_error)}")
                
                # Create synthetic task_id for failed enqueue and track it
                failed_task_id = f"failed_{uuid.uuid4()}"
                
                # Initialize progress with failed status to maintain batch consistency
                await progress_service.initialize_task_progress(
                    task_id=failed_task_id,
                    document_id=doc["document_id"],
                    document_title=doc["metadata"].get("title", doc["filename"]),
                    batch_id=batch_id,
                    filename=doc["filename"]
                )
                
                # Mark as failed immediately
                await progress_service.mark_task_failed(
                    task_id=failed_task_id,
                    error_message=f"Failed to enqueue: {str(task_error)}"
                )
                
                task_list.append({
                    "task_id": failed_task_id,
                    "document_id": doc["document_id"],
                    "filename": doc["filename"],
                    "status": "failed",
                    "error": str(task_error)
                })
        
        logger.info(f"Batch {batch_id}: {len(task_list)} tasks queued")
        
        return success_response(
            data={
                "batch_id": batch_id,
                "total_files": len(uploaded_documents),
                "tasks": task_list
            },
            message=f"Bulk upload queued: {len(uploaded_documents)} documents"
        )
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Bulk upload failed: {str(e)}")
        raise AppException(
            message="Bulk upload failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="BULK_UPLOAD_FAILED"
        )


@router.post("/documents/bulk-upload-yargitay")
async def bulk_upload_yargitay(
    kurum_id: str = Form(...),
    category: str = Form(...),
    institution: str = Form(...),
    belge_adi: str = Form(...),
    daire: str = Form(...),
    esasNo: str = Form(...),
    kararNo: str = Form(...),
    kararTarihi: str = Form(...),
    etiketler: str = Form(...),
    icerik: str = Form(...),
    icerik_text: str = Form(...),
    sayfa_sayisi: int = Form(...),
    dosya_boyutu_mb: float = Form(...),
    pdf_url: str = Form(...),
    url_slug: str = Form(...),
    mode: str = Form(...),
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Yargitay bulk upload with HTML content (Admin only)
    """
    try:
        if not icerik:
            raise AppException(
                message="icerik alanı boş olamaz",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="YARGITAY_EMPTY_CONTENT"
            )

        karar_tarihi = None
        try:
            karar_tarihi = datetime.strptime(kararTarihi, "%d.%m.%Y").date().isoformat()
        except ValueError:
            try:
                karar_tarihi = datetime.strptime(kararTarihi, "%Y-%m-%d").date().isoformat()
            except ValueError as e:
                raise AppException(
                    message="kararTarihi formatı geçersiz",
                    detail=str(e),
                    status_code=status.HTTP_400_BAD_REQUEST,
                    error_code="YARGITAY_INVALID_DATE"
                )

        mongo_id = None
        if mode in ["t", "p"]:
            mongo_payload = {
                "pdf_adi": belge_adi,
                "kurum_id": kurum_id,
                "belge_turu": category,
                "belge_durumu": "Yürürlükte",
                "url_slug": url_slug,
                "status": "aktif",
                "sayfa_sayisi": sayfa_sayisi,
                "dosya_boyutu_mb": dosya_boyutu_mb,
                "olusturulma_tarihi": datetime.utcnow(),
                "pdf_url": pdf_url,
                "daire": daire,
                "esasNo": esasNo,
                "kararNo": kararNo,
                "kararTarihi": kararTarihi,
                "etiketler": etiketler,
            "icerik": icerik,
            "icerik_text": icerik_text
            }

            logger.info("\033[94m[YARGITAY] MongoDB kayıt başladı\033[0m")
            mongo_id = await yargitay_mongo_service.insert_metadata(mongo_payload)
            logger.info(f"\033[92m[YARGITAY] MongoDB kayıt bitti - mongo_id={mongo_id}\033[0m")
        else:
            logger.info("\033[93m[YARGITAY] MongoDB kayıt atlandı (mode=m)\033[0m")

        document_id = None
        celery_task = None
        if mode in ["t", "m"]:
            supabase_payload = {
                "kurum_id": kurum_id,
                "category": category,
                "institution": institution,
                "belge_adi": belge_adi,
                "daire": daire,
                "esas_no": esasNo,
                "karar_no": kararNo,
                "karar_tarihi": karar_tarihi,
                "etiketler": etiketler,
                "icerik_html": icerik,
                "icerik_text": icerik_text,
                "pdf_url": pdf_url,
                "url_slug": url_slug,
                "status": "aktif",
                "sayfa_sayisi": sayfa_sayisi,
                "dosya_boyutu_mb": dosya_boyutu_mb,
                "belge_durumu": "Yürürlükte"
            }

            logger.info(
                f"\033[94m[YARGITAY] Supabase kayıt başladı - sayfa_sayisi={supabase_payload.get('sayfa_sayisi')}, "
                f"dosya_boyutu_mb={supabase_payload.get('dosya_boyutu_mb')}\033[0m"
            )
            document_id = await supabase_client.create_yargitay_document(supabase_payload)
            logger.info("\033[92m[YARGITAY] Supabase kayıt bitti\033[0m")

            logger.info(f"\033[94m[YARGITAY] Celery enqueue başladı - document_id={document_id}\033[0m")
            celery_task = process_yargitay_document_task.delay(str(document_id))
            logger.info(f"\033[92m[YARGITAY] Celery enqueue bitti - task_id={celery_task.id}\033[0m")
        else:
            logger.info("\033[93m[YARGITAY] Supabase/Celery atlandı (mode=p)\033[0m")

        return success_response(
            data={
                "document_id": str(document_id) if document_id else None,
                "task_id": celery_task.id if celery_task else None,
                "mongo_id": mongo_id
            },
            message="Yargitay bulk upload queued"
        )

    except AppException:
        raise
    except Exception as e:
        logger.error(f"Yargitay bulk upload failed: {str(e)}")
        raise AppException(
            message="Yargitay bulk upload failed",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="YARGITAY_BULK_UPLOAD_FAILED"
        )

@router.get("/documents/bulk-upload/batch/{batch_id}/progress")
async def get_batch_progress(
    batch_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Get progress for all tasks in a batch upload
    
    Args:
        batch_id: Batch ID from bulk upload
        current_user: Current admin user
    
    Returns:
        Batch progress with all individual task statuses
    """
    try:
        from services.progress_service import progress_service
        
        batch_data = await progress_service.get_batch_progress(batch_id)
        
        if not batch_data:
            raise AppException(
                message="Batch not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="BATCH_NOT_FOUND"
            )
        
        return success_response(data=batch_data)
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch progress: {str(e)}")
        raise AppException(
            message="Failed to get batch progress",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="BATCH_PROGRESS_FAILED"
        )

@router.get("/documents/bulk-upload/progress/{task_id}")
async def get_task_progress(
    task_id: str,
    current_user: UserResponse = Depends(get_admin_user)
):
    """
    Get progress status for a single task
    
    Args:
        task_id: Individual task ID
        current_user: Current admin user
    
    Returns:
        Task progress data
    """
    try:
        from services.progress_service import progress_service
        
        task_data = await progress_service.get_task_progress(task_id)
        
        if not task_data:
            raise AppException(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="TASK_NOT_FOUND"
            )
        
        return success_response(data=task_data)
        
    except AppException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task progress: {str(e)}")
        raise AppException(
            message="Failed to get task progress",
            detail=str(e),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="TASK_PROGRESS_FAILED"
        )
