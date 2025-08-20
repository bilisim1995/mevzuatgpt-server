"""
Source Enhancement Service - Modular PDF Source Information System
Provides detailed source information including page numbers, line ranges, and PDF links
"""

from typing import List, Dict, Any, Optional
import logging
import re
from urllib.parse import urljoin
from core.config import settings

logger = logging.getLogger(__name__)


class SourceEnhancementService:
    """
    Service for enhancing search results with detailed source information
    Provides PDF links, page numbers, and line ranges for better referencing
    """
    
    def __init__(self):
        self.bunny_cdn_base = settings.BUNNY_STORAGE_ENDPOINT
        self.bunny_zone = settings.BUNNY_STORAGE_ZONE
    
    def enhance_search_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enhance search results with detailed source information
        
        Args:
            search_results: Raw search results from vector database
            
        Returns:
            Enhanced results with source details
        """
        try:
            enhanced_results = []
            
            # Batch fetch document URLs and metadata to avoid duplicate queries
            logger.info(f"🚀 Starting batch fetch for {len(search_results)} search results")
            document_data = self._batch_fetch_document_urls(search_results)
            logger.info(f"📦 Batch fetch completed: {len(document_data.get('urls', {}))} documents with URLs")
            
            for result in search_results:
                document_id = result.get("document_id")
                enhanced_result = self._enhance_single_result(result, document_data)
                
                enhanced_results.append(enhanced_result)
            
            logger.info(f"Enhanced {len(enhanced_results)} search results with source information")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Failed to enhance search results: {e}")
            # Return original results if enhancement fails
            return search_results
    
    def _enhance_single_result(self, result: Dict[str, Any], document_data: Dict = None) -> Dict[str, Any]:
        """Enhance a single search result with source information"""
        try:
            # Start with original result
            enhanced = result.copy()
            
            # Extract base information
            document_id = result.get("document_id")
            document_title = result.get("document_title", "")
            chunk_index = result.get("chunk_index", 0)
            content = result.get("content", "")
            
            # Make sure document_id is preserved in enhanced result
            if document_id:
                enhanced["document_id"] = document_id
            
            # Add PDF URL and metadata from pre-fetched cache or database
            if document_data and isinstance(document_data, dict):
                document_urls = document_data.get('urls', {})
                document_metadata = document_data.get('metadata', {})
                
                if document_id and document_id in document_urls:
                    file_url = document_urls[document_id]
                    enhanced["pdf_url"] = self._convert_to_public_cdn_url(file_url)
                
                # Add metadata information
                if document_id and document_id in document_metadata:
                    metadata = document_metadata[document_id]
                    if isinstance(metadata, dict):
                        enhanced["source_institution"] = metadata.get("source_institution", "")
                        enhanced["category"] = metadata.get("category", "")
                        enhanced["keywords"] = metadata.get("keywords", [])
            
            # Fallback: If no PDF URL found, try direct DB query
            if not enhanced.get("pdf_url") and document_id:
                pdf_url = self._get_pdf_url_from_db(document_id)
                enhanced["pdf_url"] = self._convert_to_public_cdn_url(pdf_url)
                logger.debug(f"Fetched PDF URL for doc {document_id}: {pdf_url is not None}")
            elif enhanced.get("pdf_url"):
                # Ensure existing URL is in public CDN format
                enhanced["pdf_url"] = self._convert_to_public_cdn_url(enhanced["pdf_url"])
                logger.debug(f"PDF URL found in cache for doc {document_id}: ✓")
            else:
                logger.warning(f"No PDF URL available for doc {document_id}")
            
            # Use direct column values first, fallback to extraction methods
            page_number = result.get("page_number") or self._extract_page_number(result)
            line_start = result.get("line_start")
            line_end = result.get("line_end")
            
            # If direct columns don't have data, calculate estimates
            if not line_start or not line_end:
                line_range = self._calculate_line_range(content, chunk_index)
                if line_range:
                    line_start = line_range["start"]
                    line_end = line_range["end"]
            
            # Set final values with validation
            if page_number and isinstance(page_number, int) and page_number > 0:
                enhanced["page_number"] = page_number
            if line_start and isinstance(line_start, int) and line_start > 0:
                enhanced["line_start"] = line_start
            if line_end and isinstance(line_end, int) and line_end > 0:
                enhanced["line_end"] = line_end
                
            # Validate source data consistency
            enhanced = self._validate_source_data(enhanced)
            
            # Add source citation
            citation = self._generate_citation(document_title, page_number, line_range)
            enhanced["citation"] = citation
            
            # Add preview text for reference
            preview = self._generate_content_preview(content)
            enhanced["content_preview"] = preview
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Failed to enhance single result: {e}")
            return result
    
    def _batch_fetch_document_urls(self, search_results: List[Dict[str, Any]]) -> Dict[str, str]:
        """Batch fetch document URLs to avoid duplicate database queries"""
        try:
            # Extract unique document IDs
            document_ids = list(set(
                result.get("document_id") for result in search_results 
                if result.get("document_id")
            ))
            
            logger.info(f"🔍 Extracted {len(document_ids)} unique document IDs: {document_ids[:3]}...")
            
            if not document_ids:
                logger.warning("❌ No document IDs found in search results")
                return {'urls': {}, 'metadata': {}}
                
            from models.supabase_client import supabase_client
            
            # Batch query for all document URLs and metadata including filename
            result = supabase_client.supabase.table('mevzuat_documents') \
                .select('id, file_url, filename, metadata') \
                .in_('id', document_ids) \
                .execute()
            
            # Create lookup dictionary with URLs and metadata
            url_map = {}
            metadata_map = {}
            if result.data:
                for doc in result.data:
                    doc_id = doc['id']
                    file_url = doc.get('file_url')
                    filename = doc.get('filename', 'Unknown')
                    
                    metadata_map[doc_id] = doc.get('metadata', {})
                    
                    # Enhanced debug logging for each document
                    if file_url:
                        logger.debug(f"✅ Batch: Found URL for {doc_id} ({filename}): {file_url[:50] if len(file_url) > 50 else file_url}")
                        url_map[doc_id] = file_url
                    else:
                        logger.warning(f"❌ Batch: NULL file_url for document {doc_id} - filename: {filename}")
                        # Try to generate CDN URL from filename if possible
                        if filename and filename != 'Unknown' and '.' in filename:
                            generated_url = f"https://cdn.mevzuatgpt.org/documents/{filename}"
                            logger.info(f"🔧 Generated CDN URL for {filename}: {generated_url}")
                            url_map[doc_id] = generated_url
                        else:
                            url_map[doc_id] = None
            
            logger.info(f"📦 Batch fetched URLs for {len(url_map)} documents, {sum(1 for url in url_map.values() if url)} have valid URLs")
            return {'urls': url_map, 'metadata': metadata_map}
            
        except Exception as e:
            logger.error(f"Failed to batch fetch document URLs: {e}")
            return {'urls': {}, 'metadata': {}}
    
    def _get_pdf_url_from_db(self, document_id: str) -> Optional[str]:
        """Get actual PDF URL from document table in database"""
        try:
            if not document_id:
                return None
                
            from models.supabase_client import supabase_client
            
            logger.debug(f"🔍 Fetching PDF URL from DB for document_id: {document_id}")
            
            # Query document table for file_url and filename for debugging
            result = supabase_client.supabase.table('mevzuat_documents') \
                .select('file_url, filename, title') \
                .eq('id', document_id) \
                .single() \
                .execute()
            
            if result.data:
                file_url = result.data.get('file_url')
                filename = result.data.get('filename')
                title = result.data.get('title')
                
                logger.debug(f"📁 Document found - Name: {filename}, Title: {title}")
                
                if file_url:
                    logger.info(f"✅ PDF URL found in DB for {document_id}: {file_url[:50] if len(file_url) > 50 else file_url}")
                    return file_url
                else:
                    logger.warning(f"❌ PDF file_url is NULL in database for document {document_id} ({filename})")
                    return None
            else:
                logger.warning(f"❌ Document {document_id} not found in database")
                return None
            
        except Exception as e:
            logger.error(f"Failed to get PDF URL for document {document_id}: {e}")
            return None
    
    def _extract_page_number(self, result: Dict[str, Any]) -> Optional[int]:
        """Extract page number from result metadata or content"""
        try:
            # First try to get from direct metadata
            page_num = result.get("page_number")
            if page_num:
                return int(page_num)
            
            # Try to extract from content patterns
            content = result.get("content", "")
            
            # Look for page indicators in content
            page_patterns = [
                r'(?:Sayfa|Page)\s*:?\s*(\d+)',
                r'(?:s\.|sf\.|p\.)\s*(\d+)',
                r'\[Sayfa\s+(\d+)\]',
                r'- (\d+) -'  # Page numbers like "- 5 -"
            ]
            
            for pattern in page_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return int(match.group(1))
            
            # Fallback: estimate from chunk_index  
            chunk_index = result.get("chunk_index", 0)
            if chunk_index >= 0:  # Allow chunk_index 0
                # More realistic estimate for legal documents: ~10-12 chunks per page
                # Legal docs tend to have smaller chunks due to formatting
                estimated_page = (chunk_index // 10) + 1
                logger.debug(f"Estimated page {estimated_page} from chunk_index {chunk_index}")
                return estimated_page
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract page number: {e}")
            return None
    
    def _calculate_line_range(self, content: str, chunk_index: int) -> Optional[Dict[str, int]]:
        """Calculate estimated line range for content chunk"""
        try:
            if not content:
                return None
            
            # Count lines in content
            lines = content.split('\n')
            content_lines = len(lines)
            
            # More realistic line calculation for legal documents
            # Legal documents have dense content: ~4-6 lines per chunk
            lines_per_chunk = 5  # More accurate for legal content
            estimated_start = (chunk_index * lines_per_chunk) + 1
            
            # Calculate end based on actual content lines, but cap for realism
            content_line_count = max(3, min(content_lines, 6))  # Legal chunks are typically 3-6 lines
            estimated_end = estimated_start + content_line_count - 1
            
            logger.debug(f"Line range calculated: {estimated_start}-{estimated_end} for chunk {chunk_index}")
            
            return {
                "start": max(1, estimated_start),
                "end": max(estimated_start, estimated_end)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate line range: {e}")
            return None
    
    def _validate_source_data(self, enhanced: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean source data for consistency"""
        try:
            # Validate page number
            page_number = enhanced.get("page_number")
            if page_number is not None:
                if not isinstance(page_number, int) or page_number < 1:
                    logger.warning(f"Invalid page number {page_number}, removing")
                    enhanced.pop("page_number", None)
            
            # Validate line numbers
            line_start = enhanced.get("line_start")
            line_end = enhanced.get("line_end")
            
            if line_start is not None or line_end is not None:
                # Both should be present and valid
                if (not isinstance(line_start, int) or line_start < 1 or
                    not isinstance(line_end, int) or line_end < 1 or
                    line_end < line_start):
                    
                    logger.warning(f"Invalid line range {line_start}-{line_end}, removing")
                    enhanced.pop("line_start", None)
                    enhanced.pop("line_end", None)
            
            # Validate chunk_index
            chunk_index = enhanced.get("chunk_index")
            if chunk_index is not None and (not isinstance(chunk_index, int) or chunk_index < 0):
                logger.warning(f"Invalid chunk_index {chunk_index}, setting to 0")
                enhanced["chunk_index"] = 0
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error validating source data: {e}")
            return enhanced
    
    def _generate_citation(self, document_title: str, page_number: Optional[int], 
                          line_range: Optional[Dict[str, int]]) -> str:
        """Generate academic-style citation for the source"""
        try:
            # Base citation with document name
            citation_parts = [document_title] if document_title else ["Kaynak"]
            
            # Add page reference
            if page_number:
                citation_parts.append(f"s. {page_number}")
            
            # Add line range
            if line_range:
                line_ref = f"satır {line_range['start']}"
                if line_range['end'] != line_range['start']:
                    line_ref += f"-{line_range['end']}"
                citation_parts.append(line_ref)
            
            return ", ".join(citation_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate citation: {e}")
            return document_title or "Kaynak belirtilmemiş"
    
    def _generate_content_preview(self, content: str, max_length: int = 150) -> str:
        """Generate a preview of the content for reference"""
        try:
            if not content:
                return ""
            
            # Clean and truncate content
            cleaned = content.strip().replace('\n', ' ').replace('\r', ' ')
            
            # Remove extra spaces
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            # Truncate with ellipsis
            if len(cleaned) > max_length:
                preview = cleaned[:max_length].rsplit(' ', 1)[0] + "..."
            else:
                preview = cleaned
            
            return preview
            
        except Exception as e:
            logger.error(f"Failed to generate content preview: {e}")
            return content[:100] + "..." if content else ""
    
    def format_sources_for_response(self, enhanced_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format enhanced results for API response"""
        try:
            formatted_sources = []
            
            for result in enhanced_results:
                source = {
                    "document_title": result.get("document_title", "Belge adı bilinmiyor"),
                    "pdf_url": result.get("pdf_url"),
                    "page_number": result.get("page_number"),
                    "line_start": result.get("line_start"),
                    "line_end": result.get("line_end"),
                    "citation": result.get("citation", ""),
                    "content_preview": result.get("content_preview", ""),
                    "similarity_score": result.get("similarity_score", 0.0),
                    "chunk_index": result.get("chunk_index", 0),
                    "source_institution": result.get("source_institution", ""),
                    "category": result.get("category", "")
                }
                
                # Handle PDF URL - try to generate from filename if null
                if source.get("pdf_url") is None:
                    document_title = source.get('document_title', 'Unknown')
                    if document_title and document_title != 'Unknown' and '.' in document_title:
                        # Generate CDN URL from document title (which is filename)
                        generated_url = f"https://cdn.mevzuatgpt.org/documents/{document_title}"
                        source["pdf_url"] = generated_url
                        logger.info(f"🔧 Final fallback: Generated CDN URL for {document_title}: {generated_url}")
                
                # Keep PDF URL even if None for debugging, but remove other nulls
                filtered_source = {}
                for k, v in source.items():
                    if k == "pdf_url":
                        filtered_source[k] = v  # Always include pdf_url
                        if v is None:
                            logger.warning(f"PDF URL is null for source: {source.get('document_title', 'Unknown')}")
                    elif v is not None:
                        filtered_source[k] = v
                
                formatted_sources.append(filtered_source)
            
            return formatted_sources
            
        except Exception as e:
            logger.error(f"Failed to format sources for response: {e}")
            return []
    
    def get_source_statistics(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about the sources"""
        try:
            if not sources:
                return {"total_sources": 0}
            
            # Count unique documents
            unique_docs = len(set(s.get("document_title", "") for s in sources))
            
            # Count sources with page numbers
            sources_with_pages = sum(1 for s in sources if s.get("page_number"))
            
            # Count sources with PDF URLs
            sources_with_urls = sum(1 for s in sources if s.get("pdf_url"))
            
            # Calculate average similarity
            similarities = [s.get("similarity_score", 0) for s in sources]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            return {
                "total_sources": len(sources),
                "unique_documents": unique_docs,
                "sources_with_page_numbers": sources_with_pages,
                "sources_with_pdf_urls": sources_with_urls,
                "average_similarity": round(avg_similarity, 3)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate source statistics: {e}")
            return {"total_sources": len(sources) if sources else 0}
    
    def _convert_to_public_cdn_url(self, file_url: Optional[str]) -> Optional[str]:
        """
        Convert database file_url to public CDN URL with cdn.mevzuatgpt.org format
        Format: https://cdn.mevzuatgpt.org/documents/{document_id}.pdf
        
        Args:
            file_url: Original file URL from database
            
        Returns:
            Public CDN URL starting with cdn.mevzuatgpt.org/documents/
        """
        if not file_url:
            return None
            
        try:
            # If already a public CDN URL, return as is
            if file_url.startswith('https://cdn.mevzuatgpt.org'):
                logger.debug(f"✅ Already public CDN URL: {file_url[:50]}")
                return file_url
            
            # If it's a Bunny.net storage URL, convert to public CDN
            if 'b-cdn.net' in file_url or 'bunny' in file_url.lower():
                # Extract filename from the URL
                filename = file_url.split('/')[-1]
                public_url = f"https://cdn.mevzuatgpt.org/documents/{filename}"
                logger.info(f"🔄 Converted Bunny URL to public CDN: {file_url[:30]} → {public_url[:50]}")
                return public_url
            
            # If it's just a filename/path, construct the full CDN URL
            if not file_url.startswith('http'):
                # Remove leading slash if present
                clean_path = file_url.lstrip('/')
                # If path doesn't include 'documents/', add it
                if not clean_path.startswith('documents/'):
                    clean_path = f"documents/{clean_path}"
                public_url = f"https://cdn.mevzuatgpt.org/{clean_path}"
                logger.info(f"🔄 Constructed CDN URL from path: {file_url} → {public_url}")
                return public_url
            
            # For other URLs, try to extract filename and construct CDN URL
            if '/' in file_url:
                filename = file_url.split('/')[-1]
                if filename and '.' in filename:  # Make sure it's a valid filename
                    public_url = f"https://cdn.mevzuatgpt.org/documents/{filename}"
                    logger.info(f"🔄 Extracted filename for CDN URL: {filename} → {public_url}")
                    return public_url
            
            logger.warning(f"❌ Could not convert URL to public CDN format: {file_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error converting URL to public CDN format: {e}")
            return None