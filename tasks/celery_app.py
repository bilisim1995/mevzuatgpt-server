"""
Celery application configuration
Sets up distributed task queue for background processing
"""

from celery import Celery
import logging
from core.config import settings

logger = logging.getLogger(__name__)

# Create Celery app instance
celery_app = Celery(
    "mevzuat_gpt",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "tasks.document_processor"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
    
    # Task execution settings
    task_always_eager=False,
    task_eager_propagates=True,
    task_ignore_result=False,
    task_store_eager_result=True,
    
    # CRITICAL: Task persistence settings - prevents task loss on worker restart
    task_acks_late=True,  # Tasks acknowledged AFTER completion, not before
    task_reject_on_worker_lost=True,  # Requeue tasks if worker crashes/restarts
    task_track_started=True,  # Track task state when it starts
    worker_prefetch_multiplier=1,  # Only fetch one task at a time
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Broker connection retry
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # CRITICAL: Redis connection pool optimization
    broker_pool_limit=5,  # Max 5 broker connections
    broker_transport_options={
        'max_connections': 5,
    },
    redis_max_connections=5,  # Redis connection pool size
    
    # Task routing
    task_routes={
        "tasks.document_processor.process_document_task": {"queue": "celery"},
        "tasks.document_processor.bulk_process_documents_task": {"queue": "celery"},
        "tasks.document_processor.cleanup_failed_documents": {"queue": "celery"},
    },
    
    # Task retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    result_backend_transport_options={
        'visibility_timeout': 3600,
        'max_connections': 5,
    },
    
    # Beat scheduler settings (for periodic tasks)
    beat_schedule={
        "cleanup-failed-documents": {
            "task": "tasks.document_processor.cleanup_failed_documents",
            "schedule": 3600.0,  # Every hour
        },
    },
)

# Task error handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
    logger.info("Debug task executed successfully")
    return "Debug task completed"

# Application events
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic maintenance tasks"""
    logger.info("Celery periodic tasks configured")

# Worker events
@celery_app.on_after_finalize.connect
def setup_workers(sender, **kwargs):
    """Setup worker configuration after finalize"""
    logger.info("Celery workers configured")

# Error handling
class CeleryTaskError(Exception):
    """Custom exception for Celery task errors"""
    pass

# Task state constants
class TaskStates:
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"

# Logging configuration for Celery
def setup_celery_logging():
    """Setup logging configuration for Celery workers"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Reduce noise from some libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)

# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Health check task for monitoring"""
    return {
        "status": "healthy",
        "worker_id": self.request.id,
        "timestamp": str(logger.info.__class__.__name__)
    }

if __name__ == "__main__":
    celery_app.start()
