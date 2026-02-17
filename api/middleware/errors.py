"""
MyCasa Pro - Standardized Error Handling Middleware
All API errors return consistent structure with correlation IDs.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Optional, Any, Dict
from datetime import datetime
import uuid
import logging
import traceback


logger = logging.getLogger("mycasa.api.errors")


class APIException(Exception):
    """
    Base exception for all MyCasa API errors.
    
    All errors include:
    - code: Machine-readable error code
    - message: Human-readable description
    - details: Additional context (optional)
    - correlation_id: UUID for tracking
    """
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ValidationError(APIException):
    """Request validation failed"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class NotFoundError(APIException):
    """Resource not found"""
    
    def __init__(self, resource: str, identifier: Optional[str] = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} not found: {identifier}"
        super().__init__(
            code="NOT_FOUND",
            message=message,
            status_code=404,
            details={"resource": resource, "identifier": identifier},
        )


class ConflictError(APIException):
    """Resource conflict (duplicate, invalid state, etc.)"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            details=details,
        )


class UnauthorizedError(APIException):
    """Authentication required or failed"""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class ForbiddenError(APIException):
    """Action not permitted"""
    
    def __init__(self, message: str = "Action not permitted"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


class RateLimitError(APIException):
    """Rate limit exceeded"""
    
    def __init__(self, retry_after: Optional[int] = None):
        details = {"retry_after_seconds": retry_after} if retry_after else None
        super().__init__(
            code="RATE_LIMITED",
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            details=details,
        )


class ServiceUnavailableError(APIException):
    """Service temporarily unavailable"""
    
    def __init__(self, service: str, message: Optional[str] = None):
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message or f"{service} is temporarily unavailable",
            status_code=503,
            details={"service": service},
        )


def _build_error_response(
    code: str,
    message: str,
    details: Optional[Any] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build standardized error response"""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Central error handler for all exceptions.
    
    Converts exceptions to standardized JSON responses.
    """
    correlation_id = str(uuid.uuid4())
    
    # Get request info for logging
    request_info = {
        "method": request.method,
        "path": str(request.url.path),
        "correlation_id": correlation_id,
    }
    
    if isinstance(exc, APIException):
        # Our custom exceptions
        logger.warning(
            f"API Error: {exc.code} - {exc.message}",
            extra={**request_info, "error_code": exc.code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                correlation_id=correlation_id,
            ),
        )
    
    elif isinstance(exc, RequestValidationError):
        # FastAPI validation errors
        errors = exc.errors()
        logger.warning(
            f"Validation Error: {len(errors)} errors",
            extra={**request_info, "validation_errors": errors},
        )
        return JSONResponse(
            status_code=422,
            content=_build_error_response(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": errors},
                correlation_id=correlation_id,
            ),
        )
    
    elif isinstance(exc, StarletteHTTPException):
        # Standard HTTP exceptions
        logger.warning(
            f"HTTP Error: {exc.status_code} - {exc.detail}",
            extra={**request_info, "status_code": exc.status_code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_build_error_response(
                code=f"HTTP_{exc.status_code}",
                message=str(exc.detail),
                correlation_id=correlation_id,
            ),
        )
    
    else:
        # Unexpected errors - log full traceback
        logger.error(
            f"Unexpected Error: {type(exc).__name__}: {exc}",
            extra={**request_info, "traceback": traceback.format_exc()},
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=_build_error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"type": type(exc).__name__} if logger.level <= logging.DEBUG else None,
                correlation_id=correlation_id,
            ),
        )


def setup_error_handlers(app: FastAPI) -> None:
    """
    Register error handlers with FastAPI app.
    
    Call this during app startup:
        setup_error_handlers(app)
    """
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        return error_handler(request, exc)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return error_handler(request, exc)
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return error_handler(request, exc)
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return error_handler(request, exc)
