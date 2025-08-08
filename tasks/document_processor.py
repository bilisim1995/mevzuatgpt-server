"""
Document processing tasks
Handles PDF text extraction, chunking, embedding generation, and storage
"""

import logging
import asyncio
import traceback
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import PyPDF2
import pdfplumber
import io
from langchain.text_splitter import RecursiveCharacterTextSplitter

from tasks.celery_app import celery_app, CeleryTaskError, TaskStates
from models.supabase_client import supabase_client
from services.storage_service import StorageService
from services.embedding_service import EmbeddingService
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

# Text splitter configuration
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
)

@celery_app.task(bind=True, name="process_document_task")
def process_document_task(self, document_id: str):
    """
    Process uploaded document: extract text, generate embeddings, store in vector database
    
    Args:
        document_id: UUID of the document to process
        
    Returns:
        Processing result dictionary
    """
    logger.info(f"Starting document processing for document_id: {document_id}")
    
    try:
        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_process_document_async(document_id))
            return result
        finally:
            # Ensure all async connections are properly closed
            try:
                loop.run_until_complete(_cleanup_connections())
            except Exception as cleanup_error:
                logger.warning(f"Cleanup warning: {cleanup_error}")
            finally:
                loop.close()
            
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update document status to failed
        try:
            error_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(error_loop)
            try:
                error_loop.run_until_complete(_update_document_status(document_id, "failed", str(e)))
            finally:
                try:
                    error_loop.run_until_complete(_cleanup_connections())
                except:
                    pass
                error_loop.close()
        except Exception as status_error:
            logger.error(f"Failed to update document status: {str(status_error)}")
        
        # Retry the task if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying document processing for {document_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)
        
        raise CeleryTaskError(f"Document processing failed after {self.max_retries} attempts: {str(e)}")

async def _process_document_async(document_id: str) -> Dict[str, Any]:
    """
    Async document processing implementation
    
    Args:
        document_id: Document UUID
        
    Returns:
        Processing result
        
    Raises:
        AppException: If processing fails
    """
    try:
        # Initialize services
        storage_service = StorageService()
        embedding_service = EmbeddingService()
        
        # Update status to processing
        await supabase_client.update_document_status(document_id, "processing")
        
        # Step 1: Get document from database
        logger.info(f"Retrieving document metadata: {document_id}")
        document = await supabase_client.get_document(document_id)
        
        if not document:
            raise AppException(
                message="Document not found",
                error_code="DOCUMENT_NOT_FOUND"
            )
        
        # Step 2: Download PDF from storage
        logger.info(f"Downloading PDF from storage: {document['file_url']}")
        pdf_content = await storage_service.download_file(document['file_url'])
        
        # Step 3: Extract text from PDF
        logger.info(f"Extracting text from PDF: {document['filename']}")
        extracted_text = _extract_text_from_pdf(pdf_content)
        
        if not extracted_text.strip():
            raise AppException(
                message="No text could be extracted from PDF",
                error_code="PDF_TEXT_EXTRACTION_FAILED"
            )
        
        # Step 4: Split text into chunks
        logger.info(f"Splitting text into chunks for document: {document_id}")
        text_chunks = text_splitter.split_text(extracted_text)
        
        if not text_chunks:
            raise AppException(
                message="Failed to split text into chunks",
                error_code="TEXT_CHUNKING_FAILED"
            )
        
        logger.info(f"Generated {len(text_chunks)} text chunks")
        
        # Step 5: Generate embeddings for chunks using Supabase
        logger.info(f"Generating embeddings for {len(text_chunks)} chunks")
        
        # Store embeddings one by one using Supabase client
        for i, chunk_text in enumerate(text_chunks):
            # Generate embedding for this chunk
            embedding = await embedding_service.generate_embedding(chunk_text)
            
            # Store in Supabase
            await supabase_client.create_embedding(
                doc_id=document_id,
                content=chunk_text,
                embedding=embedding,
                chunk_index=i
            )
        
        # Step 6: Update document status to completed
        await supabase_client.update_document_status(document_id, "completed")
        
        result = {
            "document_id": document_id,
            "status": "completed",
            "text_length": len(extracted_text),
            "chunks_created": len(text_chunks),
            "processing_time": datetime.now().isoformat()
        }
        
        logger.info(f"Document processing completed successfully: {document_id}")
        return result
        
    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}")
        raise

