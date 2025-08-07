"""
Document service
Handles document metadata operations and database interactions
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from typing import List, Tuple, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
import logging

from models.database import Document, User, Embedding
from models.schemas import DocumentCreate, DocumentUpdate, DocumentResponse
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class DocumentService:
    """Service class for document management operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_document(self, document_data: DocumentCreate) -> DocumentResponse:
        """
        Create a new document record in database
        
        Args:
            document_data: Document creation data
            
        Returns:
            Created document information
            
        Raises:
            AppException: If document creation fails
        """
        try:
            # Parse publish_date if it's a string
            publish_date = None
            if document_data.publish_date:
                if isinstance(document_data.publish_date, str):
                    publish_date = datetime.strptime(document_data.publish_date, "%Y-%m-%d").date()
                else:
                    publish_date = document_data.publish_date
            
            # Create document instance
            db_document = Document(
                title=document_data.title,
                category=document_data.category,
                description=document_data.description,
                keywords=document_data.keywords,
                source_institution=document_data.source_institution,
                publish_date=publish_date,
                file_name=document_data.file_name,
                file_url=document_data.file_url,
                file_size=document_data.file_size,
                uploaded_by=document_data.uploaded_by
            )
            
            # Add to database
            self.db.add(db_document)
            await self.db.flush()
            await self.db.refresh(db_document)
            
            logger.info(f"Document created: {db_document.id} - {document_data.title}")
            
            return DocumentResponse(
                id=db_document.id,
                title=db_document.title,
                category=db_document.category,
                description=db_document.description,
                keywords=db_document.keywords or [],
                source_institution=db_document.source_institution,
                publish_date=db_document.publish_date,
                file_name=db_document.file_name,
                file_url=db_document.file_url,
                file_size=db_document.file_size,
                processing_status=db_document.processing_status,
                status=db_document.status,
                uploaded_by=db_document.uploaded_by,
                uploaded_at=db_document.uploaded_at,
                updated_at=db_document.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to create document: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to create document",
                detail=str(e),
                error_code="DOCUMENT_CREATION_FAILED"
            )
    
    async def get_document_by_id(self, document_id: str) -> Optional[DocumentResponse]:
        """
        Get document by ID
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document information if found, None otherwise
        """
        try:
            stmt = select(Document).where(Document.id == UUID(document_id))
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()
            
            if document:
                return DocumentResponse(
                    id=document.id,
                    title=document.title,
                    category=document.category,
                    description=document.description,
                    keywords=document.keywords or [],
                    source_institution=document.source_institution,
                    publish_date=document.publish_date,
                    file_name=document.file_name,
                    file_url=document.file_url,
                    file_size=document.file_size,
                    processing_status=document.processing_status,
                    status=document.status,
                    uploaded_by=document.uploaded_by,
                    uploaded_at=document.uploaded_at,
                    updated_at=document.updated_at
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {str(e)}")
            return None
    
    async def get_published_document_by_id(self, document_id: str) -> Optional[DocumentResponse]:
        """
        Get published document by ID (for user access)
        
        Args:
            document_id: Document UUID
            
        Returns:
            Document information if found and published, None otherwise
        """
        try:
            stmt = select(Document).where(
                and_(
                    Document.id == UUID(document_id),
                    Document.status == "active",
                    Document.processing_status == "completed"
                )
            )
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()
            
            if document:
                return DocumentResponse(
                    id=document.id,
                    title=document.title,
                    category=document.category,
                    description=document.description,
                    keywords=document.keywords or [],
                    source_institution=document.source_institution,
                    publish_date=document.publish_date,
                    file_name=document.file_name,
                    file_url=document.file_url,
                    file_size=document.file_size,
                    processing_status=document.processing_status,
                    status=document.status,
                    uploaded_by=document.uploaded_by,
                    uploaded_at=document.uploaded_at,
                    updated_at=document.updated_at
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get published document {document_id}: {str(e)}")
            return None
    
    async def list_documents(
        self,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[DocumentResponse], int]:
        """
        List documents with pagination and filtering (Admin access)
        
        Args:
            page: Page number (starts from 1)
            limit: Number of documents per page
            category: Filter by category
            status: Filter by processing status
            
        Returns:
            Tuple of (documents list, total count)
        """
        try:
            # Build filter conditions
            conditions = []
            
            if category:
                conditions.append(Document.category == category)
            
            if status:
                conditions.append(Document.processing_status == status)
            
            # Base query
            base_query = select(Document)
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # Count total documents
            count_query = select(func.count(Document.id))
            if conditions:
                count_query = count_query.where(and_(*conditions))
            
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Get documents with pagination
            documents_query = (
                base_query
                .order_by(desc(Document.uploaded_at))
                .offset((page - 1) * limit)
                .limit(limit)
            )
            
            result = await self.db.execute(documents_query)
            documents = result.scalars().all()
            
            # Convert to response models
            document_responses = []
            for doc in documents:
                document_responses.append(DocumentResponse(
                    id=doc.id,
                    title=doc.title,
                    category=doc.category,
                    description=doc.description,
                    keywords=doc.keywords or [],
                    source_institution=doc.source_institution,
                    publish_date=doc.publish_date,
                    file_name=doc.file_name,
                    file_url=doc.file_url,
                    file_size=doc.file_size,
                    processing_status=doc.processing_status,
                    status=doc.status,
                    uploaded_by=doc.uploaded_by,
                    uploaded_at=doc.uploaded_at,
                    updated_at=doc.updated_at
                ))
            
            return document_responses, total_count
            
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise AppException(
                message="Failed to retrieve documents",
                detail=str(e),
                error_code="DOCUMENT_LIST_FAILED"
            )
    
    async def list_published_documents(
        self,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> Tuple[List[DocumentResponse], int]:
        """
        List published documents (User access)
        
        Args:
            page: Page number (starts from 1)
            limit: Number of documents per page
            category: Filter by category
            keyword: Search in titles and descriptions
            
        Returns:
            Tuple of (documents list, total count)
        """
        try:
            # Build filter conditions
            conditions = [
                Document.status == "active",
                Document.processing_status == "completed"
            ]
            
            if category:
                conditions.append(Document.category == category)
            
            if keyword:
                keyword_condition = or_(
                    Document.title.ilike(f"%{keyword}%"),
                    Document.description.ilike(f"%{keyword}%")
                )
                conditions.append(keyword_condition)
            
            # Count total documents
            count_query = select(func.count(Document.id)).where(and_(*conditions))
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            # Get documents with pagination
            documents_query = (
                select(Document)
                .where(and_(*conditions))
                .order_by(desc(Document.uploaded_at))
                .offset((page - 1) * limit)
                .limit(limit)
            )
            
            result = await self.db.execute(documents_query)
            documents = result.scalars().all()
            
            # Convert to response models
            document_responses = []
            for doc in documents:
                document_responses.append(DocumentResponse(
                    id=doc.id,
                    title=doc.title,
                    category=doc.category,
                    description=doc.description,
                    keywords=doc.keywords or [],
                    source_institution=doc.source_institution,
                    publish_date=doc.publish_date,
                    file_name=doc.file_name,
                    file_url=doc.file_url,
                    file_size=doc.file_size,
                    processing_status=doc.processing_status,
                    status=doc.status,
                    uploaded_by=doc.uploaded_by,
                    uploaded_at=doc.uploaded_at,
                    updated_at=doc.updated_at
                ))
            
            return document_responses, total_count
            
        except Exception as e:
            logger.error(f"Failed to list published documents: {str(e)}")
            raise AppException(
                message="Failed to retrieve published documents",
                detail=str(e),
                error_code="PUBLISHED_DOCUMENTS_LIST_FAILED"
            )
    
    async def update_document(
        self, 
        document_id: str, 
        document_update: DocumentUpdate
    ) -> Optional[DocumentResponse]:
        """
        Update document metadata
        
        Args:
            document_id: Document UUID
            document_update: Updated document data
            
        Returns:
            Updated document information
            
        Raises:
            AppException: If update fails
        """
        try:
            # Prepare update data
            update_data = {}
            
            if document_update.title is not None:
                update_data["title"] = document_update.title
            if document_update.category is not None:
                update_data["category"] = document_update.category
            if document_update.description is not None:
                update_data["description"] = document_update.description
            if document_update.keywords is not None:
                update_data["keywords"] = document_update.keywords
            if document_update.source_institution is not None:
                update_data["source_institution"] = document_update.source_institution
            if document_update.publish_date is not None:
                update_data["publish_date"] = document_update.publish_date
            if document_update.status is not None:
                update_data["status"] = document_update.status
            
            if not update_data:
                # No changes to make
                return await self.get_document_by_id(document_id)
            
            # Update document
            stmt = (
                update(Document)
                .where(Document.id == UUID(document_id))
                .values(**update_data)
                .returning(Document)
            )
            
            result = await self.db.execute(stmt)
            updated_document = result.scalar_one_or_none()
            
            if not updated_document:
                return None
            
            await self.db.flush()
            
            logger.info(f"Document updated: {document_id}")
            
            return DocumentResponse(
                id=updated_document.id,
                title=updated_document.title,
                category=updated_document.category,
                description=updated_document.description,
                keywords=updated_document.keywords or [],
                source_institution=updated_document.source_institution,
                publish_date=updated_document.publish_date,
                file_name=updated_document.file_name,
                file_url=updated_document.file_url,
                file_size=updated_document.file_size,
                processing_status=updated_document.processing_status,
                status=updated_document.status,
                uploaded_by=updated_document.uploaded_by,
                uploaded_at=updated_document.uploaded_at,
                updated_at=updated_document.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to update document",
                detail=str(e),
                error_code="DOCUMENT_UPDATE_FAILED"
            )
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete document and its embeddings
        
        Args:
            document_id: Document UUID
            
        Returns:
            True if deleted successfully
            
        Raises:
            AppException: If deletion fails
        """
        try:
            stmt = delete(Document).where(Document.id == UUID(document_id))
            result = await self.db.execute(stmt)
            
            if result.rowcount == 0:
                return False
            
            await self.db.flush()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            await self.db.rollback()
            raise AppException(
                message="Failed to delete document",
                detail=str(e),
                error_code="DOCUMENT_DELETE_FAILED"
            )
    
    async def update_processing_status(
        self, 
        document_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update document processing status
        
        Args:
            document_id: Document UUID
            status: Processing status (pending, processing, completed, failed)
            error_message: Error message if status is failed
            
        Returns:
            True if updated successfully
        """
        try:
            update_data = {"processing_status": status}
            if error_message:
                update_data["processing_error"] = error_message
            
            stmt = (
                update(Document)
                .where(Document.id == UUID(document_id))
                .values(**update_data)
            )
            
            result = await self.db.execute(stmt)
            await self.db.flush()
            
            logger.info(f"Document processing status updated: {document_id} -> {status}")
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update processing status for {document_id}: {str(e)}")
            return False
    
    async def get_available_categories(self) -> List[str]:
        """
        Get list of available document categories
        
        Returns:
            List of category names
        """
        try:
            stmt = (
                select(Document.category)
                .where(
                    and_(
                        Document.category.isnot(None),
                        Document.status == "active",
                        Document.processing_status == "completed"
                    )
                )
                .distinct()
                .order_by(Document.category)
            )
            
            result = await self.db.execute(stmt)
            categories = [row[0] for row in result.fetchall()]
            
            return categories
            
        except Exception as e:
            logger.error(f"Failed to get categories: {str(e)}")
            return []
    
    async def get_recent_documents(self, limit: int = 10) -> List[DocumentResponse]:
        """
        Get recently published documents
        
        Args:
            limit: Number of documents to return
            
        Returns:
            List of recent documents
        """
        try:
            stmt = (
                select(Document)
                .where(
                    and_(
                        Document.status == "active",
                        Document.processing_status == "completed"
                    )
                )
                .order_by(desc(Document.uploaded_at))
                .limit(limit)
            )
            
            result = await self.db.execute(stmt)
            documents = result.scalars().all()
            
            # Convert to response models
            document_responses = []
            for doc in documents:
                document_responses.append(DocumentResponse(
                    id=doc.id,
                    title=doc.title,
                    category=doc.category,
                    description=doc.description,
                    keywords=doc.keywords or [],
                    source_institution=doc.source_institution,
                    publish_date=doc.publish_date,
                    file_name=doc.file_name,
                    file_url=doc.file_url,
                    file_size=doc.file_size,
                    processing_status=doc.processing_status,
                    status=doc.status,
                    uploaded_by=doc.uploaded_by,
                    uploaded_at=doc.uploaded_at,
                    updated_at=doc.updated_at
                ))
            
            return document_responses
            
        except Exception as e:
            logger.error(f"Failed to get recent documents: {str(e)}")
            return []
