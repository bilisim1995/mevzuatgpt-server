"""
User routes for document search and retrieval
Accessible by authenticated users with appropriate permissions
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from core.database import get_db
from api.dependencies import get_current_user, get_optional_user
from models.schemas import (
    UserResponse, SearchRequest, SearchResponse, 
    DocumentResponse, DocumentListResponse,
    AskRequest, AskResponse, SuggestionsResponse
)
from services.search_service import SearchService
from services.document_service import DocumentService
from services.query_service import QueryService
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
    1. Generate embeddings for the query (with caching)
    2. Search for relevant document chunks
    3. Generate AI response using Ollama
    4. Return answer with sources and confidence score
    
    Features:
    - Redis caching for performance
    - Rate limiting protection (30 requests/minute)
    - Institution filtering
    - Confidence scoring
    - User search history tracking
    
    Args:
        ask_request: Question and search parameters
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        AI-generated answer with sources and metadata
    """
    try:
        query_service = QueryService(db)
        
        result = await query_service.process_ask_query(
            query=ask_request.query,
            user_id=str(current_user.id),
            institution_filter=ask_request.institution_filter,
            limit=ask_request.limit,
            similarity_threshold=ask_request.similarity_threshold,
            use_cache=ask_request.use_cache
        )
        
        logger.info(f"Ask query processed for user {current_user.id}: '{ask_request.query[:50]}' - confidence: {result['confidence_score']}")
        
        return success_response(data=result)
        
    except AppException as e:
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
        logger.error(f"Ask error for user {current_user.id}: {str(e)}")
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
