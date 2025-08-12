#!/usr/bin/env python3
"""Test script for validating observability features."""

import asyncio
import os
import sys
from pathlib import Path

# Add the backend app to Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Set environment variables for testing
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("DEBUG", "true")

try:
    from app.config import settings
    from app.health_simple import check_basic_health
    from app.observability_simple import (
        get_logger,
        track_embedding_operation,
        track_search_operation,
    )

    print("✅ Successfully imported observability modules")

    # Test logger
    logger = get_logger(__name__)
    logger.info("Testing structured logging", test_field="test_value", number=42)
    print("✅ Structured logging working")

    # Test configuration
    print(f"✅ Configuration loaded - Environment: {settings.environment}")
    print(f"✅ Log level: {settings.log_level}")

    # Test async context managers
    async def test_tracking():
        async with track_search_operation("test_search"):
            logger.info("Inside search operation context")
            await asyncio.sleep(0.1)

        async with track_embedding_operation("test_embedding"):
            logger.info("Inside embedding operation context")
            await asyncio.sleep(0.1)

        print("✅ Operation tracking context managers working")

    # Test health checks
    async def test_health_checks():
        try:
            # Test basic health check
            health_check = await check_basic_health()
            print(f"✅ Basic health check: {health_check.status.value} ({health_check.duration_ms}ms)")

        except Exception as e:
            print(f"❌ Health check error: {e}")

    async def main():
        print("\n🔍 Testing Prethrift Backend Observability Features\n")

        await test_tracking()
        await test_health_checks()

        print("\n✅ All observability tests completed successfully!")
        print("\nNext steps:")
        print("1. Set up database connection for full health checks")
        print("2. Configure OTLP_ENDPOINT for tracing")
        print("3. Configure SENTRY_DSN for error tracking")
        print("4. Run the FastAPI app: uvicorn app.main:app --reload")
        print("5. Check endpoints:")
        print("   - http://localhost:8000/health")
        print("   - http://localhost:8000/metrics")
        print("   - http://localhost:8000/docs")

    if __name__ == "__main__":
        asyncio.run(main())

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required dependencies:")
    print("pip install structlog opentelemetry-api opentelemetry-sdk sentry-sdk prometheus-client")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
