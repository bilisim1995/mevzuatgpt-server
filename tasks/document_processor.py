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
from services.pdf_source_parser import PDFSourceParser
from services.progress_service import progress_service
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
            task_id = self.request.id if hasattr(self.request, 'id') else None
            result = loop.run_until_complete(_process_document_async(document_id, task_id))
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

async def _process_document_async(
    document_id: str, 
    task_id: str = None, 
    metadata_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Async document processing implementation with progress tracking
    
    Args:
        document_id: Document UUID
        task_id: Celery task ID for progress tracking
        metadata_overrides: Optional metadata to override from bulk upload JSON
            (e.g., title, description, keywords from section metadata)
        
    Returns:
        Processing result
        
    Raises:
        AppException: If processing fails
    """
    try:
        # Initialize services
        storage_service = StorageService()
        embedding_service = EmbeddingService()
        
        # Step 1: Get document from database
        logger.info(f"Retrieving document metadata: {document_id}")
        document = await supabase_client.get_document(document_id)
        
        if not document:
            raise AppException(
                message="Document not found",
                error_code="DOCUMENT_NOT_FOUND"
            )
        
        # Skip progress initialization if already done by upload endpoint
        # Progress is now initialized immediately after task creation
        if task_id:
            try:
                # Check if progress already exists
                existing_progress = await progress_service.get_task_progress(task_id)
                if not existing_progress:
                    await progress_service.initialize_task_progress(
                        task_id=task_id,
                        document_id=document_id,
                        document_title=document.get('document_title', document.get('filename', 'Unknown')),
                        total_steps=5  # download, extract, chunk, embed, store
                    )
                else:
                    logger.info(f"Progress tracking already initialized for task {task_id}")
            except Exception as progress_error:
                logger.warning(f"Progress tracking error: {progress_error}")
        
        # Update status to processing
        await supabase_client.update_document_status(document_id, "processing")
        
        # Step 1 Progress: Download PDF
        if task_id:
            await progress_service.update_progress(
                task_id=task_id,
                stage="download",
                current_step="PDF dosyası indiriliyor...",
                completed_steps=1
            )
        
        # Step 2: Download PDF from storage
        logger.info(f"Downloading PDF from storage: {document['file_url']}")
        pdf_content = await storage_service.download_file(document['file_url'])
        
        # Step 2 Progress: Extract text
        if task_id:
            await progress_service.update_progress(
                task_id=task_id,
                stage="extract",
                current_step="PDF'den metin çıkarılıyor...",
                completed_steps=2
            )
        
        # Step 3: Extract text from PDF with source tracking
        logger.info(f"Enhanced PDF parsing with source tracking: {document['filename']}")
        pdf_parser = PDFSourceParser()
        parsed_data = pdf_parser.parse_pdf_with_sources(pdf_content, document['filename'])
        
        if not parsed_data.get("parsing_success") or not parsed_data.get("chunks"):
            error_msg = parsed_data.get("error", "No text could be extracted from PDF")
            raise AppException(
                message=error_msg,
                error_code="PDF_TEXT_EXTRACTION_FAILED"
            )
        
        chunks_with_sources = parsed_data["chunks"]
        logger.info(f"Generated {len(chunks_with_sources)} chunks with source information from {parsed_data['total_pages']} pages")
        
        # Step 3 Progress: Text chunking completed
        if task_id:
            await progress_service.update_progress(
                task_id=task_id,
                stage="chunk",
                current_step=f"{len(chunks_with_sources)} metin parçası oluşturuldu...",
                completed_steps=3
            )
        
        # Step 4: Generate embeddings and store in Elasticsearch
        logger.info(f"Generating 2048D embeddings for {len(chunks_with_sources)} chunks")
        
        # Step 4 Progress: Start embedding generation
        if task_id:
            await progress_service.update_progress(
                task_id=task_id,
                stage="embed",
                current_step=f"{len(chunks_with_sources)} parça için vektör oluşturuluyor...",
                completed_steps=4
            )
        
        # Prepare chunks data for Elasticsearch bulk storage
        chunks_for_elasticsearch = []
        for i, chunk_data in enumerate(chunks_with_sources):
            chunk_text = chunk_data["content"]
            
            # Generate 2048-dimensional embedding
            embedding = await embedding_service.generate_embedding(chunk_text)
            
            # Prepare enhanced metadata for Elasticsearch
            # Use metadata_overrides if provided (from bulk upload JSON)
            doc_title = document['title']
            doc_description = None
            doc_keywords = None
            
            if metadata_overrides:
                # Override with JSON metadata if available
                doc_title = metadata_overrides.get('title', document['title'])
                doc_description = metadata_overrides.get('description')
                doc_keywords = metadata_overrides.get('keywords')
            
            chunk_metadata = {
                "total_chunks": len(chunks_with_sources),
                "chunk_length": len(chunk_text),
                "document_title": doc_title,
                "document_filename": document['filename'],
                "belge_adi": document.get('belge_adi'),
                "description": doc_description,
                "keywords": doc_keywords,
                "source_metadata": chunk_data.get("source_metadata", {}),
                "processing_timestamp": datetime.now().isoformat(),
                "text_preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            }
            
            # Prepare chunk for Elasticsearch
            elasticsearch_chunk = {
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": chunk_data["chunk_index"],
                "page_number": chunk_data.get("page_number"),
                "line_start": chunk_data.get("line_start"),
                "line_end": chunk_data.get("line_end"),
                "source_institution": document.get('source_institution') or document.get('institution') or 'Belirtilmemiş',
                "source_document": document['filename'],
                "metadata": chunk_metadata
            }
            chunks_for_elasticsearch.append(elasticsearch_chunk)
        
        # Store all embeddings in Elasticsearch using bulk operation
        logger.info(f"Storing {len(chunks_for_elasticsearch)} embeddings in Elasticsearch")
        embedding_ids = await embedding_service.store_embeddings(
            document_id=document_id,
            chunks=chunks_for_elasticsearch
        )
        
        # Step 5 Progress: Storage completed
        if task_id:
            await progress_service.update_progress(
                task_id=task_id,
                stage="store",
                current_step="Vektörler Elasticsearch'e kaydediliyor...",
                completed_steps=5,
                status="completed"
            )
            
            # Progress temizleme - task tamamlandığında otomatik temizle
            try:
                await progress_service.complete_task_progress(task_id)
                logger.info(f"Progress cleaned up for completed task: {task_id}")
            except Exception as cleanup_error:
                logger.warning(f"Progress cleanup warning for {task_id}: {cleanup_error}")
        
        # Step 6: Update document status to completed
        await supabase_client.update_document_status(document_id, "completed")
        
        result = {
            "document_id": document_id,
            "status": "completed",
            "total_pages": parsed_data.get("total_pages", 0),
            "text_length": parsed_data.get("total_text_length", 0),
            "chunks_created": len(chunks_with_sources),
            "parsing_success": parsed_data.get("parsing_success", False),
            "processing_time": datetime.now().isoformat()
        }
        
        logger.info(f"Document processing completed successfully: {document_id}")
        return result
        
    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}")
        
        # Mark progress as failed if tracking was initialized
        if task_id:
            try:
                await progress_service.mark_task_failed(task_id, str(e))
            except Exception as progress_error:
                logger.error(f"Failed to update progress on error: {progress_error}")
        
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
    
    # Ensure proper UTF-8 encoding for Turkish characters
    try:
        # Handle Turkish characters properly - ensure UTF-8 encoding
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Normalize Turkish characters to ensure consistency
        import unicodedata
        text = unicodedata.normalize('NFC', text)
        
        # Fix common OCR/encoding issues with Turkish characters
        turkish_fixes = {
            'Ğ': 'Ğ', 'ğ': 'ğ', 'Ü': 'Ü', 'ü': 'ü', 'Ş': 'Ş', 'ş': 'ş',
            'İ': 'İ', 'ı': 'ı', 'Ö': 'Ö', 'ö': 'ö', 'Ç': 'Ç', 'ç': 'ç',
            # Common encoding issues
            'Â°': 'ğ', 'Ã§': 'ç', 'Ã¼': 'ü', 'Ä±': 'ı', 'Ã¶': 'ö', 'Ã': 'ş'
        }
        
        for wrong, correct in turkish_fixes.items():
            text = text.replace(wrong, correct)
            
    except Exception as encoding_error:
        logger.warning(f"Turkish character encoding issue: {encoding_error}")
        # Fallback to safe ASCII replacement
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='ignore')
    
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
        # Use Supabase client instead of missing database session
        await supabase_client.update_document_status(document_id, status, error_message)
    except Exception as e:
        logger.error(f"Failed to update document status: {str(e)}")
        return False

async def _cleanup_connections():
    """
    Clean up any remaining async connections and tasks
    """
    try:
        # Sadece basit cleanup, recursive cancellation'dan kaçın
        logger.debug("Cleaning up async connections")
        
        # Sadece mevcut task'ı temizle, diğer task'lara dokunma
        current_task = asyncio.current_task()
        if current_task and not current_task.done():
            logger.debug("Current task cleanup completed")
            
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
    Async implementation of failed documents cleanup using Supabase
    
    Returns:
        Cleanup result statistics
    """
    try:
        # Simple cleanup using Supabase - mark old processing docs as failed
        logger.info("Cleanup task simplified - using direct Supabase calls")
        cleanup_count = 0
        
        result = {
            "cleanup_time": datetime.utcnow().isoformat(),
            "documents_cleaned": cleanup_count,
            "status": "completed"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return {
            "cleanup_time": datetime.utcnow().isoformat(),
            "documents_cleaned": 0,
            "status": "failed",
            "error": str(e)
        }

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
        
        # Trigger normal processing - return task result not task object
        result = process_document_task.apply_async((document_id,))
        return result.get()
        
    except Exception as e:
        logger.error(f"Failed to reprocess document {document_id}: {str(e)}")
        raise CeleryTaskError(f"Document reprocessing failed: {str(e)}")

@celery_app.task(bind=True, name="bulk_process_documents_task")
def bulk_process_documents_task(self, task_payload: Dict[str, Any]):
    """
    Process multiple documents sequentially with progress tracking
    
    This task processes documents one-by-one (not in parallel) to avoid
    overwhelming OpenAI API and Elasticsearch with concurrent requests.
    
    Args:
        task_payload: Dictionary containing:
            - task_id: Bulk upload task ID for progress tracking
            - documents: List of document objects with filename, document_id, metadata
            - user_id: User who initiated the bulk upload
    
    Returns:
        Processing summary with success/failure counts
    """
    task_id = task_payload.get("task_id")
    documents = task_payload.get("documents", [])
    user_id = task_payload.get("user_id")
    
    logger.info(f"Starting bulk document processing: task_id={task_id}, total_documents={len(documents)}")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_bulk_process_documents_async(task_id, documents, user_id))
            return result
        finally:
            try:
                loop.run_until_complete(_cleanup_connections())
            except Exception as cleanup_error:
                logger.warning(f"Bulk cleanup warning: {cleanup_error}")
            finally:
                loop.close()
    
    except Exception as e:
        logger.error(f"Bulk document processing failed for task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update Redis status to failed
        try:
            error_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(error_loop)
            try:
                from services.redis_service import RedisService
                redis_service = RedisService()
                error_loop.run_until_complete(
                    redis_service.update_bulk_upload_progress(task_id, {"status": "failed", "error": str(e)})
                )
            finally:
                error_loop.close()
        except Exception as status_error:
            logger.error(f"Failed to update bulk task status: {str(status_error)}")
        
        raise CeleryTaskError(f"Bulk document processing failed: {str(e)}")

async def _bulk_process_documents_async(task_id: str, documents: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
    """
    Async implementation of bulk document processing with sequential processing
    
    Args:
        task_id: Bulk upload task ID
        documents: List of document dictionaries
        user_id: User ID who initiated upload
        
    Returns:
        Processing summary
    """
    from services.redis_service import RedisService
    redis_service = RedisService()
    
    # Update status to processing
    await redis_service.update_bulk_upload_progress(task_id, {
        "status": "processing",
        "started_at": datetime.utcnow().isoformat()
    })
    
    success_count = 0
    failed_count = 0
    
    # Process documents sequentially (one at a time)
    for index, doc in enumerate(documents):
        filename = doc["filename"]
        document_id = doc["document_id"]
        section_metadata = doc.get("metadata", {})
        
        logger.info(f"Processing document {index + 1}/{len(documents)}: {filename}")
        
        # Update progress - currently processing this file
        await redis_service.update_bulk_upload_progress(task_id, {
            "current_index": index + 1,
            "current_filename": filename
        })
        
        try:
            # Extract metadata overrides for this document
            metadata_overrides = {
                "title": section_metadata.get("title"),
                "description": section_metadata.get("description"),
                "keywords": section_metadata.get("keywords")
            }
            
            # Process single document with metadata overrides
            # Generate a sub-task ID for individual progress tracking
            sub_task_id = f"{task_id}:doc{index}"
            
            result = await _process_document_async(
                document_id=document_id,
                task_id=sub_task_id,
                metadata_overrides=metadata_overrides
            )
            
            # Mark file as completed in Redis
            await redis_service.complete_bulk_upload_file(task_id, filename, document_id)
            success_count += 1
            
            logger.info(f"Successfully processed {filename}: {result.get('status')}")
            
        except Exception as doc_error:
            logger.error(f"Failed to process {filename}: {str(doc_error)}")
            logger.error(traceback.format_exc())
            
            # Mark file as failed in Redis
            await redis_service.fail_bulk_upload_file(task_id, filename, str(doc_error))
            failed_count += 1
            
            # Update document status to failed in database
            try:
                await _update_document_status(document_id, "failed", str(doc_error))
            except Exception as status_error:
                logger.error(f"Failed to update document status: {str(status_error)}")
            
            # Continue with next document (don't fail the entire batch)
            continue
    
    # Determine final status
    if failed_count == 0:
        final_status = "completed"
    elif success_count == 0:
        final_status = "failed"
    else:
        final_status = "completed_with_errors"
    
    # Update final progress
    await redis_service.update_bulk_upload_progress(task_id, {
        "status": final_status,
        "current_index": len(documents),
        "current_filename": None,
        "completed_at": datetime.utcnow().isoformat(),
        "summary": {
            "total": len(documents),
            "success": success_count,
            "failed": failed_count
        }
    })
    
    result = {
        "task_id": task_id,
        "status": final_status,
        "total_documents": len(documents),
        "successful": success_count,
        "failed": failed_count,
        "completed_at": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Bulk processing completed: {result}")
    return result
