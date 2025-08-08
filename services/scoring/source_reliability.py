"""
Source Reliability Scoring Module
Assesses the quality, quantity and diversity of sources
"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SourceReliabilityScorer:
    """
    Evaluates source reliability based on:
    - Number of sources found
    - Similarity scores quality
    - Source diversity (different documents)
    """
    
    def __init__(self):
        self.weight = 30  # 30% of total score
        
    def calculate_score(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate source reliability score
        
        Args:
            search_results: List of search results from Supabase
            
        Returns:
            Dict with score, details and explanation
        """
        try:
            if not search_results:
                return self._no_sources_result()
            
            # Calculate sub-scores
            quantity_score = self._calculate_quantity_score(search_results)
            similarity_score = self._calculate_similarity_score(search_results)
            diversity_score = self._calculate_diversity_score(search_results)
            
            # Weighted average of sub-scores
            final_score = int((quantity_score * 0.3 + similarity_score * 0.4 + diversity_score * 0.3))
            
            # Generate details
            details = self._generate_details(search_results, quantity_score, similarity_score, diversity_score)
            
            return {
                "score": final_score,
                "weight": self.weight,
                "description": "Resmi kaynaklar, mevzuat metinleri ve güvenilir referansların kullanımı",
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Source reliability calculation failed: {e}")
            return self._fallback_result()
    
    def _calculate_quantity_score(self, search_results: List[Dict[str, Any]]) -> float:
        """Score based on number of sources found"""
        count = len(search_results)
        
        if count >= 5:
            return 100.0
        elif count >= 3:
            return 85.0
        elif count >= 2:
            return 70.0
        elif count == 1:
            return 50.0
        else:
            return 0.0
    
    def _calculate_similarity_score(self, search_results: List[Dict[str, Any]]) -> float:
        """Score based on average similarity scores"""
        similarities = []
        
        for result in search_results:
            similarity = result.get("similarity_score", 0.0)
            if similarity > 0:
                similarities.append(similarity)
        
        if not similarities:
            return 0.0
        
        avg_similarity = sum(similarities) / len(similarities)
        return min(avg_similarity * 100, 100.0)
    
    def _calculate_diversity_score(self, search_results: List[Dict[str, Any]]) -> float:
        """Score based on source diversity (different documents)"""
        document_ids = set()
        
        for result in search_results:
            doc_id = result.get("document_id")
            if doc_id:
                document_ids.add(doc_id)
        
        unique_docs = len(document_ids)
        total_results = len(search_results)
        
        if unique_docs == total_results:
            return 100.0  # All from different documents
        elif unique_docs >= total_results * 0.7:
            return 85.0   # Most from different documents
        elif unique_docs >= total_results * 0.4:
            return 70.0   # Some diversity
        else:
            return 50.0   # Low diversity
    
    def _generate_details(self, search_results: List[Dict[str, Any]], 
                         quantity: float, similarity: float, diversity: float) -> List[str]:
        """Generate human-readable details"""
        details = []
        
        # Quantity detail
        count = len(search_results)
        if count >= 3:
            details.append(f"{count} farklı kaynaktan bilgi")
        elif count >= 2:
            details.append(f"{count} kaynaktan bilgi")
        else:
            details.append("Sınırlı kaynak sayısı")
        
        # Similarity detail
        if similarity >= 85:
            details.append("Yüksek benzerlik skorları")
        elif similarity >= 70:
            details.append("Orta düzey benzerlik skorları")
        else:
            details.append("Düşük benzerlik skorları")
        
        # Diversity detail
        unique_docs = len(set(result.get("document_id") for result in search_results if result.get("document_id")))
        if unique_docs > 1:
            details.append(f"{unique_docs} farklı belgeden referans")
        else:
            details.append("Tek belgeden referans")
        
        return details
    
    def _no_sources_result(self) -> Dict[str, Any]:
        """Result when no sources found"""
        return {
            "score": 0,
            "weight": self.weight,
            "description": "Resmi kaynaklar, mevzuat metinleri ve güvenilir referansların kullanımı",
            "details": ["Hiç kaynak bulunamadı", "Bilgi doğrulanamadı"]
        }
    
    def _fallback_result(self) -> Dict[str, Any]:
        """Fallback result in case of error"""
        return {
            "score": 50,
            "weight": self.weight,
            "description": "Resmi kaynaklar, mevzuat metinleri ve güvenilir referansların kullanımı",
            "details": ["Kaynak değerlendirmesi tamamlanamadı"]
        }