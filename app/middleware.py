"""Middleware for request/response handling."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uuid
import logging
from contextvars import ContextVar

# Context variables for request data
REQUEST_CONTEXT_REQUESTOR_ID: ContextVar[str] = ContextVar('requestor_id', default='anonymous')
REQUEST_CONTEXT_CORRELATION_ID: ContextVar[str] = ContextVar('correlation_id', default='')

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and store request context like:
    - X-Requestor-Id header (required for DDL/DML operations)
    - X-Correlation-Id header (for request tracing)
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and extract context headers."""
        
        # Extract or generate Correlation ID
        correlation_id = request.headers.get('X-Correlation-Id', str(uuid.uuid4()))
        REQUEST_CONTEXT_CORRELATION_ID.set(correlation_id)
        
        # Extract Requestor ID from header
        requestor_id = request.headers.get('X-Requestor-Id', 'anonymous')
        REQUEST_CONTEXT_REQUESTOR_ID.set(requestor_id)
        
        # Log request context
        logger.debug(
            f"Request received",
            extra={
                'correlation_id': correlation_id,
                'requestor_id': requestor_id,
                'method': request.method,
                'path': request.url.path
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers['X-Correlation-Id'] = correlation_id
        
        return response


def get_correlation_id() -> str:
    """Get the current request correlation ID from context."""
    return REQUEST_CONTEXT_CORRELATION_ID.get()


def get_requestor_id() -> str:
    """Get the current requestor ID from context."""
    return REQUEST_CONTEXT_REQUESTOR_ID.get()