def _extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text content from PDF file using multiple methods
    Tries pdfplumber first (better for complex PDFs), then falls back to PyPDF2
    
    Args:
        pdf_content: PDF file content as bytes
        
    Returns:
        Extracted text content
        
    Raises:
        AppException: If text extraction fails
    """
    try:
        pdf_file = io.BytesIO(pdf_content)
        
        # Method 1: Try pdfplumber (better for complex PDFs)
        logger.info("Attempting text extraction with pdfplumber...")
        try:
            extracted_text = []
            with pdfplumber.open(pdf_file) as pdf:
                total_pages = len(pdf.pages)
                logger.info(f"PDF opened with pdfplumber - {total_pages} pages found")
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            extracted_text.append(page_text.strip())
                            logger.debug(f"Extracted {len(page_text)} characters from page {page_num + 1}")
                        else:
                            logger.debug(f"No text found on page {page_num + 1}")
                    except Exception as page_error:
                        logger.warning(f"pdfplumber failed on page {page_num + 1}: {str(page_error)}")
                        continue
            
            if extracted_text:
                full_text = "\n\n".join(extracted_text)
                full_text = _clean_extracted_text(full_text)
                logger.info(f"pdfplumber successfully extracted {len(full_text)} characters")
                return full_text
            else:
                logger.warning("pdfplumber found no text content")
        
        except Exception as plumber_error:
            logger.warning(f"pdfplumber extraction failed: {str(plumber_error)}")
        
        # Method 2: Fallback to PyPDF2
        logger.info("Attempting text extraction with PyPDF2...")
        pdf_file.seek(0)  # Reset file pointer
        
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            logger.info(f"PDF opened with PyPDF2 - {len(pdf_reader.pages)} pages found")
            
            extracted_text = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        extracted_text.append(page_text.strip())
                        logger.debug(f"Extracted {len(page_text)} characters from page {page_num + 1}")
                except Exception as page_error:
                    logger.warning(f"PyPDF2 failed on page {page_num + 1}: {str(page_error)}")
                    continue
            
            if extracted_text:
                full_text = "\n\n".join(extracted_text)
                full_text = _clean_extracted_text(full_text)
                logger.info(f"PyPDF2 successfully extracted {len(full_text)} characters")
                return full_text
            else:
                logger.warning("PyPDF2 found no text content")
        
        except Exception as pypdf_error:
            logger.warning(f"PyPDF2 extraction failed: {str(pypdf_error)}")
        
        # If both methods fail
        raise AppException(
            message="No text content found in PDF - file may be image-based or corrupted",
            error_code="PDF_NO_TEXT_CONTENT"
        )
        
    except PyPDF2.errors.PdfReadError as e:
        logger.error(f"PDF read error: {str(e)}")
        raise AppException(
            message="Invalid or corrupted PDF file",
            detail=str(e),
            error_code="PDF_READ_ERROR"
        )
    except Exception as e:
        logger.error(f"Text extraction error: {str(e)}")
        raise AppException(
            message="Failed to extract text from PDF",
            detail=str(e),
            error_code="PDF_TEXT_EXTRACTION_ERROR"
        )

def _clean_extracted_text(text: str) -> str:
    """
    Clean extracted text by removing excessive whitespace and formatting issues
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    # Remove excessive whitespace
    import re
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive line breaks
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # Clean up common PDF artifacts
    text = text.replace('\x00', '')  # Remove null bytes
    text = text.replace('\ufffd', '')  # Remove replacement characters
    
    # Normalize Turkish characters
    turkish_char_map = {
        'Ğ': 'Ğ', 'ğ': 'ğ', 'Ü': 'Ü', 'ü': 'ü', 'Ş': 'Ş', 'ş': 'ş',
        'İ': 'İ', 'ı': 'ı', 'Ö': 'Ö', 'ö': 'ö', 'Ç': 'Ç', 'ç': 'ç'
    }
    
    for old_char, new_char in turkish_char_map.items():
        text = text.replace(old_char, new_char)
    
    return text.strip()

