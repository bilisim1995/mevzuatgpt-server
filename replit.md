# MevzuatGPT

## Overview
MevzuatGPT is a production-ready RAG (Retrieval-Augmented Generation) system for legal document processing and semantic search. It allows admin users to upload legal PDF documents, which are then processed, vectorized, and made searchable through AI-powered queries. The system provides comprehensive document management with role-based access control, supporting both document search and intelligent question-answering capabilities. It functions as a legal research assistant, enabling users to query complex legal documents in natural language and receive contextually relevant answers with source attribution and confidence scoring.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
The application is built on FastAPI, chosen for its high-performance asynchronous capabilities, automatic OpenAPI documentation, and native Pydantic integration.

### Database and Storage
The system uses a multi-tiered storage approach:
- **Primary Database**: Self-hosted Supabase PostgreSQL at https://supabase.mevzuatgpt.org for authentication/user management/document metadata with Row Level Security (RLS) policies.
- **Vector Storage**: Elasticsearch at https://elastic.mevzuatgpt.org/ for ALL vector operations and similarity search with 1536-dimensional embeddings from OpenAI's `text-embedding-3-small` model.
- **File Storage**: PDF documents are stored on Bunny.net CDN with automatic URL generation to https://cdn.mevzuatgpt.org/documents/ format.
- **Cache Layer**: Redis Cloud provides caching for search results, rate limiting, and session management.

#### Complete Database Schema (Updated August 20, 2025)
All required tables are now present and functional in Supabase:
- `user_profiles` - User authentication and role management
- `mevzuat_documents` - PDF document metadata with filename/file_url/category support  
- `search_logs` - Query history and analytics
- `ai_prompts` - Dynamic AI prompt management for runtime updates
- `support_tickets` - User support ticket system
- `user_credits` - Credit balance management
- `credit_transactions` - Credit transaction history

Note: Vector embeddings are stored in Elasticsearch, NOT in Supabase database.

#### PDF Upload System (Fixed August 20, 2025)
Document upload workflow fully operational:
- File upload to Bunny.net CDN with automatic URL generation
- Metadata storage in Supabase with proper column mapping
- Background processing via Celery for text extraction and vectorization
- Elasticsearch indexing for semantic search capabilities

### Authentication and Authorization
Role-based access control (RBAC) is implemented via Supabase Auth. Roles include:
- **Admin**: Full document upload, management, and administrative functions.
- **User**: Document search and query capabilities.
JWT tokens are managed by Supabase with automatic refresh and integrated with database-level RLS.

### Document Processing Pipeline
An asynchronous processing pipeline handles documents:
1.  **Upload**: PDFs are uploaded to Bunny.net CDN with metadata stored in `mevzuat_documents` table.
2.  **Text Extraction**: Multi-method PDF parsing using `pdfplumber` with fallbacks.
3.  **Text Chunking**: Intelligent text splitting with overlap preservation using LangChain.
4.  **Vectorization**: Batch embedding generation via OpenAI API with 1536-dimensional vectors.
5.  **Storage**: Vector embeddings stored in Elasticsearch for semantic search and similarity matching.
6.  **Background Processing**: Celery workers manage long-running tasks with Redis queue.

#### PDF URL Resolution System (Fixed August 20, 2025)
A three-tier fallback system ensures all documents have accessible URLs:
1. **Primary**: Use existing `file_url` from database if present
2. **Fallback**: Generate CDN URL from `filename`: `https://cdn.mevzuatgpt.org/documents/{filename}`
3. **Final**: Use `document_title` as filename for URL generation if needed

### AI and Search Architecture
The query processing system supports multiple AI providers with dynamic prompt management:
-   **Primary**: Groq API for fast, cost-effective inference using Llama models.
-   **Fallback**: OpenAI GPT-4o for complex reasoning tasks.
-   **Dynamic Prompts**: AI prompts are stored in Supabase `ai_prompts` table and loaded dynamically at runtime.
-   **Prompt Management**: Admin panel for updating AI behavior without server restart.
-   **Search**: `pgvector`-powered semantic search with configurable similarity thresholds.
-   **Institution Filtering**: Document-level pre-filtering by institution before vector search for performance.
-   **Smart Credit Refund**: Automatic credit refund for "no information found" responses.

