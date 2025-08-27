"""
Pydantic models for request/response validation
Data transfer objects with type validation and serialization
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from uuid import UUID
import re

# User Models
class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr
    full_name: Optional[str] = None
    ad: Optional[str] = Field(None, max_length=50, description="Ad (opsiyonel)")
    soyad: Optional[str] = Field(None, max_length=50, description="Soyad (opsiyonel)")
    meslek: Optional[str] = Field(None, max_length=100, description="Meslek (opsiyonel)")
    calistigi_yer: Optional[str] = Field(None, max_length=150, description="Çalıştığı yer (opsiyonel)")
    role: str = Field(default="user", description="User role (user/admin)")

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('passwords do not match')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r"[A-Za-z]", v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r"[0-9]", v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class UserProfileUpdate(BaseModel):
    """User profile update model"""
    full_name: Optional[str] = None
    ad: Optional[str] = Field(None, max_length=50, description="Ad")
    soyad: Optional[str] = Field(None, max_length=50, description="Soyad")
    meslek: Optional[str] = Field(None, max_length=100, description="Meslek")
    calistigi_yer: Optional[str] = Field(None, max_length=150, description="Çalıştığı yer")
    
class PasswordChange(BaseModel):
    """Password change model"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str
    
    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('passwords do not match')
        return v

class PasswordReset(BaseModel):
    """Password reset model"""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('passwords do not match')
        return v

class UserResponse(BaseModel):
    """User response model (without password)"""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    ad: Optional[str] = None
    soyad: Optional[str] = None
    meslek: Optional[str] = None
    calistigi_yer: Optional[str] = None
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Token Models
class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600  # Default 1 hour
    user: UserResponse

# Document Models
class DocumentBase(BaseModel):
    """Base document model"""
    title: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    keywords: Optional[List[str]] = Field(default=[])
    source_institution: Optional[str] = Field(None, max_length=200)
    publish_date: Optional[date] = None

class DocumentCreate(DocumentBase):
    """Document creation model"""
    file_name: str
    file_url: str
    file_size: int
    uploaded_by: UUID

