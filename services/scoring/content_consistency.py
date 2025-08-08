"""
Content Consistency Scoring Module
Assesses answer-source alignment and internal consistency
"""

from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


class ContentConsistencyScorer:
    """
    Evaluates content consistency based on:
    - Answer-source text alignment
    - Answer completeness
    - Internal coherence indicators
    """
    
    def __init__(self):
        self.weight = 25  # 25% of total score
        
        # Turkish stop words for filtering
        self.stop_words = {
            'bir', 'bu', 'şu', 've', 'ile', 'için', 'de', 'da', 'den', 'dan',
            'ın', 'in', 'un', 'ün', 'a', 'e', 'i', 'ı', 'o', 'ö', 'u', 'ü',
            'olan', 'olan', 'olarak', 'göre', 'kadar', 'gibi', 'daha', 'en'
        }
    
    def calculate_score(self, search_results: List[Dict[str, Any]], 
                       ai_answer: str) -> Dict[str, Any]:
        """
        Calculate content consistency score
        
        Args:
            search_results: List of search results from Supabase
            ai_answer: Generated AI response
            
        Returns:
            Dict with score, details and explanation
        """
        try:
            if not search_results or not ai_answer:
                return self._fallback_result()
            
            # Combine all source contexts
            combined_context = self._combine_contexts(search_results)
            
            # Calculate sub-scores
            alignment_score = self._calculate_alignment_score(combined_context, ai_answer)
            completeness_score = self._calculate_completeness_score(ai_answer)
            coherence_score = self._calculate_coherence_score(ai_answer)
            
            # Weighted average
            final_score = int((alignment_score * 0.5 + completeness_score * 0.3 + coherence_score * 0.2))
            
            # Generate details
            details = self._generate_details(alignment_score, completeness_score, coherence_score, ai_answer)
            
            return {
                "score": final_score,
                "weight": self.weight,
                "description": "Yanıtın iç tutarlılığı ve mantıksal bütünlüğü",
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Content consistency calculation failed: {e}")
            return self._fallback_result()
    
    def _combine_contexts(self, search_results: List[Dict[str, Any]]) -> str:
        """Combine all source contexts into single text"""
        contexts = []
        for result in search_results:
            content = result.get("content", "")
            if content and len(content.strip()) > 10:
                contexts.append(content.strip())
        
        return " ".join(contexts)
    
    def _calculate_alignment_score(self, context: str, answer: str) -> float:
        """Calculate how well answer aligns with source context"""
        if not context or not answer:
            return 0.0
        
        # Normalize texts
        context_clean = self._normalize_text(context)
        answer_clean = self._normalize_text(answer)
        
        # Extract keywords (excluding stop words)
        context_words = self._extract_keywords(context_clean)
        answer_words = self._extract_keywords(answer_clean)
        
        if not context_words or not answer_words:
            return 50.0  # Neutral score if can't analyze
        
        # Calculate intersection ratio
        intersection = context_words.intersection(answer_words)
        alignment_ratio = len(intersection) / len(answer_words) if answer_words else 0
        
        return min(alignment_ratio * 100, 100.0)
    
    def _calculate_completeness_score(self, answer: str) -> float:
        """Score based on answer completeness indicators"""
        if not answer:
            return 0.0
        
        answer_length = len(answer.strip())
        
        # Length-based scoring
        if answer_length >= 200:
            length_score = 100.0
        elif answer_length >= 100:
            length_score = 80.0
        elif answer_length >= 50:
            length_score = 60.0
        else:
            length_score = 30.0
        
        # Check for completeness indicators
        completeness_bonus = 0
        
        # Positive indicators
        if any(phrase in answer.lower() for phrase in ['göre', 'uyarınca', 'kapsamında', 'belirtilen']):
            completeness_bonus += 10
        
        if any(phrase in answer.lower() for phrase in ['madde', 'fıkra', 'bent', 'kanun']):
            completeness_bonus += 10
        
        # Negative indicators
        if any(phrase in answer.lower() for phrase in ['bilgi yok', 'bulunamadı', 'belirtilmemiş']):
            completeness_bonus -= 20
        
        final_score = length_score + completeness_bonus
        return max(0, min(final_score, 100.0))
    
    def _calculate_coherence_score(self, answer: str) -> float:
        """Score based on internal coherence indicators"""
        if not answer:
            return 0.0
        
        coherence_score = 70.0  # Base score
        
        # Sentence structure check
        sentences = [s.strip() for s in re.split(r'[.!?]+', answer) if s.strip()]
        
        if len(sentences) >= 2:
            coherence_score += 15  # Multi-sentence structure
        
        # Check for connecting words
        connectors = ['ancak', 'fakat', 'lakin', 'ayrıca', 'buna göre', 'bu nedenle', 'dolayısıyla']
        if any(conn in answer.lower() for conn in connectors):
            coherence_score += 10
        
        # Check for contradictions (simple)
        contradictions = ['ama', 'fakat', 'ancak', 'lakin']
        contradiction_count = sum(1 for cont in contradictions if answer.lower().count(cont) > 1)
        if contradiction_count > 2:
            coherence_score -= 15  # Too many contradictions
        
        return max(0, min(coherence_score, 100.0))
    
    def _normalize_text(self, text: str) -> str:
        """Normalize Turkish text for comparison"""
        if not text:
            return ""
        
        # Convert to lowercase and handle Turkish characters
        text = text.lower()
        text = text.replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u')
        text = text.replace('ş', 's').replace('ö', 'o').replace('ç', 'c')
        
        # Remove punctuation and extra spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text"""
        if not text:
            return set()
        
        words = text.split()
        keywords = set()
        
        for word in words:
            # Filter out stop words and short words
            if len(word) >= 3 and word not in self.stop_words:
                keywords.add(word)
        
        return keywords
    
    def _generate_details(self, alignment: float, completeness: float, 
                         coherence: float, answer: str) -> List[str]:
        """Generate human-readable details"""
        details = []
        
        # Alignment detail
        if alignment >= 80:
            details.append("Kaynaklara uygun içerik")
        elif alignment >= 60:
            details.append("Kaynaklarla kısmen uyumlu")
        else:
            details.append("Kaynaklarla sınırlı uyum")
        
        # Completeness detail
        if completeness >= 80:
            details.append("Kapsamlı ve detaylı yanıt")
        elif completeness >= 60:
            details.append("Yeterli düzeyde açıklama")
        else:
            details.append("Kısa ve sınırlı açıklama")
        
        # Coherence detail
        if coherence >= 80:
            details.append("Mantıksal bütünlük mevcut")
        elif coherence >= 60:
            details.append("Genel olarak tutarlı")
        else:
            details.append("Tutarlılık sorunları mevcut")
        
        return details
    
    def _fallback_result(self) -> Dict[str, Any]:
        """Fallback result in case of error"""
        return {
            "score": 50,
            "weight": self.weight,
            "description": "Yanıtın iç tutarlılığı ve mantıksal bütünlüğü",
            "details": ["İçerik tutarlılığı değerlendirilemedi"]
        }