### Reliability and Quality Control
A comprehensive confidence scoring mechanism includes:
-   Source Reliability Scoring.
-   Content Consistency Analysis.
-   Technical Accuracy Assessment.
-   Currency Evaluation.

### UI/UX Decisions
The system supports a support ticket system, user credit management, password reset functionality, and advanced query filtering. AI responses are enhanced for length and creativity, with a focus on detailed legal analysis. PDF URL source attribution is integrated for direct document access.

### Password Reset System
A comprehensive password reset system has been implemented with enterprise-grade security:
- **Email-Based Reset**: Users can request password reset via email address
- **Secure Token Management**: Reset tokens are stored in Redis with 24-hour TTL for automatic expiry
- **Email Notifications**: SendGrid integration for professional password reset emails
- **Security Features**: Email enumeration protection, secure token generation, and automatic cleanup
- **API Endpoints**:
  - `POST /api/auth/forgot-password`: Request password reset
  - `POST /api/auth/reset-password`: Confirm password reset with token
  - `POST /api/auth/verify-reset-token`: Validate reset token

### Dynamic AI Prompt System
Real-time AI behavior management without server restarts:
- **Database-Driven Prompts**: AI prompts stored in Supabase `ai_prompts` table
- **Cached Performance**: 5-minute cache for optimal performance with manual refresh capability
- **Version Control**: Prompt versioning and history tracking for rollback support
- **Admin Management**: Full CRUD operations via `/api/admin/prompts/*` endpoints
- **Fallback Protection**: Default prompts ensure system stability if database unavailable
- **Multi-Provider Support**: Separate prompts for Groq, OpenAI, and future AI providers

### Email Notification System (October 2025)
Dual email system for different notification types:
- **SMTP (Hostinger)**: Automated credit purchase notifications via `info@mevzuatgpt.org` (auth) with `no-reply@mevzuatgpt.org` as sender
- **SendGrid**: Password reset and account security notifications only
- **Port Support**: Dual-mode SMTP with Port 587 (TLS/STARTTLS) primary and Port 465 (SSL) fallback
- **Professional Templates**: HTML/plain-text email templates with MevzuatGPT branding
- **Automatic Delivery**: Credit purchase confirmations sent immediately after successful payment
- **Error Resilience**: Email failures don't affect core transactions (credit additions proceed regardless)

### Document Comparison System with File Upload (October 2025)
Advanced document comparison supporting direct file uploads:
- **File Upload Support**: POST `/api/user/compare-documents-upload` endpoint for multipart/form-data uploads
- **Multi-Format Support**: PDF (pdfplumber), Word (.docx via python-docx), Images (OCR), Text files
- **OCR Integration**: Tesseract OCR 5.5 for image-based OCR with 85% accuracy (no API key required)
- **NLP Processing**: Automatic text cleaning, normalization, Turkish character preservation
- **Confidence Scoring**: Each extraction includes confidence score and method information
- **Analysis Levels**: Three-tier analysis (yuzeysel/normal/detayli) with customizable depth
- **File Size Limit**: 10MB maximum per file with automatic validation
- **Markdown Output**: Structured comparison reports with emoji indicators (✅ added, ❌ removed, 🔄 modified)

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

### Document Processing Libraries
-   **pdfplumber**: Primary PDF text extraction library.
-   **PyPDF2**: Fallback PDF processing library.
-   **LangChain**: For text splitting and chunking.

### Python Framework Dependencies
-   **FastAPI**: High-performance async web framework.
-   **SQLAlchemy**: Async ORM for database operations.
-   **Pydantic**: Data validation and serialization.
-   **asyncpg**: High-performance PostgreSQL driver.