# Backend Observability & Monitoring

## Overview

The Prethrift backend now includes comprehensive observability features including structured logging, distributed tracing, metrics collection, health checks, and error tracking.

## Features Implemented

### 🏗️ Infrastructure Components

#### 1. Structured Logging (`observability.py`)
- **Library**: `structlog`
- **Format**: JSON in production, colorized console in development
- **Context**: Automatic request ID, user ID, trace context injection
- **Features**:
  - Request/response logging with timing
  - Error tracking with stack traces
  - Context preservation across async calls
  - Custom log processors for enrichment

#### 2. Distributed Tracing (`observability.py`)
- **Standard**: OpenTelemetry
- **Exporters**: OTLP (Grafana, DataDog), Jaeger
- **Auto-instrumentation**: FastAPI, SQLAlchemy, PostgreSQL, boto3
- **Features**:
  - Automatic span creation for HTTP requests
  - Database query tracing
  - Custom spans for business operations
  - Trace correlation with logs

#### 3. Metrics Collection (`observability.py`)
- **Prometheus** metrics exported at `/metrics`
- **OpenTelemetry** metrics via OTLP
- **Custom Metrics**:
  - HTTP request count/duration by endpoint
  - Search operation metrics by type
  - Embedding operation metrics
  - Database connection pool metrics

#### 4. Health Checks (`health.py`)
- **Endpoints**:
  - `/health` - Comprehensive health check
  - `/health/ready` - Readiness for load balancers
  - `/health/live` - Simple liveness check
- **Checks**:
  - Database connectivity
  - pgvector extension
  - Embedding model availability
  - AWS S3 connectivity
  - Memory usage monitoring

#### 5. Error Tracking (`observability.py`)
- **Library**: Sentry
- **Features**:
  - Automatic error capture
  - Performance monitoring
  - Release tracking
  - Environment-specific configuration

### 📊 Configuration System (`config.py`)

Environment-based configuration with validation:

```python
# Application settings
SERVICE_NAME=prethrift-backend
SERVICE_VERSION=1.0.0
ENVIRONMENT=development|staging|production
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@host:port/db
DB_POOL_SIZE=10

# Observability
LOG_LEVEL=INFO
OTLP_ENDPOINT=https://api.honeycomb.io/v1/traces
OTLP_API_KEY=your-api-key
JAEGER_ENDPOINT=http://localhost:14268
SENTRY_DSN=https://your-sentry-dsn
TRACE_SAMPLE_RATE=0.1

# AWS
AWS_REGION=us-east-1
IMAGES_BUCKET=your-s3-bucket
```

## Usage Examples

### 🔍 Structured Logging

```python
from app.observability import get_logger, track_search_operation

logger = get_logger(__name__)

# Basic logging
logger.info("User search started", user_id="123", query="blue dress")

# Context tracking for operations
async with track_search_operation("text_search"):
    results = await perform_text_search(query)
    logger.info("Search completed", result_count=len(results))
```

### 📈 Custom Metrics

```python
from app.observability import SEARCH_OPERATIONS, EMBEDDING_OPERATIONS

# Increment counters
SEARCH_OPERATIONS.labels(search_type="visual", status="success").inc()
EMBEDDING_OPERATIONS.labels(operation_type="clip", status="success").inc()
```

### 🎯 Custom Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("user.id", user_id)
    span.set_attribute("operation.type", "embedding")
    # Your code here
```

### 🏥 Health Check Integration

```python
# Custom health checks can be added to health.py

async def check_external_service() -> HealthCheck:
    """Check external service connectivity."""
    start_time = time.time()

    try:
        # Test external service
        await external_service.ping()

        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="external_service",
            status=HealthStatus.HEALTHY,
            duration_ms=round(duration_ms, 2),
            message="External service is responsive"
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="external_service",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"External service error: {str(e)}"
        )
