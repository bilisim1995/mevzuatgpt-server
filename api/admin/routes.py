"""
Admin routes for document management and system administration
Only accessible by users with 'admin' role
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import logging
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
        if not file.filename.lower().endswith('.pdf'):
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
        logger.info(f"Uploading file {file.filename} to storage")
        file_url = await storage_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            content_type="application/pdf"
        )
        
        # Prepare document data for Supabase
        keywords_list = [k.strip() for k in keywords.split(",")] if keywords else []
        
        document_data = {
            'title': title,
            'filename': file.filename,
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
                'original_filename': file.filename
            }
        }
        
        # Save document metadata to Supabase
        logger.info(f"Saving document metadata for {file.filename}")
        document_id = await supabase_client.create_document(document_data)
        
        # Trigger background processing
        logger.info(f"Triggering background processing for document {document_id}")
        process_document_task.delay(str(document_id))
        
        return success_response(
            data={
                "document_id": str(document_id),
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
        
        elasticsearch_service = ElasticsearchService()
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
            'id, title, filename, file_url, category, processing_status, file_size, created_at, updated_at, uploaded_by, content_preview'
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
        es_service = ElasticsearchService()
        
        # Get embedding count and additional vector info
        embedding_count = await embedding_service.get_embeddings_count(document_id)
        
        # Get chunk information and vector statistics
        vector_stats = await es_service.get_document_vector_stats(document_id)
        
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
                    "total_vectors": vector_stats.get("total_vectors", 0),
                    "chunk_count": vector_stats.get("unique_chunks", 0),
                    "elasticsearch_index": vector_stats.get("index_name", "mevzuat_embeddings")
                },
                "processing_metrics": {
                    "embeddings_created": embedding_count,
                    "processing_status": document.get('processing_status'),
                    "has_vectors": vector_stats.get("total_vectors", 0) > 0,
                    "vectorization_complete": vector_stats.get("total_vectors", 0) > 0 and document.get('processing_status') == 'completed'
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
        es_service = ElasticsearchService()
        es_deleted_count = await es_service.delete_document_embeddings(document_id)
        logger.info(f"Deleted {es_deleted_count} embeddings from Elasticsearch")
        await es_service.close_session()
        
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
            'description': f"Admin tarafından manuel {transaction_type}: {credit_update.reason}",
            'created_by': str(current_user.id),
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
        
        # İlişkili verileri sil
        deletion_stats = {
            "credits_deleted": 0,
            "transactions_deleted": 0,
            "search_logs_deleted": 0,
            "documents_found": 0
        }
        
        # 1. İlişkili verileri sil (foreign key constraints nedeniyle)
        # Kredi bakiye kayıtlarını sil
        credit_result = supabase_client.supabase.table('user_credit_balance').delete().eq('user_id', user_id).execute()
        deletion_stats["credits_deleted"] = len(credit_result.data) if credit_result.data else 0
        
        # Kredi transaction kayıtlarını sil
        transactions_result = supabase_client.supabase.table('credit_transactions').delete().eq('user_id', user_id).execute()
        deletion_stats["transactions_deleted"] = len(transactions_result.data) if transactions_result.data else 0
        
        # Arama loglarını sil
        search_logs_result = supabase_client.supabase.table('search_logs').delete().eq('user_id', user_id).execute()
        deletion_stats["search_logs_deleted"] = len(search_logs_result.data) if search_logs_result.data else 0
        
        # Destek biletlerini sil
        supabase_client.supabase.table('support_tickets').delete().eq('user_id', user_id).execute()
        supabase_client.supabase.table('user_feedback').delete().eq('user_id', user_id).execute()
        
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
