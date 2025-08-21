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
    DocumentUpdate, DocumentListResponse, UploadResponse
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
            'document_type': category or 'Genel',
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
            'id, title, filename, file_url, category, processing_status, file_size, created_at, updated_at, uploaded_by, content_preview, processing_error'
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
                "has_error": bool(doc.get('processing_error')),
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
        
        # Step 2: Get embedding count from Elasticsearch
        from services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        embedding_count = await embedding_service.get_embeddings_count(document_id)
        
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
        
        # Step 4: Calculate storage size (estimate vector storage)
        file_size_mb = round(document.get('file_size', 0) / (1024 * 1024), 2) if document.get('file_size') else 0
        vector_storage_mb = round((embedding_count * 1536 * 4) / (1024 * 1024), 2)  # 1536 dims * 4 bytes per float
        
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
                "elasticsearch_info": {
                    "embedding_count": embedding_count,
                    "vector_storage_mb": vector_storage_mb,
                    "vector_dimensions": 1536,
                    "index_name": "mevzuat_embeddings"
                },
                "metadata": {
                    "keywords": document.get('keywords', []),
                    "source_institution": document.get('institution'),
                    "publish_date": document.get('publish_date'),
                    "processing_error": document.get('processing_error')
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
