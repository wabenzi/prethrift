#!/usr/bin/env python3
"""
Test script to validate the PreThrift development environment and observability features.
Run this after starting the development environment with start-dev.sh
"""

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict

# Service URLs (using mapped ports from docker-compose.dev.yml)
BACKEND_URL = "http://localhost:8000"
JAEGER_URL = "http://localhost:16687"  # Updated to mapped port
PROMETHEUS_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"
LOCALSTACK_URL = "http://localhost:4567"  # Updated to mapped port

def test_endpoint(url: str, description: str) -> Dict[str, Any]:
    """Test a single endpoint and return results"""
    try:
        start_time = time.time()
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'PreThrift-Test-Suite/1.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            duration = time.time() - start_time
            content = response.read().decode('utf-8')

            return {
                "url": url,
                "description": description,
                "status": response.status,
                "duration": f"{duration:.3f}s",
                "success": response.status == 200,
                "content_length": len(content),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            }
    except urllib.error.HTTPError as e:
        return {
            "url": url,
            "description": description,
            "status": e.code,
            "duration": "N/A",
            "success": False,
            "error": f"HTTP {e.code}: {e.reason}"
        }
    except Exception as e:
        return {
            "url": url,
            "description": description,
            "status": "ERROR",
            "duration": "N/A",
            "success": False,
            "error": str(e)
        }

def main():
    """Main test function"""
    print("🧪 PreThrift Development Environment Test Suite")
    print("=" * 55)

    # Test endpoints
    test_cases = [
        (f"{BACKEND_URL}/health", "Backend Health Check"),
        (f"{BACKEND_URL}/health/ready", "Backend Readiness Check"),
        (f"{BACKEND_URL}/health/live", "Backend Liveness Check"),
        (f"{BACKEND_URL}/docs", "API Documentation"),
        (f"{BACKEND_URL}/metrics", "Prometheus Metrics"),
        (f"{JAEGER_URL}/api/services", "Jaeger Services API"),
        (f"{PROMETHEUS_URL}/api/v1/label/__name__/values", "Prometheus Metrics API"),
        (f"{GRAFANA_URL}/api/health", "Grafana Health"),
        (f"{LOCALSTACK_URL}/_localstack/health", "LocalStack Health"),
    ]

    results = []

    print("🔍 Testing service endpoints...")
    print()

    for url, description in test_cases:
        result = test_endpoint(url, description)
        results.append(result)

        # Print immediate feedback
        status_icon = "✅" if result["success"] else "❌"
        print(f"{status_icon} {description:25} {result['status']:>6} ({result['duration']:>7})")

        if not result["success"] and "error" in result:
            print(f"   Error: {result['error']}")

    print()
    print("📊 Test Summary:")
    print("-" * 40)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    print(f"Successful: {successful}/{total}")
    print(f"Failed:     {total - successful}/{total}")

    if successful == total:
        print("\n🎉 All services are running correctly!")
        print("\n📋 Next Steps:")
        print("  1. Open http://localhost:8000/docs for API documentation")
        print("  2. Generate some API traffic to see traces in Jaeger")
        print("  3. View metrics in Prometheus: http://localhost:9090")
        print("  4. Create dashboards in Grafana: http://localhost:3000")
        print("\n🔍 Generate sample traces:")
        print("  curl http://localhost:8000/health")
        print("  curl http://localhost:8000/health/ready")
        print("  curl http://localhost:8000/docs")
    else:
        print(f"\n⚠️  {total - successful} services are not responding correctly.")
        print("   Check the logs with: docker-compose -f docker-compose.dev.yml logs")

        # Show failed services
        failed_services = [r for r in results if not r["success"]]
        if failed_services:
            print("\n❌ Failed Services:")
            for service in failed_services:
                error_msg = service.get('error', f"HTTP {service['status']}")
                print(f"   • {service['description']}: {error_msg}")

    # Test observability features specifically
    print("\n🔬 Testing Observability Features...")
    test_observability_features()

    return successful == total

def test_observability_features():
    """Test specific observability features"""
    print()

    # Generate some traced requests
    print("📡 Generating traced requests...")
    trace_endpoints = [
        f"{BACKEND_URL}/health",
        f"{BACKEND_URL}/health/ready",
        f"{BACKEND_URL}/health/live",
    ]

    for endpoint in trace_endpoints:
        test_endpoint(endpoint, "Trace generation")
        time.sleep(0.5)  # Small delay between requests

    print("   Generated requests for tracing")

    # Wait a moment for traces to be collected
    time.sleep(2)

    # Check if traces are available in Jaeger
    try:
        jaeger_result = test_endpoint(
            f"{JAEGER_URL}/api/traces?service=prethrift-api&limit=10",
            "Jaeger Traces"
        )

        if jaeger_result["success"]:
            try:
                traces_data = json.loads(jaeger_result["content_preview"].replace("...", ""))
                if "data" in traces_data:
                    trace_count = len(traces_data["data"])
                    print(f"✅ Found {trace_count} traces in Jaeger")
                else:
                    print("⚠️  No traces found yet (may need more time)")
            except Exception:
                print("✅ Jaeger API responded (trace data format not parsed)")
        else:
            print("❌ Could not retrieve traces from Jaeger")
    except Exception as e:
        print(f"❌ Error checking Jaeger traces: {e}")

    # Check Prometheus metrics
    try:
        metrics_result = test_endpoint(
            f"{PROMETHEUS_URL}/api/v1/query?query=http_requests_total",
            "Prometheus HTTP Metrics"
        )

        if metrics_result["success"]:
            print("✅ Prometheus metrics are being collected")
        else:
            print("⚠️  Prometheus metrics not yet available")
    except Exception as e:
        print(f"❌ Error checking Prometheus metrics: {e}")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)
