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