"""Health check endpoints and monitoring utilities."""

import asyncio
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from .core import get_client
from .observability import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheck:
    """Individual health check result."""

    name: str
    status: HealthStatus
    duration_ms: float
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: List[Dict[str, Any]]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool
    timestamp: datetime
    critical_checks: List[Dict[str, Any]]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Track startup time for uptime calculation
startup_time = time.time()


async def check_database() -> HealthCheck:
    """Check database connectivity and basic operations."""
    start_time = time.time()

    try:
        # Get database session
        db = next(get_client())

        # Test basic query
        result = db.execute(sa.text("SELECT 1 as test")).fetchone()

        if result and result.test == 1:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.HEALTHY,
                duration_ms=round(duration_ms, 2),
                message="Database connection successful",
            )
        else:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="database",
                status=HealthStatus.UNHEALTHY,
                duration_ms=round(duration_ms, 2),
                message="Database query returned unexpected result",
            )

    except SQLAlchemyError as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("Database health check failed", error=str(e), exc_info=True)
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Database error: {str(e)}",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Database health check failed with unexpected error", error=str(e), exc_info=True
        )
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Unexpected error: {str(e)}",
        )


async def check_pgvector() -> HealthCheck:
    """Check pgvector extension availability."""
    start_time = time.time()

    try:
        db = next(get_client())

        # Check if pgvector extension is available
        result = db.execute(
            sa.text("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            ) as has_vector
        """)
        ).fetchone()

        if result and result.has_vector:
            # Test vector operations
            db.execute(
                sa.text("SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector as distance")
            ).fetchone()

            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="pgvector",
                status=HealthStatus.HEALTHY,
                duration_ms=round(duration_ms, 2),
                message="pgvector extension is available and functional",
            )
        else:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="pgvector",
                status=HealthStatus.UNHEALTHY,
                duration_ms=round(duration_ms, 2),
                message="pgvector extension not installed",
            )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("pgvector health check failed", error=str(e), exc_info=True)
        return HealthCheck(
            name="pgvector",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"pgvector check failed: {str(e)}",
        )


async def check_embedding_model() -> HealthCheck:
    """Check if embedding model is available and functional."""
    start_time = time.time()

    try:
        # Import here to avoid circular imports
        from .describe_images import embed_text

        # Test embedding generation
        test_embedding = embed_text("test health check")

        if test_embedding and len(test_embedding) > 0:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="embedding_model",
                status=HealthStatus.HEALTHY,
                duration_ms=round(duration_ms, 2),
                message=f"Embedding model functional, vector size: {len(test_embedding)}",
                details={"embedding_dimension": len(test_embedding)},
            )
        else:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="embedding_model",
                status=HealthStatus.UNHEALTHY,
                duration_ms=round(duration_ms, 2),
                message="Embedding model returned empty result",
            )

    except ImportError as e:
        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="embedding_model",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Embedding model import failed: {str(e)}",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("Embedding model health check failed", error=str(e), exc_info=True)
        return HealthCheck(
            name="embedding_model",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Embedding model error: {str(e)}",
        )


async def check_aws_s3() -> HealthCheck:
    """Check AWS S3 connectivity if configured."""
    start_time = time.time()

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        bucket_name = os.getenv("IMAGES_BUCKET")
        if not bucket_name:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                name="aws_s3",
                status=HealthStatus.DEGRADED,
                duration_ms=round(duration_ms, 2),
                message="S3 bucket not configured (IMAGES_BUCKET not set)",
            )

        # Test S3 connection
        s3_client = boto3.client("s3")
        s3_client.head_bucket(Bucket=bucket_name)

        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="aws_s3",
            status=HealthStatus.HEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"S3 bucket '{bucket_name}' is accessible",
            details={"bucket_name": bucket_name},
        )

    except (BotoCoreError, ClientError) as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("S3 health check failed", error=str(e), exc_info=True)
        return HealthCheck(
            name="aws_s3",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"S3 error: {str(e)}",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("S3 health check failed with unexpected error", error=str(e), exc_info=True)
        return HealthCheck(
            name="aws_s3",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Unexpected S3 error: {str(e)}",
        )


async def check_memory_usage() -> HealthCheck:
    """Check memory usage."""
    start_time = time.time()

    try:
        import psutil

        memory = psutil.virtual_memory()
        memory_usage_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)

        # Consider memory healthy if under 85% usage
        if memory_usage_percent < 85:
            status = HealthStatus.HEALTHY
            message = f"Memory usage is normal ({memory_usage_percent:.1f}%)"
        elif memory_usage_percent < 95:
            status = HealthStatus.DEGRADED
            message = f"Memory usage is high ({memory_usage_percent:.1f}%)"
        else:
            status = HealthStatus.UNHEALTHY
            message = f"Memory usage is critical ({memory_usage_percent:.1f}%)"

        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="memory",
            status=status,
            duration_ms=round(duration_ms, 2),
            message=message,
            details={
                "usage_percent": round(memory_usage_percent, 1),
                "available_gb": round(memory_available_gb, 2),
                "total_gb": round(memory.total / (1024**3), 2),
            },
        )

    except ImportError:
        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="memory",
            status=HealthStatus.DEGRADED,
            duration_ms=round(duration_ms, 2),
            message="psutil not available for memory monitoring",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error("Memory health check failed", error=str(e), exc_info=True)
        return HealthCheck(
            name="memory",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Memory check error: {str(e)}",
        )


async def run_all_health_checks() -> List[HealthCheck]:
    """Run all health checks concurrently."""

    # Define all health checks
    health_checks = [
        check_database(),
        check_pgvector(),
        check_embedding_model(),
        check_aws_s3(),
        check_memory_usage(),
    ]

    # Run checks concurrently with timeout
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*health_checks, return_exceptions=True),
            timeout=30.0,  # 30 second timeout for all checks
        )

        # Handle any exceptions from gather
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Health check {i} failed with exception", error=str(result), exc_info=True
                )
                final_results.append(
                    HealthCheck(
                        name=f"check_{i}",
                        status=HealthStatus.UNHEALTHY,
                        duration_ms=0.0,
                        message=f"Health check failed: {str(result)}",
                    )
                )
            else:
                final_results.append(result)

        return final_results

    except asyncio.TimeoutError:
        logger.error("Health checks timed out")
        return [
            HealthCheck(
                name="timeout",
                status=HealthStatus.UNHEALTHY,
                duration_ms=30000.0,
                message="Health checks timed out after 30 seconds",
            )
        ]


def calculate_overall_status(checks: List[HealthCheck]) -> HealthStatus:
    """Calculate overall health status from individual checks."""

    if not checks:
        return HealthStatus.UNHEALTHY

    # Count status types
    healthy_count = sum(1 for check in checks if check.status == HealthStatus.HEALTHY)
    degraded_count = sum(1 for check in checks if check.status == HealthStatus.DEGRADED)
    unhealthy_count = sum(1 for check in checks if check.status == HealthStatus.UNHEALTHY)

    # Determine overall status
    if unhealthy_count > 0:
        # Any unhealthy check makes the system unhealthy
        return HealthStatus.UNHEALTHY
    elif degraded_count > 0:
        # Any degraded check makes the system degraded
        return HealthStatus.DEGRADED
    else:
        # All checks healthy
        return HealthStatus.HEALTHY


# Create router for health endpoints
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns detailed information about system health including:
    - Database connectivity
    - pgvector availability
    - Embedding model functionality
    - AWS S3 connectivity
    - Memory usage
    """

    logger.info("Running health checks")
    start_time = time.time()

    # Run all health checks
    checks = await run_all_health_checks()

    # Calculate overall status
    overall_status = calculate_overall_status(checks)

    # Calculate uptime
    uptime_seconds = time.time() - startup_time

    # Prepare response
    response = HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=os.getenv("SERVICE_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        uptime_seconds=round(uptime_seconds, 2),
        checks=[
            {
                "name": check.name,
                "status": check.status.value,
                "duration_ms": check.duration_ms,
                "message": check.message,
                "details": check.details,
            }
            for check in checks
        ],
    )

    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "Health check completed",
        overall_status=overall_status.value,
        total_duration_ms=round(duration_ms, 2),
        check_count=len(checks),
    )

    # Return appropriate HTTP status
    if overall_status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=response.dict())

    return response


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness check endpoint for load balancers and orchestrators.

    Returns ready=true only if critical systems are functional:
    - Database connectivity
    - pgvector availability
    """

    logger.info("Running readiness checks")
    start_time = time.time()

    # Run only critical checks for readiness
    critical_checks = await asyncio.gather(
        check_database(), check_pgvector(), return_exceptions=True
    )

    # Process results
    checks_data = []
    ready = True

    for i, result in enumerate(critical_checks):
        if isinstance(result, Exception):
            logger.error(f"Critical check {i} failed", error=str(result), exc_info=True)
            checks_data.append(
                {
                    "name": f"critical_check_{i}",
                    "status": HealthStatus.UNHEALTHY.value,
                    "message": f"Check failed: {str(result)}",
                }
            )
            ready = False
        else:
            checks_data.append(
                {
                    "name": result.name,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                    "message": result.message,
                }
            )
            if result.status != HealthStatus.HEALTHY:
                ready = False

    response = ReadinessResponse(
        ready=ready, timestamp=datetime.now(timezone.utc), critical_checks=checks_data
    )

    duration_ms = (time.time() - start_time) * 1000
    logger.info("Readiness check completed", ready=ready, duration_ms=round(duration_ms, 2))

    # Return appropriate HTTP status
    if not ready:
        raise HTTPException(status_code=503, detail=response.dict())

    return response


@router.get("/live")
async def liveness_check():
    """
    Simple liveness check endpoint.

    Returns 200 OK if the application is running.
    Used by orchestrators to determine if the application should be restarted.
    """

    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - startup_time, 2),
    }
