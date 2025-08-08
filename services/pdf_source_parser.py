"""
PDF Source Parser - Enhanced PDF parsing with source tracking
Extracts text with page numbers, line ranges, and source metadata
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
import pdfplumber
from io import BytesIO

logger = logging.getLogger(__name__)


class PDFSourceParser:
    """
    Enhanced PDF parser that tracks source information
    Extracts text with page numbers and line positions for better referencing
    """
    
    def __init__(self):
        self.chunk_size = 500  # Characters per chunk
        self.overlap_size = 50  # Overlap between chunks
    
    def parse_pdf_with_sources(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Parse PDF content and extract text with detailed source information
        
        Args:
            pdf_content: PDF file content as bytes
            filename: Name of the PDF file
            
        Returns:
            Dict with parsed text chunks and source metadata
        """
        try:
            logger.info(f"Starting enhanced PDF parsing for: {filename}")
            
            # Parse PDF pages
            pages_data = self._extract_pages_with_metadata(pdf_content)
            
            if not pages_data:
                logger.warning(f"No text extracted from PDF: {filename}")
                return {"chunks": [], "total_pages": 0, "total_text_length": 0}
            
            # Create text chunks with source information
            chunks = self._create_chunks_with_sources(pages_data, filename)
            
            # Calculate statistics
            total_text = "".join(page["text"] for page in pages_data)
            
            result = {
                "chunks": chunks,
                "total_pages": len(pages_data),
                "total_text_length": len(total_text),
                "filename": filename,
                "parsing_success": True
            }
            
            logger.info(f"Successfully parsed PDF: {len(chunks)} chunks from {len(pages_data)} pages")
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse PDF {filename}: {e}")
            return {
                "chunks": [],
                "total_pages": 0,
                "total_text_length": 0,
                "filename": filename,
                "parsing_success": False,
                "error": str(e)
            }
    
    def _extract_pages_with_metadata(self, pdf_content: bytes) -> List[Dict[str, Any]]:
        """Extract text from each page with metadata"""
        pages_data = []
        
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Extract text from page
                        page_text = page.extract_text()
                        
                        if page_text and page_text.strip():
                            # Clean and process text
                            cleaned_text = self._clean_text(page_text)
                            
                            # Split into lines for line tracking
                            lines = cleaned_text.split('\n')
                            
                            page_data = {
                                "page_number": page_num,
                                "text": cleaned_text,
                                "lines": lines,
                                "line_count": len(lines),
                                "char_count": len(cleaned_text)
                            }
                            
                            pages_data.append(page_data)
                            
                        else:
                            logger.warning(f"Empty text on page {page_num}")
                            
                    except Exception as e:
                        logger.error(f"Error processing page {page_num}: {e}")
                        continue
            
            return pages_data
            
        except Exception as e:
            logger.error(f"Error opening PDF: {e}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text while preserving line structure"""
        if not text:
            return ""
        
        # Split into lines first to preserve structure
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            if not line.strip():
                continue
            
            # Remove excessive whitespace within line
            cleaned_line = re.sub(r'\s+', ' ', line.strip())
            
            # Skip page headers/footers
            if re.match(r'^[-\s]*\d+[-\s]*$', cleaned_line):
                continue
            if re.match(r'^[-\s]*Sayfa\s+\d+[-\s]*$', cleaned_line):
                continue
            
            # Fix common OCR issues
            cleaned_line = cleaned_line.replace('‚', ',').replace('"', '"').replace('"', '"')
            cleaned_line = cleaned_line.replace(''', "'").replace(''', "'")
            
            # Normalize Turkish characters  
            cleaned_line = cleaned_line.replace('ı', 'ı').replace('İ', 'İ')
            
            if cleaned_line:  # Only add non-empty lines
                cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def _create_chunks_with_sources(self, pages_data: List[Dict[str, Any]], 
                                   filename: str) -> List[Dict[str, Any]]:
        """Create text chunks with detailed source tracking"""
        chunks = []
        chunk_index = 0
        
        for page_data in pages_data:
            page_number = page_data["page_number"]
            page_text = page_data["text"]
            page_lines = page_data["lines"]
            
            # Process page text into chunks
            page_chunks = self._chunk_page_text(page_text, page_lines, page_number)
            
            for chunk_data in page_chunks:
                chunk = {
                    "chunk_index": chunk_index,
                    "content": chunk_data["content"],
                    "page_number": page_number,
                    "line_start": chunk_data["line_start"],
                    "line_end": chunk_data["line_end"],
                    "char_start": chunk_data["char_start"],
                    "char_end": chunk_data["char_end"],
                    "filename": filename,
                    "source_metadata": {
                        "extraction_method": "pdfplumber",
                        "page_total_lines": len(page_lines),
                        "chunk_word_count": len(chunk_data["content"].split()),
                        "has_legal_terms": self._detect_legal_terms(chunk_data["content"])
                    }
                }
                
                chunks.append(chunk)
                chunk_index += 1
        
        return chunks
    
    def _chunk_page_text(self, page_text: str, page_lines: List[str], 
                        page_number: int) -> List[Dict[str, Any]]:
        """Split page text into chunks with line tracking"""
        chunks = []
        
        if not page_text or not page_lines:
            return chunks
        
        # Calculate character positions for each line in the cleaned page text
        line_positions = []
        current_pos = 0
        
        # Use the actual page_text (cleaned) to calculate positions
        actual_lines = page_text.split('\n')
        
        for i, line in enumerate(actual_lines):
            line_start = current_pos
            line_end = current_pos + len(line)
            line_positions.append({
                "line_number": i + 1,
                "start_pos": line_start,
                "end_pos": line_end,
                "text": line
            })
            current_pos = line_end + 1  # +1 for newline character
        
        # Create chunks based on character size
        text_length = len(page_text)
        start_pos = 0
        
        while start_pos < text_length:
            end_pos = min(start_pos + self.chunk_size, text_length)
            
            # Adjust to word boundaries
            if end_pos < text_length:
                # Find the last space within the chunk
                space_pos = page_text.rfind(' ', start_pos, end_pos)
                if space_pos > start_pos:
                    end_pos = space_pos
            
            # Extract chunk content
            chunk_content = page_text[start_pos:end_pos].strip()
            
            if chunk_content:
                # Find corresponding lines
                line_range = self._find_lines_for_chunk(start_pos, end_pos, line_positions)
                
                chunk_data = {
                    "content": chunk_content,
                    "char_start": start_pos,
                    "char_end": end_pos,
                    "line_start": line_range["start"],
                    "line_end": line_range["end"]
                }
                
                chunks.append(chunk_data)
            
            # Move to next chunk with overlap
            start_pos = max(start_pos + self.chunk_size - self.overlap_size, end_pos)
        
        return chunks
    
    def _find_lines_for_chunk(self, char_start: int, char_end: int, 
                             line_positions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Find which lines correspond to a character range"""
        start_line = 1
        end_line = 1
        
        for line_pos in line_positions:
            # Check if chunk starts within this line
            if char_start >= line_pos["start_pos"] and char_start <= line_pos["end_pos"]:
                start_line = line_pos["line_number"]
            
            # Check if chunk ends within this line
            if char_end >= line_pos["start_pos"] and char_end <= line_pos["end_pos"]:
                end_line = line_pos["line_number"]
        
        return {"start": start_line, "end": max(start_line, end_line)}
    
    def _detect_legal_terms(self, text: str) -> bool:
        """Detect if chunk contains legal terminology"""
        legal_terms = [
            "madde", "fıkra", "bent", "kanun", "yönetmelik", "tebliğ",
            "genelge", "uyarınca", "göre", "kapsamında", "hükümleri",
            "mevzuat", "yürürlük", "resmi gazete"
        ]
        
        text_lower = text.lower()
        return any(term in text_lower for term in legal_terms)
    
    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about parsed chunks"""
        if not chunks:
            return {"total_chunks": 0}
        
        total_chunks = len(chunks)
        pages_covered = len(set(chunk["page_number"] for chunk in chunks))
        legal_chunks = sum(1 for chunk in chunks 
                          if chunk.get("source_metadata", {}).get("has_legal_terms", False))
        
        avg_chunk_size = sum(len(chunk["content"]) for chunk in chunks) / total_chunks
        
        return {
            "total_chunks": total_chunks,
            "pages_covered": pages_covered,
            "chunks_with_legal_terms": legal_chunks,
            "legal_content_percentage": round((legal_chunks / total_chunks) * 100, 1),
            "average_chunk_size": round(avg_chunk_size, 1)
        }