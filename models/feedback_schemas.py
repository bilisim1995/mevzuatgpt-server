"""
Feedback system için Pydantic modelleri
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, validator

class FeedbackSubmit(BaseModel):
    """Feedback gönderimi için model"""
    search_log_id: str
    feedback_type: str
    feedback_comment: Optional[str] = None
    
    @validator('feedback_type')
    def validate_feedback_type(cls, v):
        if v not in ['positive', 'negative']:
            raise ValueError('feedback_type must be positive or negative')
        return v
    
    @validator('feedback_comment')
    def validate_comment(cls, v, values):
        # Negative feedback için comment zorunlu değil ama önerilir
        if v is not None and len(v.strip()) == 0:
            return None
        return v

class FeedbackResponse(BaseModel):
    """Feedback yanıt modeli"""
    id: str
    user_id: str
    search_log_id: str
    query_text: str
    answer_text: str
    feedback_type: str
    feedback_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class FeedbackListResponse(BaseModel):
    """Feedback listesi yanıt modeli"""
    feedback_list: list[FeedbackResponse]
    total_count: int
    has_more: bool
    page: int
    limit: int

class FeedbackOperationResponse(BaseModel):
    """Feedback işlemi sonuç modeli"""
    success: bool
    message: str
    feedback: Optional[FeedbackResponse] = None