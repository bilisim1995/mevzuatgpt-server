"""
Yargitay document processing tasks.
Uses HTML content for chunking and embeddings, stores in Yargitay Elasticsearch index.
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import settings
from models.supabase_client import supabase_client
from services.embedding_service import EmbeddingService
from tasks.celery_app import celery_app, CeleryTaskError
from utils.exceptions import AppException

logger = logging.getLogger(__name__)


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
)


def _extract_filename_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    path = urlparse(url).path
    filename = os.path.basename(path)
    return filename or None


@celery_app.task(bind=True, name="process_yargitay_document_task")
def process_yargitay_document_task(self, document_id: str):
    logger.info(f"Starting Yargitay document processing for document_id: {document_id}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(_process_yargitay_document_async(document_id))
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"Yargitay document processing failed for {document_id}: {str(e)}")
        logger.error(traceback.format_exc())

        if isinstance(e, AppException) and e.error_code == "YARGITAY_DOCUMENT_NOT_FOUND":
            if self.request.retries < 1:
                logger.info(
                    f"Retrying Yargitay document processing for {document_id} (attempt {self.request.retries + 1})"
                )
                raise self.retry(countdown=60, exc=e)

            logger.warning(f"Skipping Yargitay document processing for {document_id}: document not found")
            return {
                "document_id": document_id,
                "status": "skipped",
                "reason": "document_not_found"
            }

        if self.request.retries < self.max_retries:
            logger.info(f"Retrying Yargitay document processing for {document_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=e)

        raise CeleryTaskError(f"Yargitay document processing failed after {self.max_retries} attempts: {str(e)}")


async def _process_yargitay_document_async(document_id: str) -> Dict[str, Any]:
    try:
        embedding_service = EmbeddingService()

        document = await supabase_client.get_yargitay_document(document_id)
        if not document:
            raise AppException(
                message="Yargitay document not found",
                error_code="YARGITAY_DOCUMENT_NOT_FOUND"
            )

        text_content = document.get("icerik_text") or ""
        if not text_content:
            raise AppException(
                message="Yargitay document content is empty",
                error_code="YARGITAY_EMPTY_CONTENT"
            )

        chunks = text_splitter.split_text(text_content)
        if not chunks:
            raise AppException(
                message="Yargitay document could not be chunked",
                error_code="YARGITAY_CHUNK_FAILED"
            )

        filename = _extract_filename_from_url(document.get("pdf_url"))
        chunks_for_elasticsearch = []

        for i, chunk_text in enumerate(chunks):
            embedding = await embedding_service.generate_embedding(chunk_text)

            metadata = {
                "document_title": document.get("belge_adi"),
                "document_filename": filename,
                "belge_adi": document.get("belge_adi"),
                "daire": document.get("daire"),
                "esasNo": document.get("esas_no"),
                "kararNo": document.get("karar_no"),
                "kararTarihi": document.get("karar_tarihi"),
                "total_chunks": len(chunks),
                "chunk_length": len(chunk_text),
                "processing_timestamp": datetime.utcnow().isoformat(),
                "text_preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text
            }

            chunks_for_elasticsearch.append({
                "content": chunk_text,
                "embedding": embedding,
                "chunk_index": i,
                "source_institution": document.get("institution") or "Yargıtay Başkanlığı",
                "source_document": filename,
                "belge_adi": document.get("belge_adi"),
                "metadata": metadata
            })

        logger.info("\033[94m[YARGITAY] Elasticsearch başladı\033[0m")
        embedding_ids = await embedding_service.store_embeddings(
            document_id=document_id,
            chunks=chunks_for_elasticsearch,
            index_name=settings.ELASTICSEARCH_YARGITAY_INDEX,
            include_positions=False
        )
        logger.info("\033[92m[YARGITAY] Elasticsearch bitti\033[0m")
        logger.info("\033[92m[YARGITAY] Tüm süreç tamamlandı\033[0m")

        return {
            "document_id": document_id,
            "status": "completed",
            "chunks_created": len(chunks),
            "embedding_count": len(embedding_ids)
        }

    except Exception as e:
        logger.error(f"Yargitay document processing failed: {str(e)}")
        raise
