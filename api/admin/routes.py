"""
Admin routes for document management and system administration
Only accessible by users with 'admin' role
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import logging
import asyncio
from datetime import datetime

from core.database import get_db
from api.dependencies import get_admin_user
from models.schemas import (
    UserResponse, DocumentResponse, DocumentCreate, 
    DocumentUpdate, DocumentListResponse, UploadResponse,
    AdminUserUpdate, AdminUserResponse, AdminUserListResponse,
    UserCreditUpdate, UserBanRequest
)
from models.supabase_client import supabase_client
from services.storage_service import StorageService
from services.redis_service import RedisService
from tasks.document_processor import process_document_task
from utils.response import success_response, error_response
from utils.exceptions import AppException

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
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
            'filename': filename,
            'file_url': file_url,
            'file_size': len(file_content),
            'content_preview': f"{title} - {description or ''}"[:500],
            'uploaded_by': str(current_user.id),
            'status': 'processing',
            'institution': source_institution or 'Belirtilmemiş',
            'metadata': {
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
    - Email service (SendGrid)
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
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    search: Optional[str] = Query(None, description="Search in title or filename"),
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
        logger.info(f"Admin listing documents - page: {page}, limit: {limit}, filters: category={category}, status={status}")
        
        # Build query
        query = supabase_client.supabase.table('mevzuat_documents').select(
            'id, title, filename, file_url, category, institution, processing_status, file_size, created_at, updated_at, uploaded_by, content_preview'
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
            
            # Close Redis connection
            await redis_service._close_client()
            
        except asyncio.TimeoutError:
            redis_status = {
                "connection": "timeout",
                "error": "Redis operations timed out"
            }
            # Close connection on timeout
            if redis_service:
                try:
                    await redis_service._close_client()
                except:
                    pass
        except Exception as redis_error:
            redis_status = {
                "connection": "error",
                "error": str(redis_error)
            }
            # Close connection on error
            if redis_service:
                try:
                    await redis_service._close_client()
                except:
                    pass
        
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
        
        from tasks.celery_app import celery_app
        
        # Tüm queue'ları purge et
        purged_count = celery_app.control.purge()
        
        logger.info(f"Celery queue purged: {purged_count} tasks removed")
        
        return {
            "success": True,
            "message": f"Celery queue temizlendi",
            "data": {
                "purged_tasks": purged_count,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Celery queue temizleme hatası: {e}")
        return {
            "success": False,
            "message": f"Celery queue temizleme başarısız: {str(e)}"
        }

@router.post("/celery/restart-worker")
async def restart_celery_worker(
    current_user: UserResponse = Depends(get_admin_user)
):
    """Celery worker'ı restart et (Admin only)"""
    try:
        logger.warning(f"Admin {current_user.email} Celery worker restart işlemi başlatıyor")
        
        import subprocess
        import asyncio
        from tasks.celery_app import celery_app
        
        # Önce worker'ın durumunu kontrol et
        inspector = celery_app.control.inspect()
        active_workers = inspector.active()
        stats = inspector.stats()
        
        worker_info = {
            "before_restart": {
                "active_workers": len(active_workers) if active_workers else 0,
                "worker_stats": stats
            }
        }
        
        # Worker'ı restart et (workflow restart)
        try:
            # Replit workflow restart komutu
            restart_result = subprocess.run(
                ["pkill", "-f", "celery.*worker"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            logger.info(f"Celery worker restart signal sent. Return code: {restart_result.returncode}")
            
            # Kısa bir bekleme
            await asyncio.sleep(2)
            
            # Restart sonrası durum kontrolü
            try:
                inspector_after = celery_app.control.inspect()
                active_workers_after = inspector_after.active()
                stats_after = inspector_after.stats()
                
                worker_info["after_restart"] = {
                    "active_workers": len(active_workers_after) if active_workers_after else 0,
                    "worker_stats": stats_after
                }
                restart_status = "success"
                
            except Exception as check_error:
                worker_info["after_restart"] = {
                    "error": "Worker durumu kontrol edilemedi",
                    "details": str(check_error)
                }
                restart_status = "partial"
                
        except subprocess.TimeoutExpired:
            restart_status = "timeout"
            worker_info["restart_error"] = "Restart işlemi timeout"
        except Exception as restart_error:
            restart_status = "error"
            worker_info["restart_error"] = str(restart_error)
        
        return {
            "success": restart_status in ["success", "partial"],
            "message": f"Celery worker restart {'başarılı' if restart_status == 'success' else 'kısmen başarılı' if restart_status == 'partial' else 'başarısız'}",
            "data": {
                "restart_status": restart_status,
                "worker_info": worker_info,
                "timestamp": datetime.now().isoformat(),
                "note": "Worker Replit workflow sistemi tarafından otomatik olarak yeniden başlatılacak"
            }
        }
        
    except Exception as e:
        logger.error(f"Celery worker restart hatası: {e}")
        return {
            "success": False,
            "message": f"Celery worker restart başarısız: {str(e)}"
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
            
            # Connection pool bilgileri  
            client = await redis_service._get_client()
            connection_pool = client.connection_pool
            
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
            
            await redis_service._close_client()
            logger.info(f"Final connection_info keys: {list(connection_info.keys())}")
            logger.info(f"Connection status: {connection_info.get('connection_status', 'NOT SET')}")
            
        except Exception as redis_error:
            logger.error(f"Redis connection info error: {redis_error}")
            connection_info = {
                "connection_status": "error",
                "error": str(redis_error),
                "timestamp": datetime.now().isoformat()
            }
            if redis_service:
                try:
                    await redis_service._close_client()
                except:
                    pass
        
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
