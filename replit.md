# MevzuatGPT - Legal Document RAG System

## Overview

MevzuatGPT is a production-ready RAG (Retrieval-Augmented Generation) system designed for legal document processing and semantic search. The application provides role-based access control where admin users can upload PDF documents, and authenticated users can perform semantic searches using natural language queries. The system leverages OpenAI embeddings for vector similarity search and integrates with Bunny.net CDN for file storage.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Architecture Changes (August 7, 2025)

### Major Updates - Supabase & Redis Cloud Integration
- **Supabase Auth**: Replaced custom JWT authentication with Supabase Auth for centralized user management
- **Supabase Database**: Migrated to Supabase PostgreSQL as primary database with pgvector for vector operations
- **Redis Cloud**: Updated Celery configuration to use Redis Cloud instead of local Redis
- **RLS Security**: Implemented Row Level Security policies for secure data access
- **Vector Search**: Created optimized `search_embeddings()` function for similarity search
- **API Modernization**: Updated all auth routes to use Supabase Auth service
- **Dependency Updates**: Modified FastAPI dependencies to work with Supabase authentication

### Required Configuration Updates
- All external services (OpenAI, Bunny.net, Supabase, Redis Cloud) are now mandatory for full functionality
- Added comprehensive .env.example and API_KEYS_REQUIREMENTS.md for setup guidance
- Created models/supabase_models.py with complete SQL schema for Supabase setup

## System Architecture

### Backend Framework
The application uses **FastAPI** as the web framework, chosen for its high performance, automatic OpenAPI documentation generation, and native Pydantic integration. The async nature of FastAPI aligns well with the database operations and external service integrations.

### Database Architecture
The system uses **Supabase PostgreSQL** as the primary database with **pgvector** extension for vector similarity search. The database features Row Level Security (RLS) for secure data access and integrates with Supabase Auth for seamless user management.

Key database tables:
- `auth.users` - Supabase managed user authentication
- `public.user_profiles` - Extended user information and roles
- `public.mevzuat_documents` - Document metadata and file references
- `public.mevzuat_embeddings` - Vector embeddings with content chunks
- `public.search_logs` - Analytics and search history

Database connections use SQLAlchemy async sessions with connection pooling configured for optimal performance.

### Authentication & Authorization
**Supabase Auth** provides centralized authentication and user management with **role-based access control (RBAC)**:
- `admin` - Can upload documents and access administrative functions
- `user` - Can search and access documents

User registration, login, and session management are handled through Supabase's Auth API. JWT tokens are managed by Supabase with automatic refresh capabilities and Row Level Security (RLS) policies for database access control.

### File Storage Strategy
**Bunny.net CDN** is used for PDF file storage, chosen for its cost-effectiveness and global distribution capabilities. Files are uploaded through their REST API with proper error handling and retry mechanisms.

### Background Processing
**Celery with Redis Cloud** handles asynchronous document processing tasks including:
- PDF text extraction using PyPDF2
- Text chunking with LangChain's RecursiveCharacterTextSplitter
- OpenAI embedding generation
- Vector storage in Supabase PostgreSQL

Redis Cloud provides a scalable message broker and result backend, ensuring reliable task distribution and preventing application blocking during lengthy document processing operations.

### Configuration Management
**Pydantic Settings** provides type-validated configuration management, reading from environment variables with proper defaults and validation. This ensures all required configurations are present at startup and properly typed.

### Error Handling & Logging
A centralized exception handling system using custom `AppException` classes provides structured error responses with appropriate HTTP status codes. Logging is configured with rotation, multiple formatters, and different output targets (console, file) based on environment.

### Vector Search Implementation
Semantic search uses **OpenAI's text-embedding-3-large** model for generating 1536-dimensional embeddings. These are stored in **Supabase PostgreSQL** with the **pgvector** extension. Similarity search employs cosine distance with configurable thresholds through a custom `search_embeddings()` SQL function that efficiently queries across document chunks.

## External Dependencies

### AI Services
- **OpenAI API** - Embedding generation (text-embedding-3-large) and chat completions (gpt-4o)

### Storage Services
- **Bunny.net Storage API** - PDF file storage and CDN delivery

### Database Services
- **Supabase PostgreSQL** - Primary database with pgvector extension for embedding storage and Row Level Security
- **Redis Cloud** - Message broker for Celery background tasks and caching

### Authentication & User Management
- **Supabase Auth** - Complete user authentication, registration, and session management system

### Background Processing
- **Celery** - Distributed task queue for document processing
- **Redis** - Message broker and result backend for Celery

### Text Processing
- **LangChain** - Text chunking and document processing utilities
- **PyPDF2** - PDF text extraction

### Python Libraries
- **FastAPI** - Web framework and API server
- **SQLAlchemy** - Database ORM with async support
- **Pydantic** - Data validation and settings management
- **Alembic** - Database migrations
- **Uvicorn** - ASGI server for production deployment