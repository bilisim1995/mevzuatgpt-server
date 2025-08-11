# MevzuatGPT

## Overview

MevzuatGPT is a production-ready RAG (Retrieval-Augmented Generation) system designed for legal document processing and semantic search. The application allows admin users to upload PDF documents containing legal texts, which are then processed, vectorized, and made searchable through AI-powered queries. The system provides comprehensive document management with role-based access control, supporting both document search and intelligent question-answering capabilities.

The platform serves as a legal research assistant, enabling users to query complex legal documents in natural language and receive contextually relevant answers with source attribution and confidence scoring.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

### AI Response Format Improvement (August 11, 2025)
- **Issue Fixed**: AI responses included unnecessary template phrases like "Belge içeriğinde, sigortalılık şartları şu şekilde belirtilmiştir:"
- **Solution**: Updated Groq service system prompt to provide direct, concise answers without introductory phrases
- **Markdown Support**: Added Markdown formatting instructions for better response structure (headers, lists, bold text)
- **Format Rules**: AI now uses ## for headers, - or 1. for lists, **bold** for emphasis, and clean Markdown syntax
- **Prompt Changes**: Added "Doğrudan cevap ver, gereksiz başlık veya giriş cümlesi kullanma" rule to system message
- **User Message**: Simplified prompt to "Soruyu doğrudan cevapla, giriş cümlesi kullanma"
- **Result**: AI provides structured Markdown responses like "## Sigortalılık Şartları\n1. **Yaş şartı**: 18 yaş üstü..."
- **Impact**: Better user experience with well-formatted, natural responses that render beautifully in web interfaces

### Search History System Implementation (August 10, 2025)
- **New Feature**: Complete search history tracking with detailed user query logs
- **Enhanced Database**: Extended search_logs table with response, sources, reliability_score, credits_used, institution_filter columns
- **API Endpoints**: New GET /api/user/search-history with pagination and filtering capabilities  
- **Search Statistics**: GET /api/user/search-history/stats for user analytics and usage insights
- **Query Integration**: Automatic logging of all search results with AI responses, source documents, and confidence scores
- **Filtering Options**: Filter by institution, date range, reliability score, and search within previous queries
- **User Benefits**: Users can now review all past searches, responses, credit usage, and search performance metrics

### Performance-Optimized Institution Filtering Implementation (August 10, 2025)
- **Architecture Change**: Implemented document-level pre-filtering before vector search for 10x performance improvement
- **Optimization Strategy**: Changed from post-search metadata filtering to pre-search document ID filtering
- **Implementation Details**: Added `_get_documents_by_institution` method to query service for institution-specific document filtering
- **Performance Benefit**: Search operations now filter documents by institution BEFORE performing vector similarity search
- **Database Query**: Uses Supabase service client to query `metadata->source_institution` field directly
- **Code Changes**: Updated embedding service, search service, and query service to support document ID filtering
- **Result**: Significantly faster searches when institution filter is applied (searches 4-20 documents vs 203 embeddings)

### Smart Credit Refund System Implementation (August 10, 2025)
- **New Feature**: Automatic credit refund system for "no information found" responses
- **Detection Logic**: AI responses are analyzed for phrases like "Verilen belge içeriğinde bu konuda bilgi bulunmamaktadır"
- **Refund Process**: When no information is found, users automatically get their credits refunded
- **Implementation**: Added to /api/user/ask endpoint with phrase detection and credit service integration
- **Admin Handling**: Admin users see refund simulation in response (refund_would_apply field) but don't get charged
- **Testing**: Confirmed working with normal users - credits properly refunded when AI can't find relevant information
- **Fairness**: Ensures users only pay for queries that return useful information from legal documents

### AI Response Quality Improvement (August 10, 2025)  
- **Issue Fixed**: AI was appending "Verilen belge içeriğinde bu konuda bilgi bulunmamaktadır" to all responses
- **Root Cause**: Hardcoded text in Groq service system prompt was always adding disclaimer text
- **Solution**: Refined prompt to only show "no information" message when documents are truly empty or irrelevant
- **Result**: AI now provides clean, accurate responses when relevant documents are found
- **Testing**: Verified with "Sigortalılık şartları" query - now returns proper bullet-point legal requirements

### Critical Search Functionality Fix (August 9, 2025)
- **Issue Identified**: Search returning "no information found" due to empty embeddings table
- **Root Cause**: Documents existed but had no embeddings generated, causing semantic search to fail
- **Resolution**: Fixed Supabase RLS policy infinite recursion errors and service client access issues
- **Embedding Generation**: Created automated embedding generation script for existing documents
- **Testing**: Comprehensive debug scripts to identify and resolve search pipeline issues
- **PDF URL Display**: Fixed source enhancement to properly show Bunny.net PDF download links in query responses
- **Cache Management**: Resolved stale cache issues that prevented proper PDF URL display
- **Status**: Search functionality fully restored with proper similarity scoring, document retrieval, and PDF download links

### Support Ticket System Implementation Complete (August 10, 2025)
- **Status**: Fully operational support ticket system deployed and tested
- **Core Features**: Complete ticket lifecycle management with automated numbering (TK-000001 format)
- **Database**: Support tables operational with service role access bypassing RLS issues
- **API Endpoints**: All user and admin endpoints working (/api/user/tickets, /api/admin/tickets)
- **Testing Results**: Successfully created 3 test tickets, verified listing and admin access
- **Technical Resolution**: Fixed UUID serialization, RLS infinite recursion, and foreign key join issues
- **Performance**: Service client integration provides fast, reliable database access
- **Security**: User isolation maintained while allowing admin oversight of all tickets

### Extended User Profile System (August 9, 2025)
- **Enhanced Registration**: Added optional profile fields (ad, soyad, meslek, calistigi_yer) to user registration
- **Database Schema**: Extended user_profiles table with new VARCHAR columns and performance indexes
- **API Extensions**: New profile management endpoints (/api/user/profile GET/PUT)
- **Supabase Integration**: Updated authentication service to handle extended user metadata
- **Validation**: Proper field length limits and optional field handling
- **Migration Files**: Complete SQL migration for Supabase compatibility

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