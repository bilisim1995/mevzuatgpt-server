"""
Response utility functions
Standardized API response formatting for consistency
"""

from typing import Any, Optional, Dict
from datetime import datetime
from fastapi.responses import JSONResponse
from fastapi import status

def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Create standardized success response
    
    Args:
        data: Response data
        message: Optional success message
        status_code: HTTP status code
        headers: Optional response headers
        
    Returns:
        JSONResponse with standardized format
    """
    response_body = {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    if data is not None:
        response_body["data"] = data
    
    if message:
        response_body["message"] = message
    
    return JSONResponse(
        content=response_body,
        status_code=status_code,
        headers=headers
    )

def error_response(
    message: str,
    detail: Optional[str] = None,
    error_code: Optional[str] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    extra_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Create standardized error response
    
    Args:
        message: Error message for users
        detail: Detailed error information
        error_code: Application-specific error code
        status_code: HTTP status code
        extra_data: Additional error data
        headers: Optional response headers
        
    Returns:
        JSONResponse with standardized error format
    """
    error_dict = {
        "message": message,
        "code": error_code or "UNKNOWN_ERROR"
    }
    
    if detail:
        error_dict["detail"] = detail
    
    if extra_data:
        error_dict.update(extra_data)
    
    response_body = {
        "success": False,
        "error": error_dict,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return JSONResponse(
        content=response_body,
        status_code=status_code,
        headers=headers
    )

def paginated_response(
    items: list,
    total_count: int,
    page: int,
    limit: int,
    message: Optional[str] = None
) -> JSONResponse:
    """
    Create standardized paginated response
    
    Args:
        items: List of items for current page
        total_count: Total number of items
        page: Current page number
        limit: Items per page
        message: Optional message
        
    Returns:
        JSONResponse with pagination metadata
    """
    total_pages = (total_count + limit - 1) // limit
    
    data = {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "next_page": page + 1 if page < total_pages else None,
            "prev_page": page - 1 if page > 1 else None
        }
    }
    
    return success_response(data=data, message=message)

def created_response(
    data: Any,
    message: str = "Resource created successfully",
    location: Optional[str] = None
) -> JSONResponse:
    """
    Create standardized response for resource creation
    
    Args:
        data: Created resource data
        message: Success message
        location: Optional Location header value
        
    Returns:
        JSONResponse with 201 status code
    """
    headers = {}
    if location:
        headers["Location"] = location
    
    return success_response(
        data=data,
        message=message,
        status_code=status.HTTP_201_CREATED,
        headers=headers if headers else None
    )

def no_content_response(message: str = "Operation completed successfully") -> JSONResponse:
    """
    Create standardized response for operations with no content
    
    Args:
        message: Success message
        
    Returns:
        JSONResponse with 204 status code
    """
    return JSONResponse(
        content=None,
        status_code=status.HTTP_204_NO_CONTENT
    )

def accepted_response(
    data: Any = None,
    message: str = "Request accepted for processing"
) -> JSONResponse:
    """
    Create standardized response for accepted requests (async operations)
    
    Args:
        data: Optional response data (e.g., task ID)
        message: Acceptance message
        
    Returns:
        JSONResponse with 202 status code
    """
    return success_response(
        data=data,
        message=message,
        status_code=status.HTTP_202_ACCEPTED
    )

def validation_error_response(
    field_errors: Dict[str, list],
    message: str = "Validation failed"
) -> JSONResponse:
    """
    Create standardized response for validation errors
    
    Args:
        field_errors: Dictionary of field names and their error messages
        message: General validation error message
        
    Returns:
        JSONResponse with 400 status code and field errors
    """
    return error_response(
        message=message,
        error_code="VALIDATION_ERROR",
        status_code=status.HTTP_400_BAD_REQUEST,
        extra_data={"field_errors": field_errors}
    )

def unauthorized_response(message: str = "Authentication required") -> JSONResponse:
    """
    Create standardized response for authentication failures
    
    Args:
        message: Authentication error message
        
    Returns:
        JSONResponse with 401 status code
    """
    headers = {"WWW-Authenticate": "Bearer"}
    
    return error_response(
        message=message,
        error_code="AUTHENTICATION_REQUIRED",
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers=headers
    )

def forbidden_response(message: str = "Access denied") -> JSONResponse:
    """
    Create standardized response for authorization failures
    
    Args:
        message: Authorization error message
        
    Returns:
        JSONResponse with 403 status code
    """
    return error_response(
        message=message,
        error_code="ACCESS_DENIED",
        status_code=status.HTTP_403_FORBIDDEN
    )

def not_found_response(
    message: str = "Resource not found",
    resource_type: Optional[str] = None
) -> JSONResponse:
    """
    Create standardized response for not found errors
    
    Args:
        message: Not found error message
        resource_type: Type of resource that was not found
        
    Returns:
        JSONResponse with 404 status code
    """
    extra_data = {}
    if resource_type:
        extra_data["resource_type"] = resource_type
    
    return error_response(
        message=message,
        error_code="NOT_FOUND",
        status_code=status.HTTP_404_NOT_FOUND,
        extra_data=extra_data if extra_data else None
    )

def conflict_response(message: str = "Resource conflict") -> JSONResponse:
    """
    Create standardized response for conflict errors
    
    Args:
        message: Conflict error message
        
    Returns:
        JSONResponse with 409 status code
    """
    return error_response(
        message=message,
        error_code="CONFLICT",
        status_code=status.HTTP_409_CONFLICT
    )

def rate_limit_response(
    message: str = "Rate limit exceeded",
    retry_after: Optional[int] = None
) -> JSONResponse:
    """
    Create standardized response for rate limit errors
    
    Args:
        message: Rate limit error message
        retry_after: Seconds to wait before retrying
        
    Returns:
        JSONResponse with 429 status code
    """
    headers = {}
    extra_data = {}
    
    if retry_after:
        headers["Retry-After"] = str(retry_after)
        extra_data["retry_after"] = retry_after
    
    return error_response(
        message=message,
        error_code="RATE_LIMIT_EXCEEDED",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        extra_data=extra_data if extra_data else None,
        headers=headers if headers else None
    )

def service_unavailable_response(
    message: str = "Service temporarily unavailable",
    retry_after: Optional[int] = None
) -> JSONResponse:
    """
    Create standardized response for service unavailable errors
    
    Args:
        message: Service unavailable message
        retry_after: Seconds to wait before retrying
        
    Returns:
        JSONResponse with 503 status code
    """
    headers = {}
    extra_data = {}
    
    if retry_after:
        headers["Retry-After"] = str(retry_after)
        extra_data["retry_after"] = retry_after
    
    return error_response(
        message=message,
        error_code="SERVICE_UNAVAILABLE",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        extra_data=extra_data if extra_data else None,
        headers=headers if headers else None
    )
