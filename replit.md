# MevzuatGPT

## Overview

MevzuatGPT is a production-ready RAG (Retrieval-Augmented Generation) system designed for legal document processing and semantic search. The application allows admin users to upload PDF documents containing legal texts, which are then processed, vectorized, and made searchable through AI-powered queries. The system provides comprehensive document management with role-based access control, supporting both document search and intelligent question-answering capabilities.

The platform serves as a legal research assistant, enabling users to query complex legal documents in natural language and receive contextually relevant answers with source attribution and confidence scoring.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### Support Ticket System Implementation (August 9, 2025)
- **New Feature**: Complete modular support ticket system for user inquiries and admin management
- **Database**: Support tables with RLS policies and automated ticket numbering (TK-001 format)
- **Categories**: 7 categories including technical issues, account problems, feature requests, security, billing, general questions, other
- **Priority Levels**: 4 levels from low to urgent with proper escalation
- **Status Management**: Open, answered, closed status with automatic updates
- **API Endpoints**: User endpoints (/api/user/support) and Admin endpoints (/api/admin/support)
- **Features**: Pagination, filtering, search, statistics, message threading
- **Testing**: Comprehensive Postman collection for automated testing
- **Security**: Full RLS implementation with user isolation and admin access

## System Architecture

### Backend Framework Architecture
The application is built on **FastAPI** as the core web framework, chosen for its high-performance asynchronous capabilities, automatic OpenAPI documentation generation, and native Pydantic integration. The framework supports async operations throughout the application stack, enabling efficient handling of document processing, database operations, and AI service calls.

### Database and Storage Architecture
The system uses a multi-tiered storage approach:

**Primary Database**: Supabase PostgreSQL with pgvector extension for vector similarity search operations. The database includes Row Level Security (RLS) policies for secure data access control and optimized indexes for search performance.

**Vector Storage**: Legal document embeddings are stored as 1536-dimensional vectors using OpenAI's text-embedding-3-small model, enabling semantic search capabilities across document chunks.

**File Storage**: PDF documents are stored on Bunny.net CDN for fast, globally distributed access with automated backup and versioning.

**Cache Layer**: Redis Cloud provides caching for search results, rate limiting, and session management to optimize user experience and prevent abuse.

### Authentication and Authorization System
The application implements **role-based access control (RBAC)** through Supabase Auth:

- **Admin Role**: Full document upload, management, and administrative functions
- **User Role**: Document search and query capabilities

JWT tokens are managed by Supabase with automatic refresh capabilities and integrated with database-level Row Level Security policies for granular data access control.

### Document Processing Pipeline
The system employs a sophisticated async processing pipeline:

1. **Upload Phase**: PDFs are uploaded to Bunny.net CDN with metadata validation
2. **Text Extraction**: Multi-method PDF parsing using pdfplumber with fallback mechanisms
3. **Text Chunking**: Intelligent text splitting with overlap preservation using LangChain
4. **Vectorization**: Batch embedding generation via OpenAI API
5. **Storage**: Vector embeddings stored in Supabase with source attribution
6. **Background Processing**: Celery workers handle long-running tasks with Redis queue management

### AI and Search Architecture
The query processing system supports multiple AI providers:

- **Primary**: Groq API for fast, cost-effective inference using Llama models
- **Fallback**: OpenAI GPT-4o for complex reasoning tasks
- **Search**: pgvector-powered semantic search with configurable similarity thresholds

### Reliability and Quality Control
The system includes a comprehensive confidence scoring mechanism:

- **Source Reliability Scoring**: Evaluates document source quality and authority
- **Content Consistency Analysis**: Measures internal coherence of responses
- **Technical Accuracy Assessment**: Validates legal terminology and technical correctness
- **Currency Evaluation**: Considers document recency and relevance

## External Dependencies

### AI and Machine Learning Services
- **OpenAI API**: Text embedding generation (text-embedding-3-small) and GPT-4o completion services
- **Groq API**: Primary AI inference provider for fast, cost-effective response generation using Llama models

### Database and Authentication
- **Supabase**: Comprehensive backend-as-a-service providing PostgreSQL database with pgvector extension, authentication services, and Row Level Security
- **Redis Cloud**: Distributed caching, session management, and Celery task queue backend

### Storage and CDN
- **Bunny.net Storage**: Global CDN for PDF document storage with high-availability and fast access
- **Bunny.net CDN**: Content delivery network for optimized file serving

### Background Processing
- **Celery**: Distributed task queue for document processing workflows
- **Redis**: Message broker and result backend for Celery workers

### Document Processing Libraries
- **pdfplumber**: Primary PDF text extraction with advanced parsing capabilities
- **PyPDF2**: Fallback PDF processing library
- **LangChain**: Text splitting and chunking with intelligent overlap handling

### Python Framework Dependencies
- **FastAPI**: High-performance async web framework with automatic documentation
- **SQLAlchemy**: Async ORM with connection pooling for database operations
- **Pydantic**: Data validation and serialization with type safety
- **asyncpg**: High-performance PostgreSQL driver for async operations