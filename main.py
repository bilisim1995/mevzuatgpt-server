"""
MevzuatGPT - Production Ready RAG System
Modern FastAPI backend with role-based authentication and vector search
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import logging
import time

from core.config import settings
from core.logging import setup_logging
from api.auth.routes import router as auth_router
from api.admin.routes import router as admin_router
from api.user.routes import router as user_router
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
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

# Root endpoint - HTML page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Ana sayfa - Mevzuat GPT"""
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mevzuat GPT - Hukuki Belge Sistemi</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center;
            }
            .container { 
                text-align: center; padding: 2rem; max-width: 800px; 
                background: rgba(255,255,255,0.1); backdrop-filter: blur(10px);
                border-radius: 20px; border: 1px solid rgba(255,255,255,0.2);
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }
            h1 { 
                font-size: 3.5rem; margin-bottom: 1rem; 
                background: linear-gradient(45deg, #fff, #e0e0e0);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                background-clip: text; text-shadow: 0 2px 10px rgba(0,0,0,0.3);
            }
            .subtitle { 
                font-size: 1.3rem; margin-bottom: 2rem; opacity: 0.9;
                font-weight: 300; letter-spacing: 0.5px;
            }
            .features { 
                display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
                gap: 1.5rem; margin: 2rem 0; 
            }
            .feature { 
                padding: 1.5rem; background: rgba(255,255,255,0.1); 
                border-radius: 15px; border: 1px solid rgba(255,255,255,0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .feature:hover { 
                transform: translateY(-5px); 
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            }
            .feature h3 { margin-bottom: 0.5rem; color: #fff; font-size: 1.2rem; }
            .feature p { opacity: 0.8; line-height: 1.5; }
            .api-info { 
                margin-top: 2rem; padding: 1.5rem; 
                background: rgba(0,0,0,0.2); border-radius: 15px;
                border: 1px solid rgba(255,255,255,0.1);
            }
            .endpoints { 
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 1rem; margin-top: 1rem; 
            }
            .endpoint { 
                padding: 0.8rem; background: rgba(255,255,255,0.1); 
                border-radius: 10px; font-family: monospace; font-size: 0.9rem;
                border: 1px solid rgba(255,255,255,0.2);
            }
            .status { 
                display: inline-block; padding: 0.3rem 0.8rem; 
                background: #27ae60; border-radius: 20px; 
                font-size: 0.8rem; margin-top: 1rem;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .footer { 
                margin-top: 2rem; opacity: 0.7; 
                font-size: 0.9rem; border-top: 1px solid rgba(255,255,255,0.2);
                padding-top: 1rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Mevzuat GPT</h1>
            <p class="subtitle">Yapay Zeka Destekli Hukuki Belge İşleme ve Semantik Arama Sistemi</p>
            
            <div class="features">
                <div class="feature">
                    <h3>📄 Belge İşleme</h3>
                    <p>PDF hukuki belgeleri otomatik olarak analiz eder ve içeriği vektör formatına çevirir</p>
                </div>
                <div class="feature">
                    <h3>🔍 Semantik Arama</h3>
                    <p>Doğal dil ile arama yapın, AI anlam çıkararak en ilgili sonuçları bulur</p>
                </div>
                <div class="feature">
                    <h3>🔐 Güvenli Erişim</h3>
                    <p>Rol tabanlı erişim kontrolü ile admin ve kullanıcı yetkilendirmesi</p>
                </div>
                <div class="feature">
                    <h3>⚡ Yüksek Performans</h3>
                    <p>FastAPI ve PostgreSQL vector search ile hızlı ve ölçeklenebilir</p>
                </div>
            </div>

            <div class="api-info">
                <h3>🚀 API Bilgileri</h3>
                <p><strong>Versiyon:</strong> 1.0.0 | <strong>Ortam:</strong> """ + settings.ENVIRONMENT + """</p>
                <div class="endpoints">
                    <div class="endpoint">/health<br><small>Sistem durumu</small></div>
                    <div class="endpoint">/api/auth/<br><small>Kimlik doğrulama</small></div>
                    <div class="endpoint">/api/admin/<br><small>Admin işlemleri</small></div>
                    <div class="endpoint">/api/user/<br><small>Kullanıcı işlemleri</small></div>
                </div>
                <div class="status">🟢 Sistem Çalışıyor</div>
            </div>

            <div class="footer">
                <p>MevzuatGPT © 2025 | Modern hukuki belge yönetimi için tasarlandı</p>
                <p><small>FastAPI + Supabase + OpenAI + Redis Cloud + Bunny.net</small></p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

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
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(user_router, prefix="/api/user", tags=["User"])

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
