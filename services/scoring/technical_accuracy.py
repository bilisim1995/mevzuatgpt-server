"""
Technical Accuracy Scoring Module
Assesses legal terminology and technical detail accuracy
"""

from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


class TechnicalAccuracyScorer:
    """
    Evaluates technical accuracy based on:
    - Legal terminology usage
    - Reference to articles, laws, regulations
    - Date and numerical accuracy
    """
    
    def __init__(self):
        self.weight = 25  # 25% of total score
        
        # Legal terminology indicators
        self.legal_terms = {
            'kanun', 'yönetmelik', 'tebliğ', 'genelge', 'madde', 'fıkra', 'bent',
            'uyarınca', 'göre', 'kapsamında', 'hükümleri', 'düzenlemesi',
            'mevzuat', 'yürürlük', 'resmi gazete', 'sayılı', 'tarihli'
        }
        
        # Formal language indicators
        self.formal_indicators = {
            'belirtilen', 'düzenlenen', 'öngörülen', 'belirlenen', 'sağlanan',
            'yapılacak', 'olacaktır', 'bulunmaktadır', 'edilmektedir'
        }
    
    def calculate_score(self, search_results: List[Dict[str, Any]], 
                       ai_answer: str) -> Dict[str, Any]:
        """
        Calculate technical accuracy score
        
        Args:
            search_results: List of search results from Supabase
            ai_answer: Generated AI response
            
        Returns:
            Dict with score, details and explanation
        """
        try:
            if not ai_answer:
                return self._fallback_result()
            
            # Calculate sub-scores
            terminology_score = self._calculate_terminology_score(ai_answer)
            reference_score = self._calculate_reference_score(ai_answer, search_results)
            formal_score = self._calculate_formal_language_score(ai_answer)
            
            # Weighted average
            final_score = int((terminology_score * 0.4 + reference_score * 0.4 + formal_score * 0.2))
            
            # Generate details
            details = self._generate_details(terminology_score, reference_score, formal_score, ai_answer)
            
            return {
                "score": final_score,
                "weight": self.weight,
                "description": "Hukuki terminoloji ve teknik detayların doğruluğu",
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Technical accuracy calculation failed: {e}")
            return self._fallback_result()
    
    def _calculate_terminology_score(self, answer: str) -> float:
        """Score based on legal terminology usage"""
        if not answer:
            return 0.0
        
        answer_lower = answer.lower()
        terminology_count = 0
        
        for term in self.legal_terms:
            if term in answer_lower:
                terminology_count += 1
        
        # Score based on terminology density
        if terminology_count >= 5:
            return 100.0
        elif terminology_count >= 3:
            return 85.0
        elif terminology_count >= 2:
            return 70.0
        elif terminology_count >= 1:
            return 60.0
        else:
            return 30.0  # Low terminology usage
    
    def _calculate_reference_score(self, answer: str, search_results: List[Dict[str, Any]]) -> float:
        """Score based on specific legal references"""
        if not answer:
            return 0.0
        
        score = 50.0  # Base score
        answer_lower = answer.lower()
        
        # Check for article references
        article_patterns = [
            r'madde\s*\d+', r'md\.\s*\d+', r'\d+\.\s*madde',
            r'fıkra\s*\d+', r'\d+\.\s*fıkra'
        ]
        
        article_count = 0
        for pattern in article_patterns:
            matches = re.findall(pattern, answer_lower)
            article_count += len(matches)
        
        if article_count >= 2:
            score += 30
        elif article_count >= 1:
            score += 20
        
        # Check for law/regulation numbers
        law_patterns = [
            r'\d{4}\s*sayılı', r'kanun\s*no\s*\d+', r'yönetmelik\s*no\s*\d+'
        ]
        
        law_count = 0
        for pattern in law_patterns:
            matches = re.findall(pattern, answer_lower)
            law_count += len(matches)
        
        if law_count >= 1:
            score += 20
        
        # Check for date references
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}', r'\d{1,2}\.\d{1,2}\.\d{4}',
            r'\d{4}\s*yılı', r'\d{1,2}\s*(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)'
        ]
        
        date_count = 0
        for pattern in date_patterns:
            matches = re.findall(pattern, answer_lower)
            date_count += len(matches)
        
        if date_count >= 1:
            score += 10
        
        return min(score, 100.0)
    
    def _calculate_formal_language_score(self, answer: str) -> float:
        """Score based on formal language usage"""
        if not answer:
            return 0.0
        
        answer_lower = answer.lower()
        formal_count = 0
        
        for indicator in self.formal_indicators:
            if indicator in answer_lower:
                formal_count += 1
        
        # Check for formal sentence structures
        formal_structures = [
            'edilmektedir', 'yapılmaktadır', 'bulunmaktadır', 'olacaktır',
            'gerekmektedir', 'sağlanmaktadır'
        ]
        
        structure_count = 0
        for structure in formal_structures:
            if structure in answer_lower:
                structure_count += 1
        
        # Combined scoring
        total_formal_elements = formal_count + structure_count
        
        if total_formal_elements >= 3:
            return 100.0
        elif total_formal_elements >= 2:
            return 80.0
        elif total_formal_elements >= 1:
            return 60.0
        else:
            return 40.0
    
    def _generate_details(self, terminology: float, reference: float, 
                         formal: float, answer: str) -> List[str]:
        """Generate human-readable details"""
        details = []
        
        # Terminology detail
        if terminology >= 85:
            details.append("Zengin hukuki terminoloji")
        elif terminology >= 60:
            details.append("Yeterli terim kullanımı")
        else:
            details.append("Sınırlı terminoloji")
        
        # Reference detail
        if reference >= 80:
            details.append("Detaylı madde referansları")
        elif reference >= 60:
            details.append("Bazı yasal referanslar")
        else:
            details.append("Sınırlı referans bilgisi")
        
        # Formal language detail
        if formal >= 80:
            details.append("Resmi hukuki dil")
        elif formal >= 60:
            details.append("Formal ifade tarzı")
        else:
            details.append("Günlük dil kullanımı")
        
        return details
    
    def _fallback_result(self) -> Dict[str, Any]:
        """Fallback result in case of error"""
        return {
            "score": 50,
            "weight": self.weight,
            "description": "Hukuki terminoloji ve teknik detayların doğruluğu",
            "details": ["Teknik doğruluk değerlendirilemedi"]
        }