"""Simplified observability module for initial testing."""

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import Request

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SERVICE_NAME = os.getenv("SERVICE_NAME", "prethrift-backend")


def configure_structured_logging():
    """Configure structured logging with context injection."""

    if ENVIRONMENT == "production":
        # JSON formatting for production
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Console formatting for development
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


async def logging_middleware(request: Request, call_next):
    """Middleware for structured logging."""

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Set context variables
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None
    )

    # Start timing
    start_time = time.time()

    # Get logger
    logger = structlog.get_logger(__name__)

    # Log request start
    logger.info(
        "Request started",
        method=request.method,
        path=request.url.path,
        query_params=dict(request.query_params)
    )

    try:
        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log successful response
        logger.info(
            "Request completed",
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as exc:
        # Calculate duration
        duration = time.time() - start_time

        # Log error
        logger.error(
            "Request failed",
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=round(duration * 1000, 2),
            exc_info=True
        )

        # Re-raise exception to be handled by FastAPI
        raise


def get_logger(name: Optional[str] = None):
    """Get a structured logger instance."""
    return structlog.get_logger(name or __name__)


# Context managers for operation tracking
@asynccontextmanager
async def track_search_operation(search_type: str, logger=None):
    """Context manager for tracking search operations."""
    if logger is None:
        logger = get_logger()

    start_time = time.time()

    try:
        logger.info("Search operation started", search_type=search_type)
        yield

        duration = time.time() - start_time
        logger.info(
            "Search operation completed",
            search_type=search_type,
            duration_ms=round(duration * 1000, 2)
        )

    except Exception as exc:
        duration = time.time() - start_time
        logger.error(
            "Search operation failed",
            search_type=search_type,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=round(duration * 1000, 2),
            exc_info=True
        )
        raise


@asynccontextmanager
async def track_embedding_operation(operation_type: str, logger=None):
    """Context manager for tracking embedding operations."""
    if logger is None:
        logger = get_logger()

    start_time = time.time()

    try:
        logger.info("Embedding operation started", operation_type=operation_type)
        yield

        duration = time.time() - start_time
        logger.info(
            "Embedding operation completed",
            operation_type=operation_type,
            duration_ms=round(duration * 1000, 2)
        )

    except Exception as exc:
        duration = time.time() - start_time
        logger.error(
            "Embedding operation failed",
            operation_type=operation_type,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=round(duration * 1000, 2),
            exc_info=True
        )
        raise


def create_prometheus_metrics_endpoint():
    """Create simple metrics endpoint placeholder."""

    async def metrics_endpoint():
        """Return basic metrics."""
        return "# HELP http_requests_total Total HTTP requests\n# TYPE http_requests_total counter\nhttp_requests_total 0\n"

    return metrics_endpoint


def instrument_app(app):
    """Placeholder for app instrumentation."""
    pass


# Initialize logging
configure_structured_logging()
