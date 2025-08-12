"""Observability configuration for structured logging, tracing, and monitoring."""

import os
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
import structlog.contextvars
from fastapi import Request
from fastapi.responses import PlainTextResponse
from opentelemetry import baggage, metrics, trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, generate_latest
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SERVICE_NAME = os.getenv("SERVICE_NAME", "prethrift-backend")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT")
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT")
SENTRY_DSN = os.getenv("SENTRY_DSN")

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

SEARCH_OPERATIONS = Counter(
    'search_operations_total',
    'Total number of search operations',
    ['search_type', 'status']
)

EMBEDDING_OPERATIONS = Counter(
    'embedding_operations_total',
    'Total number of embedding operations',
    ['operation_type', 'status']
)


def configure_structured_logging():
    """Configure structured logging with context injection."""

    # Custom processors for adding context
    def add_request_id(_, __, event_dict):
        """Add request ID to all log entries."""
        request_id = structlog.contextvars.get_contextvars().get('request_id')
        if request_id:
            event_dict['request_id'] = request_id
        return event_dict

    def add_user_context(_, __, event_dict):
        """Add user context to log entries."""
        user_id = structlog.contextvars.get_contextvars().get('user_id')
        if user_id:
            event_dict['user_id'] = user_id
        return event_dict

    def add_trace_context(_, __, event_dict):
        """Add OpenTelemetry trace context."""
        span = trace.get_current_span()
        if span:
            span_context = span.get_span_context()
            if span_context.is_valid:
                event_dict['trace_id'] = f"{span_context.trace_id:032x}"
                event_dict['span_id'] = f"{span_context.span_id:016x}"
        return event_dict

    # Configure structlog
    if ENVIRONMENT == "production":
        # JSON formatting for production
        processors = [
            structlog.contextvars.merge_contextvars,
            add_request_id,
            add_user_context,
            add_trace_context,
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
            add_request_id,
            add_user_context,
            add_trace_context,
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


def configure_tracing():
    """Configure OpenTelemetry tracing."""

    # Set up trace provider
    trace.set_tracer_provider(TracerProvider(
        resource=trace.Resource.create({
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
            "environment": ENVIRONMENT
        })
    ))

    tracer_provider = trace.get_tracer_provider()

    # Configure exporters
    if OTLP_ENDPOINT:
        # OTLP exporter (for services like Grafana, DataDog, etc.)
        otlp_headers = None
        if os.getenv('OTLP_API_KEY'):
            otlp_headers = {"Authorization": f"Bearer {os.getenv('OTLP_API_KEY')}"}
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=OTLP_ENDPOINT,
            headers=otlp_headers
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if JAEGER_ENDPOINT:
        # Jaeger thrift exporter (more compatible with protobuf constraints)
        if '://' in JAEGER_ENDPOINT:
            agent_host = JAEGER_ENDPOINT.split('://')[1].split(':')[0]
        else:
            agent_host = JAEGER_ENDPOINT.split(':')[0]
            
        jaeger_exporter = JaegerExporter(
            agent_host_name=agent_host,
            agent_port=14268,  # Default Jaeger thrift port
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))


def configure_metrics():
    """Configure OpenTelemetry metrics."""

    if OTLP_ENDPOINT:
        # OTLP metrics exporter
        metrics_headers = None
        if os.getenv('OTLP_API_KEY'):
            metrics_headers = {"Authorization": f"Bearer {os.getenv('OTLP_API_KEY')}"}
            
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=OTLP_ENDPOINT.replace('/v1/traces', '/v1/metrics'),
                headers=metrics_headers
            ),
            export_interval_millis=10000  # Export every 10 seconds
        )

        metrics.set_meter_provider(MeterProvider(
            resource=metrics.Resource.create({
                "service.name": SERVICE_NAME,
                "service.version": SERVICE_VERSION,
                "environment": ENVIRONMENT
            }),
            metric_readers=[metric_reader]
        ))


def configure_error_tracking():
    """Configure Sentry for error tracking."""

    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=ENVIRONMENT,
            release=SERVICE_VERSION,
            traces_sample_rate=0.1 if ENVIRONMENT == "production" else 1.0,
            profiles_sample_rate=0.1 if ENVIRONMENT == "production" else 1.0,
            integrations=[
                FastApiIntegration(auto_enable=True),
                SqlalchemyIntegration(),
            ],
            before_send=lambda event, _: event if ENVIRONMENT == "production" else None
        )


def instrument_app(app):
    """Instrument FastAPI app with OpenTelemetry."""

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json"
    )

    # Instrument database connections
    SQLAlchemyInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()


async def logging_middleware(request: Request, call_next):
    """Middleware for structured logging and metrics collection."""

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

    # Add request ID to OpenTelemetry baggage
    baggage.set_baggage("request.id", request_id)

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

        # Update metrics
        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)

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

        # Update error metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=500
        ).inc()

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


def create_prometheus_metrics_endpoint():
    """Create endpoint for Prometheus metrics."""

    async def metrics_endpoint():
        """Return Prometheus metrics."""
        return PlainTextResponse(
            generate_latest(),
            media_type="text/plain"
        )

    return metrics_endpoint


def get_logger(name: str | None = None):
    """Get a structured logger instance."""
    return structlog.get_logger(name or __name__)


# Custom context managers for operation tracking
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
        SEARCH_OPERATIONS.labels(search_type=search_type, status="success").inc()
        logger.info(
            "Search operation completed",
            search_type=search_type,
            duration_ms=round(duration * 1000, 2)
        )

    except Exception as exc:
        duration = time.time() - start_time
        SEARCH_OPERATIONS.labels(search_type=search_type, status="error").inc()
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
        EMBEDDING_OPERATIONS.labels(operation_type=operation_type, status="success").inc()
        logger.info(
            "Embedding operation completed",
            operation_type=operation_type,
            duration_ms=round(duration * 1000, 2)
        )

    except Exception as exc:
        duration = time.time() - start_time
        EMBEDDING_OPERATIONS.labels(operation_type=operation_type, status="error").inc()
        logger.error(
            "Embedding operation failed",
            operation_type=operation_type,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=round(duration * 1000, 2),
            exc_info=True
        )
        raise


# Initialize observability on import
def initialize_observability():
    """Initialize all observability components."""
    configure_structured_logging()
    configure_tracing()
    configure_metrics()
    configure_error_tracking()


# Auto-initialize when module is imported
initialize_observability()