```

## Monitoring Endpoints

### Health Check Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/health` | Comprehensive health | Monitoring dashboards |
| `/health/ready` | Readiness check | Load balancer health checks |
| `/health/live` | Liveness check | Kubernetes liveness probes |
| `/metrics` | Prometheus metrics | Metrics collection |

### Example Health Response

```json
{
  "status": "healthy",
  "timestamp": "2025-08-10T19:00:00Z",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "checks": [
    {
      "name": "database",
      "status": "healthy",
      "duration_ms": 5.2,
      "message": "Database connection successful"
    },
    {
      "name": "pgvector",
      "status": "healthy",
      "duration_ms": 2.1,
      "message": "pgvector extension is available and functional"
    },
    {
      "name": "embedding_model",
      "status": "healthy",
      "duration_ms": 150.3,
      "message": "Embedding model functional, vector size: 512",
      "details": {"embedding_dimension": 512}
    }
  ]
}
```

## Prometheus Metrics

### Available Metrics

```prometheus
# HTTP Requests
http_requests_total{method="GET", endpoint="/api/search", status_code="200"} 1250
http_request_duration_seconds{method="GET", endpoint="/api/search"} 0.125

# Search Operations
search_operations_total{search_type="text", status="success"} 845
search_operations_total{search_type="visual", status="success"} 203

# Embedding Operations
embedding_operations_total{operation_type="clip", status="success"} 1048
embedding_operations_total{operation_type="text", status="success"} 2341
```

## Environment Setup

### Development Environment

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export DEBUG=true

# Optional: Set up local tracing
export JAEGER_ENDPOINT=http://localhost:14268

# Run with observability
uvicorn app.main:app --reload
```

### Production Environment

```bash
# Required environment variables
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export SENTRY_DSN=your-sentry-dsn
export OTLP_ENDPOINT=your-otlp-endpoint
export OTLP_API_KEY=your-api-key

# Optional performance tuning
export TRACE_SAMPLE_RATE=0.1
export DB_POOL_SIZE=20
```

## Integration Examples

### Grafana Dashboard Query Examples

```promql
# Request rate by endpoint
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Search success rate
rate(search_operations_total{status="success"}[5m]) / rate(search_operations_total[5m])
```

### DataDog Integration

```yaml
# datadog.yaml
logs:
  - type: file
    path: /app/logs/*.json
    service: prethrift-backend
    source: python

apm:
  enabled: true
  env: production
  service: prethrift-backend
```

### Kubernetes Health Checks

```yaml
# deployment.yaml
spec:
  containers:
  - name: prethrift-backend
    livenessProbe:
      httpGet:
        path: /health/live
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10
    readinessProbe:
      httpGet:
        path: /health/ready
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
```

## Alerting Rules

### Recommended Alerts

```yaml
# prometheus-alerts.yaml
groups:
- name: prethrift-backend
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"

  - alert: DatabaseDown
    expr: up{job="prethrift-health"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database health check failing"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time detected"
```

## Troubleshooting

### Common Issues

1. **Missing traces**: Check OTLP_ENDPOINT and OTLP_API_KEY
2. **High memory usage**: Adjust TRACE_SAMPLE_RATE
3. **Database health failures**: Verify DATABASE_URL and pgvector installation
4. **Missing metrics**: Check `/metrics` endpoint accessibility

### Debug Commands

```bash
# Check health status
curl http://localhost:8000/health

# View metrics
curl http://localhost:8000/metrics

# Test tracing (requires jaeger)
curl -H "X-Trace-Id: test-trace-123" http://localhost:8000/api/search?q=test

# View structured logs
tail -f logs/app.log | jq .
```

## Performance Impact

- **Overhead**: ~1-3ms per request
- **Memory**: ~50MB additional for tracing
- **Storage**: JSON logs are ~2x larger than plain text
- **Network**: OTLP exports use ~1KB per trace

The observability features provide comprehensive monitoring capabilities while maintaining minimal performance impact on the core application.
