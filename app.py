#!/usr/bin/env python3
"""
MevzuatGPT Application Entry Point
Production-ready FastAPI application launcher with proper configuration
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings
from core.logging import setup_logging

def main():
    """Main application entry point"""
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Log startup information
    logger.info("=" * 60)
    logger.info("MevzuatGPT API Server Starting")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"Python Version: {sys.version}")
    logger.info(f"Working Directory: {os.getcwd()}")
    logger.info("=" * 60)
    
    # Configure uvicorn based on environment
    if settings.ENVIRONMENT == "production":
        # Production configuration
        uvicorn_config = {
            "app": "main:app",
            "host": "0.0.0.0",
            "port": 5000,
            "workers": 4,
            "log_level": "info",
            "access_log": True,
            "use_colors": False,
            "server_header": False,
            "date_header": False,
            # SSL configuration (if certificates are available)
            # "ssl_keyfile": "/path/to/key.pem",
            # "ssl_certfile": "/path/to/cert.pem",
        }
    else:
        # Development configuration
        uvicorn_config = {
            "app": "main:app",
            "host": "0.0.0.0",
            "port": 5000,
            "reload": settings.DEBUG,
            "log_level": settings.LOG_LEVEL.lower(),
            "access_log": True,
            "use_colors": True,
        }
    
    try:
        # Start the server
        logger.info(f"Starting server on {uvicorn_config['host']}:{uvicorn_config['port']}")
        uvicorn.run(**uvicorn_config)
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        sys.exit(1)
    finally:
        logger.info("MevzuatGPT API Server stopped")

def run_celery_worker():
    """Start Celery worker for background tasks"""
    import subprocess
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Celery worker for document processing")
    
    cmd = [
        "celery",
        "-A", "tasks.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2",
        "--queues=document_processing,maintenance",
        "--hostname=worker@%h"
    ]
    
    if settings.ENVIRONMENT == "development":
        cmd.extend(["--reload"])
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Celery worker shutdown requested")
    except subprocess.CalledProcessError as e:
        logger.error(f"Celery worker failed: {e}")
        sys.exit(1)

def run_celery_beat():
    """Start Celery beat scheduler for periodic tasks"""
    import subprocess
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Celery beat scheduler")
    
    cmd = [
        "celery",
        "-A", "tasks.celery_app",
        "beat",
        "--loglevel=info"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Celery beat scheduler shutdown requested")
    except subprocess.CalledProcessError as e:
        logger.error(f"Celery beat scheduler failed: {e}")
        sys.exit(1)

def run_migrations():
    """Run database migrations"""
    import subprocess
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Running database migrations")
    
    try:
        # Run Alembic migrations
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        logger.info("Database migrations completed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Database migration failed: {e}")
        sys.exit(1)

def create_migration(message: str):
    """Create a new database migration"""
    import subprocess
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    if not message:
        logger.error("Migration message is required")
        sys.exit(1)
    
    logger.info(f"Creating migration: {message}")
    
    try:
        subprocess.run(["alembic", "revision", "--autogenerate", "-m", message], check=True)
        logger.info("Migration created successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration creation failed: {e}")
        sys.exit(1)

def show_status():
    """Show application status and configuration"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("\n" + "=" * 60)
    print("MevzuatGPT Application Status")
    print("=" * 60)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug Mode: {settings.DEBUG}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Redis URL: {settings.REDIS_URL}")
    print(f"OpenAI Model: {settings.OPENAI_MODEL}")
    print(f"Embedding Model: {settings.OPENAI_EMBEDDING_MODEL}")
    print(f"Storage Zone: {settings.BUNNY_STORAGE_ZONE}")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print("=" * 60)
    
    # Test database connection
    try:
        import asyncio
        from core.database import get_db_session
        
        async def test_db():
            async with get_db_session() as db:
                await db.execute("SELECT 1")
                return True
        
        if asyncio.run(test_db()):
            print("✅ Database connection: OK")
        else:
            print("❌ Database connection: FAILED")
    except Exception as e:
        print(f"❌ Database connection: FAILED - {e}")
    
    # Test Redis connection
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print("✅ Redis connection: OK")
    except Exception as e:
        print(f"❌ Redis connection: FAILED - {e}")
    
    print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MevzuatGPT Application Manager")
    parser.add_argument("command", choices=[
        "server", "worker", "beat", "migrate", "makemigration", "status"
    ], help="Command to execute")
    parser.add_argument("-m", "--message", help="Migration message (for makemigration)")
    
    args = parser.parse_args()
    
    if args.command == "server":
        main()
    elif args.command == "worker":
        run_celery_worker()
    elif args.command == "beat":
        run_celery_beat()
    elif args.command == "migrate":
        run_migrations()
    elif args.command == "makemigration":
        create_migration(args.message or "New migration")
    elif args.command == "status":
        show_status()
