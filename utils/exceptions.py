"""
Custom exception classes for the application
Provides structured error handling with proper HTTP status codes
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status

class AppException(Exception):
    """
    Base application exception class
    
    This exception is used throughout the application to provide
    consistent error handling with proper HTTP status codes.
    """
    
    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize AppException
        
        Args:
            message: Main error message for users
            detail: Detailed error information (for developers)
            status_code: HTTP status code
            error_code: Application-specific error code
            extra_data: Additional data to include in error response
        """
        self.message = message
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code
        self.extra_data = extra_data or {}
        
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        error_dict = {
            "message": self.message,
            "status_code": self.status_code
        }
        
        if self.detail:
            error_dict["detail"] = self.detail
        
        if self.error_code:
            error_dict["code"] = self.error_code
        
        if self.extra_data:
            error_dict.update(self.extra_data)
        
        return error_dict

class ValidationError(AppException):
    """Exception for data validation errors"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if field:
            extra_data["field"] = field
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class AuthenticationError(AppException):
    """Exception for authentication failures"""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        detail: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            **kwargs
        )

class AuthorizationError(AppException):
    """Exception for authorization failures"""
    
    def __init__(
        self,
        message: str = "Access denied",
        detail: Optional[str] = None,
        required_role: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if required_role:
            extra_data["required_role"] = required_role
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class NotFoundError(AppException):
    """Exception for resource not found errors"""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if resource_type:
            extra_data["resource_type"] = resource_type
        if resource_id:
            extra_data["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class ConflictError(AppException):
    """Exception for resource conflict errors"""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        detail: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
            **kwargs
        )

class RateLimitError(AppException):
    """Exception for rate limit exceeded errors"""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if retry_after:
            extra_data["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class ServiceUnavailableError(AppException):
    """Exception for service unavailable errors"""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service_name: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if service_name:
            extra_data["service_name"] = service_name
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class ExternalServiceError(AppException):
    """Exception for external service integration errors"""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        service_error: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        extra_data["service_name"] = service_name
        if service_error:
            extra_data["service_error"] = service_error
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class DatabaseError(AppException):
    """Exception for database operation errors"""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if operation:
            extra_data["operation"] = operation
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

class FileProcessingError(AppException):
    """Exception for file processing errors"""
    
    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        file_type: Optional[str] = None,
        detail: Optional[str] = None,
        **kwargs
    ):
        extra_data = kwargs.get("extra_data", {})
        if filename:
            extra_data["filename"] = filename
        if file_type:
            extra_data["file_type"] = file_type
        
        super().__init__(
            message=message,
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="FILE_PROCESSING_ERROR",
            extra_data=extra_data,
            **{k: v for k, v in kwargs.items() if k != "extra_data"}
        )

# Exception mapping for common HTTP status codes
STATUS_CODE_EXCEPTIONS = {
    400: ValidationError,
    401: AuthenticationError,
    403: AuthorizationError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}

def get_exception_for_status_code(status_code: int) -> type:
    """
    Get appropriate exception class for HTTP status code
    
    Args:
        status_code: HTTP status code
        
    Returns:
        Exception class
    """
    return STATUS_CODE_EXCEPTIONS.get(status_code, AppException)
