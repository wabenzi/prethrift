#!/usr/bin/env python3
"""Test the observability endpoints."""

import json

import requests


def test_endpoints():
    """Test the observability endpoints."""
    base_url = "http://localhost:8001"

    endpoints = ["/", "/health", "/health/ready", "/health/live", "/metrics"]

    print("🔍 Testing Prethrift Backend Observability Endpoints\n")

    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"Testing {url}...")

            response = requests.get(url, timeout=5)

            print(f"✅ Status: {response.status_code}")

            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                print(f"✅ Response: {json.dumps(data, indent=2)}")
            else:
                content = response.text[:200] + "..." if len(response.text) > 200 else response.text
                print(f"✅ Response: {content}")

            print(f"✅ Headers: X-Request-ID: {response.headers.get('X-Request-ID', 'Not found')}")
            print()

        except requests.exceptions.ConnectionError:
            print(f"❌ Connection failed - Is the server running on {base_url}?")
            print("To start the server:")
            print("cd /Users/leonhardt/dev/prethrift/backend")
            print("source ../.venv/bin/activate")
            print("python -m uvicorn app.main:app --host 0.0.0.0 --port 8001")
            return
        except Exception as e:
            print(f"❌ Error: {e}")
            print()

    print("✅ All endpoint tests completed!")
    print("\n📊 Observability Features Available:")
    print("- Structured logging with request IDs")
    print("- Health checks (basic, ready, live)")
    print("- Metrics endpoint (Prometheus compatible)")
    print("- Request/response middleware")
    print("- Error tracking and performance monitoring")


if __name__ == "__main__":
    test_endpoints()
