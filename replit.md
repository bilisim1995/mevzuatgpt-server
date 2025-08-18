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

### Missing Database Tables Migration Created (August 18, 2025)
- **Safe Migration Strategy**: Created tables without foreign keys first, then added constraints to avoid dependency errors
- **Legacy Compatibility Tables**: Added search_logs, user_credit_balance, user_credits, user_feedback, support_tickets, support_messages
- **Foreign Key Management**: Used DO blocks to conditionally add foreign keys only if they don't exist
- **Complete Schema**: All indexes, triggers, and initial data setup included for production readiness
- **Migration File**: safe_missing_tables_migration.sql ready for production deployment

### User Registration Schema Fixed (August 18, 2025)
- **Preferences Column Issue Resolved**: Removed problematic `preferences` JSONB column reference from registration
- **Essential Fields Only**: Registration now uses only existing columns (user_id, email, full_name, role, credits)
- **Database Field Validation**: Eliminated all non-existent column references to prevent schema cache errors
- **Simplified Profile Creation**: User profiles created with minimal required fields, avoiding complex JSONB operations
- **Registration Flow Stabilized**: Complete registration process now functional without schema dependency issues

### Admin Credit System Fully Operational (August 18, 2025)
- **Admin Credit Bypass**: Admin users now have unlimited credits (999999) and bypass all credit deduction processes
- **Database Field Mapping**: Fixed `user_profiles` query from `id` to `user_id` in credit service admin validation
- **Credit Balance Override**: Admin users receive unlimited credit balance without requiring database records
- **Deduction Bypass**: Admin credit deduction operations are bypassed with logging for audit trails
- **Production Ready**: Admin accounts can perform unlimited queries without credit restrictions

### Document Upload System Fixed (August 18, 2025)
- **Authentication Issue Resolved**: Fixed user profile query from `id` to `user_id` field mapping in authentication service
- **Database Schema Alignment**: Updated Supabase client to use correct `documents` table instead of deprecated `mevzuat_documents`
- **Column Mapping Fixed**: Aligned document creation with actual database schema (removed non-existent `content_preview` field)
- **Upload Flow Optimized**: File upload to Bunny.net working, metadata properly mapped to database schema fields
- **Processing Status**: Document status correctly set as 'active' with 'pending' processing_status for Celery processing

### Supabase Auth System Fully Operational (August 18, 2025) 
- **Auth System Restoration**: Successfully restored native Supabase Auth functionality after environment configuration updates
- **Login Endpoint**: Now using native Supabase Auth API (HTTP 200 OK) instead of direct database authentication
- **Authentication Flow**: Seamless integration with self-hosted Supabase at https://supabase.mevzuatgpt.org/auth/v1/
- **Admin Access**: Full admin authentication working with admin@mevzuatgpt.com credentials
- **Direct Database Fallback**: Maintained as backup system but no longer needed for primary authentication
- **Production Status**: Native Supabase Auth fully operational and production-ready

### Self-hosted Supabase Migration Complete (August 17, 2025)
- **Infrastructure Migration**: Successfully migrated to self-hosted Supabase at https://supabase.mevzuatgpt.org
- **Database Schema**: Deployed complete Elasticsearch-optimized schema with 12 tables
- **Connection Testing**: All 5 infrastructure tests passing (Database, REST API, Auth API, Storage API, Elasticsearch)
- **Auth System**: Fixed role-based authentication with admin user (admin@mevzuatgpt.com) properly configured
- **Database URL**: Working connection string `postgresql://postgres.5556795:ObMevzuat2025Pas@supabase.mevzuatgpt.org:5432/postgres`
- **Tables Deployed**: user_profiles, documents, search_history, elasticsearch_sync_log, support_tickets, support_messages, user_credits, user_credit_balance, user_feedback, maintenance_mode + monitoring views
- **Elasticsearch Integration**: Vector operations ready at https://elastic.mevzuatgpt.org (Version 8.19.2)
- **Production Ready**: Complete infrastructure operational with PostgreSQL for metadata and Elasticsearch for vector operations

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