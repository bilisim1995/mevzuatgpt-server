"""
SQLAlchemy database models
Database table definitions with relationships and constraints
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, BigInteger, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from core.database import Base

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

class Document(Base):
    """Document model for storing PDF metadata and processing status"""
    __tablename__ = "mevzuat_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    keywords = Column(ARRAY(String), nullable=True)
    source_institution = Column(String(200), nullable=True)
    publish_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active, inactive
    
    # File information
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    
    # Processing information
    processing_status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    
    # Audit fields
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    uploader = relationship("User", back_populates="documents")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_category', 'category'),
        Index('idx_processing_status', 'processing_status'),
        Index('idx_uploaded_by', 'uploaded_by'),
        Index('idx_status', 'status'),
        Index('idx_publish_date', 'publish_date'),
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title[:50]}, status={self.processing_status})>"

class Embedding(Base):
    """Embedding model for storing vector embeddings of document chunks"""
    __tablename__ = "mevzuat_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("mevzuat_documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(3072), nullable=False)  # text-embedding-3-large dimension
    chunk_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="embeddings")
    
    # Vector similarity index
    __table_args__ = (
        Index('idx_embedding_vector', 'embedding', postgresql_using='ivfflat'),
        Index('idx_document_id', 'document_id'),
    )
    
    def __repr__(self):
        return f"<Embedding(id={self.id}, document_id={self.document_id}, content_length={len(self.content)})>"

class SearchLog(Base):
    """Search log model for analytics and monitoring"""
    __tablename__ = "search_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    query = Column(Text, nullable=False)
    results_count = Column(Integer, nullable=False, default=0)
    execution_time = Column(Float, nullable=True)  # in seconds
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_query_text', 'query', postgresql_using='gin', postgresql_ops={'query': 'gin_trgm_ops'}),
    )
    
    def __repr__(self):
        return f"<SearchLog(id={self.id}, query={self.query[:50]}, results={self.results_count})>"

class ProcessingJob(Base):
    """Processing job model for tracking background tasks"""
    __tablename__ = "processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("mevzuat_documents.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String(255), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_document_id', 'document_id'),
        Index('idx_task_id', 'task_id'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, document_id={self.document_id}, status={self.status})>"

# Additional utility tables for system monitoring and configuration

class SystemConfig(Base):
    """System configuration model for runtime settings"""
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemConfig(key={self.key}, encrypted={self.is_encrypted})>"

class ApiUsage(Base):
    """API usage tracking model for monitoring and billing"""
    __tablename__ = "api_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Float, nullable=False)  # in milliseconds
    request_size = Column(BigInteger, nullable=True)  # in bytes
    response_size = Column(BigInteger, nullable=True)  # in bytes
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes for analytics
    __table_args__ = (
        Index('idx_user_id_usage', 'user_id'),
        Index('idx_endpoint_usage', 'endpoint'),
        Index('idx_created_at_usage', 'created_at'),
        Index('idx_status_code_usage', 'status_code'),
    )
    
    def __repr__(self):
        return f"<ApiUsage(endpoint={self.endpoint}, status={self.status_code}, time={self.response_time})>"