async def _update_document_status(
    document_id: str, 
    status: str, 
    error_message: Optional[str] = None
) -> bool:
    """
    Update document processing status in database
    
    Args:
        document_id: Document UUID
        status: New processing status
        error_message: Error message if status is failed
        
    Returns:
        True if updated successfully
    """
    try:
        async with get_db_session() as db:
            document_service = DocumentService(db)
            return await document_service.update_processing_status(
                document_id, status, error_message
            )
    except Exception as e:
        logger.error(f"Failed to update document status: {str(e)}")
        return False

async def _cleanup_connections():
    """
    Clean up any remaining async connections and tasks
    """
    try:
        # Get the current event loop
        loop = asyncio.get_event_loop()
        
        # Cancel any remaining tasks
        pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending_tasks:
            for task in pending_tasks:
                task.cancel()
            
            # Wait for tasks to complete cancellation
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            
    except Exception as e:
        logger.warning(f"Connection cleanup warning: {e}")
        pass

@celery_app.task(bind=True, name="cleanup_failed_documents")
def cleanup_failed_documents(self):
    """
    Periodic task to clean up failed document processing attempts
    """
    logger.info("Starting cleanup of failed documents")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_cleanup_failed_documents_async())
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Failed document cleanup error: {str(e)}")
        raise

async def _cleanup_failed_documents_async() -> Dict[str, Any]:
    """
    Async implementation of failed documents cleanup
    
    Returns:
        Cleanup result statistics
    """
    try:
        async with get_db_session() as db:
            # Find documents that have been in 'processing' state for too long (>1 hour)
            from sqlalchemy import select, update, and_
            from models.database import Document
            from datetime import datetime, timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            # Find stuck processing documents
            stuck_query = select(Document).where(
                and_(
                    Document.processing_status == "processing",
                    Document.updated_at < cutoff_time
                )
            )
            
            result = await db.execute(stuck_query)
            stuck_documents = result.scalars().all()
            
            # Update stuck documents to failed status
            cleanup_count = 0
            for doc in stuck_documents:
                update_stmt = (
                    update(Document)
                    .where(Document.id == doc.id)
                    .values(
                        processing_status="failed",
                        processing_error="Processing timeout - exceeded maximum processing time"
                    )
                )
                
                await db.execute(update_stmt)
                cleanup_count += 1
                
                logger.info(f"Marked stuck document as failed: {doc.id}")
            
            await db.commit()
            
            result = {
                "cleanup_time": datetime.utcnow().isoformat(),
                "documents_cleaned": cleanup_count,
                "cutoff_time": cutoff_time.isoformat()
            }
            
            logger.info(f"Cleanup completed: {cleanup_count} documents marked as failed")
            return result
            
    except Exception as e:
        logger.error(f"Failed documents cleanup error: {str(e)}")
        raise

@celery_app.task(bind=True, name="reprocess_failed_document")
def reprocess_failed_document(self, document_id: str):
    """
    Retry processing for a failed document
    
    Args:
        document_id: Document UUID to reprocess
        
    Returns:
        Reprocessing result
    """
    logger.info(f"Reprocessing failed document: {document_id}")
    
    try:
        # Reset document status to pending
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(_update_document_status(document_id, "pending"))
        finally:
            loop.close()
        
        # Trigger normal processing
        return process_document_task.delay(document_id)
        
    except Exception as e:
        logger.error(f"Failed to reprocess document {document_id}: {str(e)}")
        raise CeleryTaskError(f"Document reprocessing failed: {str(e)}")
