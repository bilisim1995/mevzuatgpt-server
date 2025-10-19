"""
Configuration management using Pydantic Settings
Handles environment variables and application settings
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional
import os
from dotenv import load_dotenv

# Force load .env file and override system environment
load_dotenv('.env', override=True)


class Settings(BaseSettings):
    """Application settings with type validation and environment variable support"""
    
    # Application
    APP_NAME: str = "MevzuatGPT"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "development-secret-key-change-in-production"
    ALLOWED_HOSTS: str = "*"
    ALLOWED_ORIGINS: str = "*"
    
    # Supabase Database & Auth (Primary)
    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_KEY: str = "your-supabase-anon-key"
    SUPABASE_SERVICE_KEY: str = "your-supabase-service-key"
    DATABASE_URL: str = "postgresql://postgres:b06dRrGS3TOsGmY7@db.omublqdeerbszkuuvoim.supabase.co:5432/postgres"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-jwt-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OpenAI - Upgraded to text-embedding-3-large for 2048 dimensions
    OPENAI_API_KEY: str = "your-openai-api-key"
    OPENAI_MODEL: str = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-large"  # Upgraded: 2048 dimensions for Elasticsearch
    OPENAI_EMBEDDING_DIMENSIONS: int = 2048  # ES 8.19.2 optimized dimensions
    OPENAI_MAX_TOKENS: int = 4000
    
    # Elasticsearch Vector Database (Primary)
    ELASTICSEARCH_URL: str = "https://elastic.mevzuatgpt.org"
    ELASTICSEARCH_INDEX: str = "mevzuat_embeddings"
    ELASTICSEARCH_TIMEOUT: int = 30
    
    # Bunny.net Storage
    BUNNY_STORAGE_API_KEY: str = "your-bunny-api-key"
    BUNNY_STORAGE_ZONE: str = "your-storage-zone"
    BUNNY_STORAGE_REGION: str = "de"
    BUNNY_STORAGE_ENDPOINT: str = "your-bunny-endpoint"
    
    # Redis Cloud & Celery
    REDIS_URL: str = "redis://default:password@redis-cloud-endpoint:port"
    CELERY_BROKER_URL: str = "redis://default:password@redis-cloud-endpoint:port"
    # CELERY_RESULT_BACKEND disabled - using custom Redis progress tracking instead
    
    # AI Model Configuration
    GROQ_API_KEY: str = "your-groq-api-key-here"
    GROQ_MODEL: str = "llama3-70b-8192"  # Default Groq model
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_TIMEOUT: int = 30
    OLLAMA_MAX_TOKENS: int = 2048
    
    # Email Service (SendGrid for password reset)
    SENDGRID_API_KEY: Optional[str] = None  # Optional email service
    SENDGRID_FROM_EMAIL: Optional[str] = None  # SendGrid from email address
    
    # SMTP Email Service (Hostinger for credit notifications)
    SMTP_HOST: str = "smtp.hostinger.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "info@mevzuatgpt.org"
    SMTP_PASSWORD: Optional[str] = None
    SMTP_SENDER: str = "no-reply@mevzuatgpt.org"
    
    # AI Provider Selection
    AI_PROVIDER: str = Field(default="groq", description="AI provider: groq, ollama, or openai")
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = ["pdf"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Vector Search - Elasticsearch optimized
    SEARCH_LIMIT: int = 10
    SIMILARITY_THRESHOLD: float = 0.7  # Optimized for Elasticsearch cosine similarity
    
    model_config = {
        "env_file": ".env", 
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "env_ignore_empty": False
    }
    
    @field_validator("ALLOWED_FILE_TYPES")
    @classmethod
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [ft.strip().lower() for ft in v.split(",")]
        return v
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        if v not in ["development", "staging", "production"]:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production")
        return v

# Create global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get global settings instance for dependency injection"""
    return settings
