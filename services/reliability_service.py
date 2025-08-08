"""
Reliability Service - Main coordinator for confidence scoring
Combines multiple scoring criteria to generate comprehensive reliability assessment
"""

from typing import List, Dict, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import scoring modules
from .scoring.source_reliability import SourceReliabilityScorer
from .scoring.content_consistency import ContentConsistencyScorer
from .scoring.technical_accuracy import TechnicalAccuracyScorer
from .scoring.currency import CurrencyScorer

logger = logging.getLogger(__name__)


class ReliabilityService:
    """
    Main service for calculating comprehensive confidence scores
    Coordinates multiple scoring criteria and generates detailed breakdown
    """
    
    def __init__(self):
        # Initialize scorers
        self.source_scorer = SourceReliabilityScorer()
        self.content_scorer = ContentConsistencyScorer()
        self.technical_scorer = TechnicalAccuracyScorer()
        self.currency_scorer = CurrencyScorer()
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def calculate_comprehensive_confidence(
        self,
        search_results: List[Dict[str, Any]],
        ai_answer: str,
        use_parallel: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive confidence score with detailed breakdown
        
        Args:
            search_results: List of search results from vector database
            ai_answer: Generated AI response text
            use_parallel: Whether to calculate scores in parallel
            
        Returns:
            Dict containing confidence score and detailed breakdown
        """
        try:
            if use_parallel:
                # Calculate all scores in parallel
                scores = await self._calculate_parallel_scores(search_results, ai_answer)
            else:
                # Calculate scores sequentially
                scores = await self._calculate_sequential_scores(search_results, ai_answer)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(scores)
            
            # Generate comprehensive response
            return {
                "confidence_score": overall_score / 100.0,  # Convert to 0-1 range
                "confidence_breakdown": {
                    "overall_score": overall_score,
                    "explanation": "Bu skor, cevabın güvenilirliğini farklı kriterlere göre değerlendirerek oluşturulmuştur.",
                    "criteria": {
                        "source_reliability": scores["source_reliability"],
                        "content_consistency": scores["content_consistency"],
                        "technical_accuracy": scores["technical_accuracy"],
                        "currency": scores["currency"]
                    },
                    "score_ranges": {
                        "high": {
                            "min": 80,
                            "max": 100,
                            "desc": "Tüm kaynaklar doğrulanmış, içerik tam ve güvenilir"
                        },
                        "medium": {
                            "min": 60,
                            "max": 79,
                            "desc": "Çoğu kaynak doğrulanmış, içerik güvenilir"
                        },
                        "low": {
                            "min": 0,
                            "max": 59,
                            "desc": "Az sayıda kaynak doğrulanmış, içerik kontrol edilmeli"
                        }
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Reliability calculation failed: {e}")
            return self._fallback_confidence_result()
    
    async def _calculate_parallel_scores(self, search_results: List[Dict[str, Any]], 
                                       ai_answer: str) -> Dict[str, Any]:
        """Calculate all scores in parallel using thread pool"""
        loop = asyncio.get_event_loop()
        
        # Submit all scoring tasks to thread pool
        tasks = {
            'source_reliability': loop.run_in_executor(
                self.executor, self.source_scorer.calculate_score, search_results
            ),
            'content_consistency': loop.run_in_executor(
                self.executor, self.content_scorer.calculate_score, search_results, ai_answer
            ),
            'technical_accuracy': loop.run_in_executor(
                self.executor, self.technical_scorer.calculate_score, search_results, ai_answer
            ),
            'currency': loop.run_in_executor(
                self.executor, self.currency_scorer.calculate_score, search_results, ai_answer
            )
        }
        
        # Wait for all tasks to complete
        scores = {}
        for key, task in tasks.items():
            try:
                scores[key] = await task
            except Exception as e:
                logger.error(f"Scoring failed for {key}: {e}")
                scores[key] = self._get_fallback_score(key)
        
        return scores
    
    async def _calculate_sequential_scores(self, search_results: List[Dict[str, Any]], 
                                         ai_answer: str) -> Dict[str, Any]:
        """Calculate all scores sequentially"""
        scores = {}
        
        try:
            scores['source_reliability'] = self.source_scorer.calculate_score(search_results)
        except Exception as e:
            logger.error(f"Source reliability scoring failed: {e}")
            scores['source_reliability'] = self._get_fallback_score('source_reliability')
        
        try:
            scores['content_consistency'] = self.content_scorer.calculate_score(search_results, ai_answer)
        except Exception as e:
            logger.error(f"Content consistency scoring failed: {e}")
            scores['content_consistency'] = self._get_fallback_score('content_consistency')
        
        try:
            scores['technical_accuracy'] = self.technical_scorer.calculate_score(search_results, ai_answer)
        except Exception as e:
            logger.error(f"Technical accuracy scoring failed: {e}")
            scores['technical_accuracy'] = self._get_fallback_score('technical_accuracy')
        
        try:
            scores['currency'] = self.currency_scorer.calculate_score(search_results, ai_answer)
        except Exception as e:
            logger.error(f"Currency scoring failed: {e}")
            scores['currency'] = self._get_fallback_score('currency')
        
        return scores
    
    def _calculate_overall_score(self, scores: Dict[str, Any]) -> int:
        """Calculate weighted average of all scores"""
        try:
            total_weighted_score = 0
            total_weight = 0
            
            for score_data in scores.values():
                score = score_data.get('score', 0)
                weight = score_data.get('weight', 0)
                
                total_weighted_score += score * weight
                total_weight += weight
            
            if total_weight == 0:
                return 50  # Fallback score
            
            overall = int(total_weighted_score / total_weight)
            return max(0, min(overall, 100))  # Ensure 0-100 range
            
        except Exception as e:
            logger.error(f"Overall score calculation failed: {e}")
            return 50
    
    def _get_fallback_score(self, criteria: str) -> Dict[str, Any]:
        """Get fallback score for a specific criteria"""
        fallback_scores = {
            'source_reliability': {
                "score": 50,
                "weight": 30,
                "description": "Resmi kaynaklar, mevzuat metinleri ve güvenilir referansların kullanımı",
                "details": ["Kaynak güvenilirliği değerlendirilemedi"]
            },
            'content_consistency': {
                "score": 50,
                "weight": 25,
                "description": "Yanıtın iç tutarlılığı ve mantıksal bütünlüğü",
                "details": ["İçerik tutarlılığı değerlendirilemedi"]
            },
            'technical_accuracy': {
                "score": 50,
                "weight": 25,
                "description": "Hukuki terminoloji ve teknik detayların doğruluğu",
                "details": ["Teknik doğruluk değerlendirilemedi"]
            },
            'currency': {
                "score": 60,
                "weight": 20,
                "description": "Bilgilerin güncel mevzuata uygunluğu",
                "details": ["Güncellik değerlendirilemedi"]
            }
        }
        
        return fallback_scores.get(criteria, {
            "score": 50,
            "weight": 25,
            "description": "Değerlendirme tamamlanamadı",
            "details": ["Skor hesaplanamadı"]
        })
    
    def _fallback_confidence_result(self) -> Dict[str, Any]:
        """Complete fallback result when entire process fails"""
        return {
            "confidence_score": 0.5,
            "confidence_breakdown": {
                "overall_score": 50,
                "explanation": "Güvenilirlik skoru hesaplanamadı, varsayılan değer kullanıldı.",
                "criteria": {
                    "source_reliability": self._get_fallback_score('source_reliability'),
                    "content_consistency": self._get_fallback_score('content_consistency'),
                    "technical_accuracy": self._get_fallback_score('technical_accuracy'),
                    "currency": self._get_fallback_score('currency')
                },
                "score_ranges": {
                    "high": {"min": 80, "max": 100, "desc": "Tüm kaynaklar doğrulanmış, içerik tam ve güvenilir"},
                    "medium": {"min": 60, "max": 79, "desc": "Çoğu kaynak doğrulanmış, içerik güvenilir"},
                    "low": {"min": 0, "max": 59, "desc": "Az sayıda kaynak doğrulanmış, içerik kontrol edilmeli"}
                }
            }
        }
    
    def __del__(self):
        """Cleanup thread pool on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)