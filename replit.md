# MevzuatGPT

## Overview
MevzuatGPT is a production-ready RAG (Retrieval-Augmented Generation) system designed for legal document processing and semantic search. It allows admin users to upload legal PDF documents, which are then processed, vectorized, and made searchable through AI-powered queries. The system provides comprehensive document management with role-based access control, supporting both document search and intelligent question-answering capabilities. It functions as a legal research assistant, enabling users to query complex legal documents in natural language and receive contextually relevant answers with source attribution and confidence scoring.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
The application is built on FastAPI, chosen for its high-performance asynchronous capabilities, automatic OpenAPI documentation, and native Pydantic integration.

### Database and Storage
The system uses a multi-tiered storage approach:
- **Primary Database**: Supabase PostgreSQL with `pgvector` extension for vector similarity search, including Row Level Security (RLS) policies.
- **Vector Storage**: Legal document embeddings (1536-dimensional, from OpenAI's `text-embedding-3-small` model) are stored for semantic search.
- **File Storage**: PDF documents are stored on Bunny.net CDN for fast, globally distributed access.
- **Cache Layer**: Redis Cloud provides caching for search results, rate limiting, and session management.

### Authentication and Authorization
Role-based access control (RBAC) is implemented via Supabase Auth. Roles include:
- **Admin**: Full document upload, management, and administrative functions.
- **User**: Document search and query capabilities.
JWT tokens are managed by Supabase with automatic refresh and integrated with database-level RLS.

### Document Processing Pipeline
An asynchronous processing pipeline handles documents:
1.  **Upload**: PDFs are uploaded to Bunny.net CDN with metadata validation.
2.  **Text Extraction**: Multi-method PDF parsing using `pdfplumber` with fallbacks.
3.  **Text Chunking**: Intelligent text splitting with overlap preservation using LangChain.
4.  **Vectorization**: Batch embedding generation via OpenAI API.
5.  **Storage**: Vector embeddings stored in Supabase with source attribution.
6.  **Background Processing**: Celery workers manage long-running tasks with Redis queue.

### AI and Search Architecture
The query processing system supports multiple AI providers:
-   **Primary**: Groq API for fast, cost-effective inference using Llama models.
-   **Fallback**: OpenAI GPT-4o for complex reasoning tasks.
-   **Search**: `pgvector`-powered semantic search with configurable similarity thresholds.
-   **Institution Filtering**: Document-level pre-filtering by institution before vector search for performance.
-   **Smart Credit Refund**: Automatic credit refund for "no information found" responses.

### Reliability and Quality Control
A comprehensive confidence scoring mechanism includes:
-   Source Reliability Scoring.
-   Content Consistency Analysis.
-   Technical Accuracy Assessment.
-   Currency Evaluation.

## External Dependencies

### AI and Machine Learning Services
-   **OpenAI API**: For text embedding generation (`text-embedding-3-small`) and GPT-4o completion services.
-   **Groq API**: Primary AI inference provider for fast, cost-effective response generation using Llama models.

### Database and Authentication
-   **Supabase**: Provides PostgreSQL database with `pgvector` extension, authentication services, and Row Level Security.
-   **Redis Cloud**: Used for distributed caching, session management, and as the Celery task queue backend.

### Storage and CDN
-   **Bunny.net Storage**: Global CDN for PDF document storage.
-   **Bunny.net CDN**: Content delivery network for optimized file serving.

### Background Processing
-   **Celery**: Distributed task queue for document processing workflows.
-   **Redis**: Message broker and result backend for Celery workers.

### Document Processing Libraries
-   **pdfplumber**: Primary PDF text extraction library.
-   **PyPDF2**: Fallback PDF processing library.
-   **LangChain**: For text splitting and chunking.

### Python Framework Dependencies
-   **FastAPI**: High-performance async web framework.
-   **SQLAlchemy**: Async ORM for database operations.
-   **Pydantic**: Data validation and serialization.
-   **asyncpg**: High-performance PostgreSQL driver.

## Recent Changes

### Self-hosted Supabase Migration Preparation (August 16, 2025)
- **Infrastructure Migration**: Configured environment variables for self-hosted Supabase at https://supabase.mevzuatgpt.org
- **Environment Variables Updated**: SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, JWT_SECRET_KEY configured for self-hosted instance
- **Database URL Format Fixed**: Corrected DATABASE_URL parsing for passwords containing special characters with URL encoding
- **Code Quality Enhancement**: Fixed 18 LSP diagnostics in user routes, improved variable scope safety and error handling
- **PostgREST Schema Cache Issue**: Identified PGRST002 schema cache retrying issue in self-hosted setup
- **DNS Resolution Pending**: Self-hosted domains (db.supabase.mevzuatgpt.org, supabase.mevzuatgpt.org) not yet resolving
- **Migration Status**: DATABASE_URL updated to self-hosted, DNS working, Auth service active, PostgREST password encoding issue identified
- **Backward Compatibility**: System remains functional with cloud fallback during infrastructure transition

### Groq AI Response Quality Enhancement (August 16, 2025)
- **User Request Fulfilled**: Significantly improved Groq response length and creativity for more detailed legal analysis
- **Model Upgrade**: Switched from `llama3-8b-8192` to `llama3-70b-8192` for enhanced reasoning capabilities  
- **Response Length Optimization**: Increased max_tokens from 1024 to 2048 tokens for comprehensive answers
- **Creativity Parameters**: Enhanced temperature (0.1→0.3), top_p (0.85→0.9), and presence_penalty (0.3→0.6)
- **Prompt Engineering**: Redesigned system prompt to require 200-300 word minimum responses with analytical depth
- **Legal Analysis Focus**: Added requirements for explaining legal terms, providing context, and connecting related articles
- **Test Results**: Achieved 214-word responses (4x improvement) with 1,751 characters of detailed legal analysis
- **Production Ready**: Users now receive comprehensive, expert-level legal document analysis instead of brief summaries

### PDF URL Source Attribution System Fixed (August 16, 2025)
- **Critical Issue Resolved**: PDF URL null problem in search responses completely fixed 
- **Root Cause Identified**: Enhancement service batch fetch was failing, causing all PDF URLs to return null
- **Database Schema Fix**: Corrected database query to use `file_url` column instead of non-existent `pdf_url` column
- **Fallback Mechanism**: Implemented robust fallback to direct database queries when batch fetch fails
- **Enhancement Service Optimization**: Streamlined PDF URL retrieval with proper error handling and fallback paths
- **Production Testing**: Manual tests confirm PDF URLs now correctly return: `https://cdn.mevzuatgpt.org/documents/[file-id].pdf`
- **Search Response Quality**: All search results now include proper PDF download links for source document access
- **Debug Cleanup**: Removed verbose logging while maintaining essential error tracking and fallback functionality