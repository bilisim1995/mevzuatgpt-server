"""
Currency Scoring Module  
Assesses information currency and relevance to current legislation
"""

from typing import List, Dict, Any
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class CurrencyScorer:
    """
    Evaluates information currency based on:
    - Document publication dates
    - Current legislation references
    - Recent updates and amendments
    """
    
    def __init__(self):
        self.weight = 20  # 20% of total score
        self.current_year = datetime.now().year
        
        # Currency indicators
        self.current_indicators = {
            'güncel', 'yürürlük', 'yürürlükte', 'geçerli', 'mevcut',
            'son değişiklik', 'değişiklik', 'güncellenmiş', 'revize'
        }
        
        # Outdated indicators
        self.outdated_indicators = {
            'yürürlükten', 'mülga', 'iptal', 'değiştirilmiş', 'kaldırılmış'
        }
    
    def calculate_score(self, search_results: List[Dict[str, Any]], 
                       ai_answer: str) -> Dict[str, Any]:
        """
        Calculate currency score
        
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
            document_currency = self._calculate_document_currency(search_results)
            content_currency = self._calculate_content_currency(ai_answer)
            legislation_currency = self._calculate_legislation_currency(ai_answer)
            
            # Weighted average
            final_score = int((document_currency * 0.4 + content_currency * 0.3 + legislation_currency * 0.3))
            
            # Generate details
            details = self._generate_details(document_currency, content_currency, 
                                           legislation_currency, search_results, ai_answer)
            
            return {
                "score": final_score,
                "weight": self.weight,
                "description": "Bilgilerin güncel mevzuata uygunluğu",
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Currency calculation failed: {e}")
            return self._fallback_result()
    
    def _calculate_document_currency(self, search_results: List[Dict[str, Any]]) -> float:
        """Score based on document publication dates"""
        if not search_results:
            return 50.0  # Neutral score if no sources
        
        years = []
        
        for result in search_results:
            # Try to extract year from various fields
            publish_date = result.get('publish_date', '')
            document_title = result.get('document_title', '')
            
            year = self._extract_year(publish_date)
            if not year:
                year = self._extract_year(document_title)
            if year:
                years.append(year)
        
        if not years:
            return 60.0  # Moderate score if can't determine dates
        
        # Calculate score based on average document age
        avg_year = sum(years) / len(years)
        year_diff = self.current_year - avg_year
        
        if year_diff <= 1:
            return 100.0  # Very recent
        elif year_diff <= 3:
            return 90.0   # Recent
        elif year_diff <= 5:
            return 80.0   # Moderately recent
        elif year_diff <= 10:
            return 60.0   # Older but acceptable
        else:
            return 30.0   # Old documents
    
    def _calculate_content_currency(self, answer: str) -> float:
        """Score based on currency indicators in the answer"""
        if not answer:
            return 0.0
        
        answer_lower = answer.lower()
        score = 60.0  # Base score
        
        # Check for current indicators
        current_count = 0
        for indicator in self.current_indicators:
            if indicator in answer_lower:
                current_count += 1
        
        if current_count >= 2:
            score += 30
        elif current_count >= 1:
            score += 20
        
        # Check for outdated indicators (negative score)
        outdated_count = 0
        for indicator in self.outdated_indicators:
            if indicator in answer_lower:
                outdated_count += 1
        
        if outdated_count >= 1:
            score -= 25
        
        # Check for recent year mentions
        recent_year_pattern = rf'({self.current_year}|{self.current_year-1}|{self.current_year-2})'
        recent_years = re.findall(recent_year_pattern, answer)
        
        if len(recent_years) >= 1:
            score += 15
        
        return max(0, min(score, 100.0))
    
    def _calculate_legislation_currency(self, answer: str) -> float:
        """Score based on current legislation references"""
        if not answer:
            return 0.0
        
        answer_lower = answer.lower()
        score = 50.0  # Base score
        
        # Check for "current law" patterns
        current_law_patterns = [
            r'\d{4}\s*sayılı.*kanun', r'yürürlükteki.*kanun',
            r'güncel.*yönetmelik', r'mevcut.*düzenleme'
        ]
        
        current_law_count = 0
        for pattern in current_law_patterns:
            matches = re.findall(pattern, answer_lower)
            current_law_count += len(matches)
        
        if current_law_count >= 2:
            score += 35
        elif current_law_count >= 1:
            score += 25
        
        # Check for amendment references
        amendment_patterns = [
            r'değiştirilen.*madde', r'eklenen.*fıkra', r'son.*değişiklik'
        ]
        
        amendment_count = 0
        for pattern in amendment_patterns:
            matches = re.findall(pattern, answer_lower)
            amendment_count += len(matches)
        
        if amendment_count >= 1:
            score += 15
        
        return min(score, 100.0)
    
    def _extract_year(self, text: str) -> int | None:
        """Extract year from text"""
        if not text:
            return None
        
        # Look for 4-digit years between 1990 and current year + 5
        year_pattern = r'\b(19[9]\d|20[0-4]\d)\b'
        matches = re.findall(year_pattern, text)
        
        if matches:
            years = [int(year) for year in matches if 1990 <= int(year) <= self.current_year + 5]
            return max(years) if years else None
        
        return None
    
    def _generate_details(self, doc_currency: float, content_currency: float,
                         legislation_currency: float, search_results: List[Dict[str, Any]],
                         answer: str) -> List[str]:
        """Generate human-readable details"""
        details = []
        
        # Document currency detail
        if doc_currency >= 90:
            details.append(f"{self.current_year} yılı mevzuatı")
        elif doc_currency >= 70:
            details.append("Son 3 yıl içerisindeki düzenlemeler")
        elif doc_currency >= 50:
            details.append("Görece güncel mevzuat")
        else:
            details.append("Eski tarihli mevzuat")
        
        # Content currency detail
        if content_currency >= 80:
            details.append("Güncel ifadeler kullanılmış")
        elif content_currency >= 60:
            details.append("Genel olarak güncel içerik")
        else:
            details.append("Güncellik belirsiz")
        
        # Legislation currency detail
        if legislation_currency >= 80:
            details.append("Yürürlükteki düzenlemeler referans alınmış")
        elif legislation_currency >= 60:
            details.append("Mevcut kanunlara atıf var")
        else:
            details.append("Sınırlı güncel referans")
        
        return details
    
    def _fallback_result(self) -> Dict[str, Any]:
        """Fallback result in case of error"""
        return {
            "score": 60,
            "weight": self.weight,
            "description": "Bilgilerin güncel mevzuata uygunluğu",
            "details": ["Güncellik değerlendirilemedi"]
        }