"""Simple health check endpoints."""

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


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
    message: str = ""


class HealthResponse(BaseModel):
    """Health check response model."""

    status: HealthStatus
    timestamp: datetime
    version: str
    environment: str
    uptime_seconds: float
    checks: list

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# Track startup time for uptime calculation
startup_time = time.time()


async def check_basic_health() -> HealthCheck:
    """Basic health check."""
    start_time = time.time()

    try:
        # Simple health check
        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="basic",
            status=HealthStatus.HEALTHY,
            duration_ms=round(duration_ms, 2),
            message="Application is running",
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return HealthCheck(
            name="basic",
            status=HealthStatus.UNHEALTHY,
            duration_ms=round(duration_ms, 2),
            message=f"Error: {str(e)}",
        )


# Create router for health endpoints
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""

    start_time = time.time()

    # Run basic health check
    check = await check_basic_health()

    # Calculate overall status
    overall_status = check.status

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
            }
        ],
    )

    # Return appropriate HTTP status
    if overall_status == HealthStatus.UNHEALTHY:
        raise HTTPException(status_code=503, detail=response.dict())

    return response


@router.get("/ready")
async def readiness_check():
    """Simple readiness check."""
    return {"ready": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/live")
async def liveness_check():
    """Simple liveness check."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - startup_time, 2),
    }
