# MevzuatGPT - Legal Document RAG System

## Overview

MevzuatGPT is a production-ready RAG (Retrieval-Augmented Generation) system designed for legal document processing and semantic search. The application provides role-based access control where admin users can upload PDF documents, and authenticated users can perform semantic searches using natural language queries. The system leverages OpenAI embeddings for vector similarity search and integrates with Bunny.net CDN for file storage.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
The application uses **FastAPI** as the web framework, chosen for its high performance, automatic OpenAPI documentation generation, and native Pydantic integration. The async nature of FastAPI aligns well with the database operations and external service integrations.

### Database Architecture
The system employs **PostgreSQL** with **SQLAlchemy** for ORM operations, specifically using the async variant (`AsyncSession`) for non-blocking database operations. The database includes the `vector` extension for storing and querying embeddings. Connection pooling is configured to handle concurrent requests efficiently.

Key database tables:
- `users` - Authentication and role management
- `mevzuat_documents` - Document metadata and file references
- `mevzuat_embeddings` - Vector embeddings with content chunks

### Authentication & Authorization
**Role-based access control (RBAC)** is implemented using JWT tokens with two distinct roles:
- `admin` - Can upload documents and access administrative functions
- `user` - Can search and access documents

JWT tokens are managed through a custom `SecurityManager` class with configurable expiration times and refresh token support.

### File Storage Strategy
**Bunny.net CDN** is used for PDF file storage, chosen for its cost-effectiveness and global distribution capabilities. Files are uploaded through their REST API with proper error handling and retry mechanisms.

### Background Processing
**Celery with Redis** handles asynchronous document processing tasks including:
- PDF text extraction using PyPDF2
- Text chunking with LangChain's RecursiveCharacterTextSplitter
- OpenAI embedding generation
- Vector database storage

This architecture prevents blocking the main application during lengthy document processing operations.

### Configuration Management
**Pydantic Settings** provides type-validated configuration management, reading from environment variables with proper defaults and validation. This ensures all required configurations are present at startup and properly typed.

### Error Handling & Logging
A centralized exception handling system using custom `AppException` classes provides structured error responses with appropriate HTTP status codes. Logging is configured with rotation, multiple formatters, and different output targets (console, file) based on environment.

### Vector Search Implementation
Semantic search uses **OpenAI's text-embedding-3-large** model for generating embeddings, stored in PostgreSQL with the vector extension. Similarity search employs L2 distance with configurable thresholds and filtering capabilities.

## External Dependencies

### AI Services
- **OpenAI API** - Embedding generation (text-embedding-3-large) and chat completions (gpt-4o)

### Storage Services
- **Bunny.net Storage API** - PDF file storage and CDN delivery

### Database Services
- **PostgreSQL** - Primary database with vector extension for embedding storage
- **Redis** - Message broker for Celery background tasks and caching

### Authentication
- **Supabase** - Integrated for additional authentication features and user management capabilities

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