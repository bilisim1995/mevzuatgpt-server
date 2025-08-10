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
            document_data = self._batch_fetch_document_urls(search_results)
            
            for result in search_results:
                # Debug: Check what's in each result before enhancement
                document_id = result.get("document_id")
                logger.info(f"Processing result with document_id: {document_id}")
                
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
            
            # Debug logging
            logger.info(f"Enhancing result: document_id={document_id}, title={document_title[:30]}")
            
            # Make sure document_id is preserved in enhanced result
            if document_id:
                enhanced["document_id"] = document_id
            
            # Add PDF URL and metadata from pre-fetched cache or database
            if document_data and isinstance(document_data, dict):
                document_urls = document_data.get('urls', {})
                document_metadata = document_data.get('metadata', {})
                
                if document_id and document_id in document_urls:
                    pdf_url = document_urls[document_id]
                    enhanced["pdf_url"] = pdf_url
                
                # Add metadata information - make sure document_id is present
                if document_id and document_id in document_metadata:
                    metadata = document_metadata[document_id]
                    if isinstance(metadata, dict):
                        enhanced["source_institution"] = metadata.get("source_institution", "")
                        enhanced["category"] = metadata.get("category", "")
                        enhanced["keywords"] = metadata.get("keywords", [])
                        # Debug log
                        logger.debug(f"Added metadata for {document_id}: institution={metadata.get('source_institution')}")
                elif document_id:
                    logger.warning(f"No metadata found for document_id: {document_id}")
                else:
                    logger.warning("Missing document_id in search result")
            else:
                if document_id:
                    pdf_url = self._get_pdf_url_from_db(document_id)
                    enhanced["pdf_url"] = pdf_url
            
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
            
            # Set final values
            if page_number:
                enhanced["page_number"] = page_number
            if line_start:
                enhanced["line_start"] = line_start
            if line_end:
                enhanced["line_end"] = line_end
            
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
            
            if not document_ids:
                return {}
                
            from models.supabase_client import supabase_client
            
            # Batch query for all document URLs and metadata
            result = supabase_client.supabase.table('mevzuat_documents') \
                .select('id, file_url, metadata') \
                .in_('id', document_ids) \
                .execute()
            
            # Create lookup dictionary with URLs and metadata
            url_map = {}
            metadata_map = {}
            if result.data:
                for doc in result.data:
                    url_map[doc['id']] = doc.get('file_url')
                    metadata_map[doc['id']] = doc.get('metadata', {})
            
            logger.debug(f"Batch fetched URLs for {len(url_map)} documents")
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
            
            # Query document table for file_url
            result = supabase_client.supabase.table('mevzuat_documents') \
                .select('file_url') \
                .eq('id', document_id) \
                .single() \
                .execute()
            
            if result.data and result.data.get('file_url'):
                return result.data['file_url']
            
            logger.warning(f"No file_url found for document {document_id}")
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
                # Conservative estimate: assume ~8 chunks per page (more realistic for legal documents)
                estimated_page = (chunk_index // 8) + 1
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
            
            # Realistic line calculation for sequential chunks (0,1,2,3...)
            # Conservative estimate: each chunk represents ~5-8 lines of original document
            lines_per_chunk = 6  # Conservative estimate
            estimated_start = (chunk_index * lines_per_chunk) + 1
            estimated_end = estimated_start + max(3, min(content_lines, 8)) - 1  # Cap at reasonable range
            
            return {
                "start": max(1, estimated_start),
                "end": max(estimated_start, estimated_end)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate line range: {e}")
            return None
    
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
                    "chunk_index": result.get("chunk_index", 0)
                }
                
                # Keep PDF URL even if None for debugging, but remove other nulls
                filtered_source = {}
                for k, v in source.items():
                    if k == "pdf_url":
                        filtered_source[k] = v  # Always include pdf_url, even if None
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