class DocumentUpdate(BaseModel):
    """Document update model"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    keywords: Optional[List[str]] = None
    source_institution: Optional[str] = Field(None, max_length=200)
    publish_date: Optional[date] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")

class DocumentResponse(DocumentBase):
    """Document response model"""
    id: UUID
    file_name: str
    file_url: str
    file_size: int
    processing_status: str
    status: str
    uploaded_by: UUID
    uploaded_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    """Document list response with pagination"""
    documents: List[DocumentResponse]
    pagination: Dict[str, int]

# Upload Models
class UploadResponse(BaseModel):
    """File upload response model"""
    document_id: str
    message: str
    file_url: str
    processing_status: str

# Search Models
class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum similarity score")
    category: Optional[str] = Field(None, description="Filter by category")
    date_range: Optional[Dict[str, date]] = Field(None, description="Date range filter")
    
    @validator('date_range')
    def validate_date_range(cls, v):
        if v and 'start' in v and 'end' in v:
            if v['start'] > v['end']:
                raise ValueError('Start date must be before end date')
        return v

class SearchResult(BaseModel):
    """Individual search result"""
    document_id: UUID
    document_title: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    
class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    results: List[SearchResult]
    total_results: int

# Ask Endpoint Models
class AskRequest(BaseModel):
    """Ask endpoint request model"""
    query: str = Field(..., min_length=3, max_length=1000, description="User's question")
    institution_filter: Optional[str] = Field(None, description="Filter by institution name")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of search results")
    similarity_threshold: float = Field(0.5, ge=0.3, le=1.0, description="Minimum similarity score")
    use_cache: bool = Field(True, description="Whether to use Redis cache")

class SourceItem(BaseModel):
    """Source document information in Ask response"""
    document_id: str
    document_title: str
    source_institution: Optional[str]
    content: str
    similarity_score: float
    category: Optional[str]
    publish_date: Optional[date]

class AskSearchStats(BaseModel):
    """Search performance statistics for Ask endpoint"""
    chunks: int
    embed_ms: int
    search_ms: int
    gen_ms: int
    total_ms: int
    cached: bool
    credits: int

class LLMStats(BaseModel):
    """LLM generation statistics"""
    model_used: str
    prompt_tokens: int
    response_tokens: int

class ConfidenceCriteria(BaseModel):
    """Individual confidence criteria details"""
    score: int
    weight: int
    description: str
    details: List[str]

class ScoreRange(BaseModel):
    """Score range information"""
    min: int
    max: int
    desc: str

class ConfidenceBreakdown(BaseModel):
    """Detailed confidence score breakdown"""
    overall_score: int
    explanation: str
    criteria: Dict[str, ConfidenceCriteria]
    score_ranges: Dict[str, ScoreRange]

class AskResponse(BaseModel):
    """Ask endpoint response model"""
    query: str
    answer: str
    search_log_id: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    sources: List[SourceItem]
    institution_filter: Optional[str]
    search_stats: AskSearchStats
    llm_stats: LLMStats

class UserSuggestion(BaseModel):
    """User search suggestion"""
    query: str
    timestamp: Optional[datetime]
    institution: Optional[str]

class PopularSearch(BaseModel):
    """Popular search item"""
    query: str
    count: int

class SuggestionsResponse(BaseModel):
    """User suggestions response"""
    recent_searches: List[UserSuggestion]
    popular_searches: List[PopularSearch]
    available_institutions: List[str]
    suggestions: List[str]

# Embedding Models
class EmbeddingCreate(BaseModel):
    """Embedding creation model"""
    document_id: UUID
    content: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None

class EmbeddingResponse(BaseModel):
    """Embedding response model"""
    id: UUID
    document_id: UUID
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Response Models
class ApiResponse(BaseModel):
    """Generic API response model"""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorDetail(BaseModel):
    """Error detail model"""
    message: str
    detail: Optional[str] = None
    code: Optional[str] = None

# Task Models
class TaskStatus(BaseModel):
    """Background task status model"""
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Statistics Models
class DocumentStats(BaseModel):
    """Document statistics model"""
    total_documents: int
    documents_by_category: Dict[str, int]
    documents_by_status: Dict[str, int]
    recent_uploads: int

class SearchStats(BaseModel):
    """Search statistics model"""
    total_searches: int
    popular_queries: List[Dict[str, Union[str, int]]]
    search_trends: Dict[str, int]

# Admin User Management Models
class AdminUserUpdate(BaseModel):
    """Admin user update model"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    ad: Optional[str] = Field(None, max_length=50)
    soyad: Optional[str] = Field(None, max_length=50)
    meslek: Optional[str] = Field(None, max_length=100)
    calistigi_yer: Optional[str] = Field(None, max_length=150)
    role: Optional[str] = Field(None, pattern="^(user|admin)$")

class AdminUserResponse(BaseModel):
    """Admin user response with additional fields"""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    ad: Optional[str] = None
    soyad: Optional[str] = None
    meslek: Optional[str] = None
    calistigi_yer: Optional[str] = None
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    current_balance: Optional[int] = None
    total_used: Optional[int] = None
    search_count: Optional[int] = None
    # Auth.users bilgileri
    email_confirmed_at: Optional[datetime] = None
    last_sign_in_at: Optional[datetime] = None
    is_banned: Optional[bool] = None
    banned_until: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AdminUserListResponse(BaseModel):
    """Admin user list response with pagination"""
    users: List[AdminUserResponse]
    pagination: Dict[str, int]

class UserCreditUpdate(BaseModel):
    """User credit update model"""
    amount: int = Field(..., description="Credit amount (positive to add, negative to subtract)")
    reason: str = Field(..., max_length=500, description="Reason for credit adjustment")

class UserBanRequest(BaseModel):
    """User ban/unban request model"""
    reason: Optional[str] = Field(None, max_length=500, description="Ban reason")
    ban_duration_hours: Optional[int] = Field(None, ge=1, le=8760, description="Ban duration in hours (max 1 year)")

# Health Check Models
class HealthCheck(BaseModel):
    """Health check response model"""
    status: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
class SystemStatus(BaseModel):
    """Detailed system status model"""
    database: str
    redis: str
    storage: str
    openai: str
    overall: str
