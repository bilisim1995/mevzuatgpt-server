"""
Search history schemas for request/response models
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator, ConfigDict


class SearchHistoryItem(BaseModel):
    """Single search history entry"""
    id: str
    query: str
    response: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    reliability_score: Optional[float] = None
    confidence_breakdown: Optional[Dict[str, Any]] = None
    search_stats: Optional[Dict[str, Any]] = None
    credits_used: Optional[int] = 0
    institution_filter: Optional[str] = None
    results_count: int = 0
    execution_time: Optional[float] = None
    created_at: datetime
    
    @validator('created_at', pre=True)
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace('Z', '+00:00'))
        return v
    
    model_config = ConfigDict(json_encoders={
        datetime: lambda v: v.isoformat()
    })


class SearchHistoryResponse(BaseModel):
    """Search history response with pagination"""
    items: List[SearchHistoryItem]
    total_count: int
    page: int
    limit: int
    has_more: bool


class SearchHistoryFilters(BaseModel):
    """Filters for search history"""
    institution: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_reliability: Optional[float] = Field(None, ge=0.0, le=1.0)
    search_query: Optional[str] = None  # Search within queries