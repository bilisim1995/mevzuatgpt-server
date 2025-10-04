"""
MevzuatGPT - Production Ready RAG System
Modern FastAPI backend with role-based authentication and vector search
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import logging
import time

from core.config import settings
from core.logging import setup_logging
from api.auth.routes import router as auth_router
from api.auth.password_reset_routes import router as password_reset_router
from api.admin.routes import router as admin_router
from api.user.routes import router as user_router
from api.user.credit_routes import router as user_credit_router
from api.admin.credit_routes import router as admin_credit_router
from api.user.feedback_routes import router as user_feedback_router
from api.admin.feedback_routes import router as admin_feedback_router
from api.user.support_routes import router as user_support_router
from api.admin.support_routes import router as admin_support_router
from api.user.profile_routes import router as user_profile_router
from api.user.progress_routes import router as user_progress_router
from api.user.maintenance_routes import router as user_maintenance_router
from api.admin.maintenance_routes import router as admin_maintenance_router
from api.admin.prompt_routes import router as admin_prompt_router
from api.admin.groq_routes import router as admin_groq_router
from api.public_routes import router as public_router
from api.payment.routes import router as payment_router
from utils.exceptions import AppException

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MevzuatGPT API",
    description="Production-ready RAG system for legal document processing and search",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# CORS middleware for mobile/web integration
# Parse ALLOWED_ORIGINS from string to list
allowed_origins = [
    "https://app.mevzuatgpt.org",
    "https://yonetim.mevzuatgpt.org",  # Admin subdomain
    "https://uygulama.mevzuatgpt.org",  # Kullanıcı uygulaması
    "http://localhost:3000",  # Development
    "http://localhost:3001",  # Development - Client App
]

# Override if * specified in settings
if settings.ALLOWED_ORIGINS == "*":
    allowed_origins = ["*"]
elif settings.ALLOWED_ORIGINS:
    # Use settings if provided
    allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Custom exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"App exception: {exc.message} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.message,
                "detail": exc.detail,
                "code": exc.error_code
            }
        }
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "message": "Internal server error",
                "detail": "An unexpected error occurred",
                "code": "INTERNAL_ERROR"
            }
        }
    )

# Static files setup
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }
    }

# Root endpoint - HTML page from file
@app.get("/", response_class=HTMLResponse)
async def root():
    """Ana sayfa - MevzuatGPT tanıtım sayfası"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>MevzuatGPT</h1><p>Ana sayfa yüklenemedi</p>",
            status_code=200
        )

# API info endpoint (JSON format)
@app.get("/api")
async def api_info():
    """API bilgileri JSON formatında"""
    return {
        "message": "MevzuatGPT API",
        "description": "Hukuki belge işleme ve semantik arama sistemi",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "docs": "/docs" if settings.DEBUG else "Debug mode kapalı",
            "auth": "/api/auth/",
            "admin": "/api/admin/",
            "user": "/api/user/"
        }
    }

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(password_reset_router, tags=["Password Reset"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(admin_credit_router, tags=["Admin-Credits"])  # Admin kredi yönetimi
app.include_router(user_router, prefix="/api/user", tags=["User"])
app.include_router(user_credit_router, tags=["User-Credits"])    # Kullanıcı kredi bilgisi
app.include_router(user_feedback_router, prefix="/api/user", tags=["User-Feedback"])    # Kullanıcı feedback sistemi
app.include_router(admin_feedback_router, prefix="/api/admin", tags=["Admin-Feedback"])  # Admin feedback yönetimi
app.include_router(user_support_router, prefix="/api/user", tags=["User-Support"])       # Kullanıcı destek sistemi
app.include_router(admin_support_router, prefix="/api/admin", tags=["Admin-Support"])    # Admin destek yönetimi
app.include_router(user_profile_router, prefix="/api/user", tags=["User-Profile"])       # Kullanıcı profil yönetimi
app.include_router(user_progress_router, prefix="/api/user", tags=["User-Progress"])          # Kullanıcı progress takibi
app.include_router(user_maintenance_router, prefix="/api/maintenance", tags=["Maintenance"])  # Bakım modu durumu
app.include_router(admin_maintenance_router, prefix="/api/admin", tags=["Admin-Maintenance"])  # Admin bakım yönetimi
app.include_router(admin_prompt_router, prefix="/api/admin", tags=["Admin-Prompts"])       # Admin prompt yönetimi
app.include_router(admin_groq_router, prefix="/api/admin", tags=["Admin-Groq"])                  # Admin Groq ayarları yönetimi
app.include_router(public_router, prefix="/api", tags=["Public"])                                  # Public endpoints
app.include_router(payment_router, prefix="/api/payment", tags=["Payment"])                        # İyzico payment endpoints

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("MevzuatGPT API starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("MevzuatGPT API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
