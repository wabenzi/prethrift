#!/bin/bash

# PreThrift Development Environment Setup Script

set -e

echo "🚀 PreThrift Development Environment Setup"
echo "=========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running."
    echo "📝 Please start Docker Desktop and try again."
    echo ""
    echo "On macOS:"
    echo "  1. Open Docker Desktop application"
    echo "  2. Wait for Docker to start (Docker icon in menu bar should be stable)"
    echo "  3. Run this script again"
    exit 1
fi

echo "✅ Docker is running"

# Navigate to backend directory
cd "$(dirname "$0")"

# Pull required images first to show progress
echo "📦 Pulling Docker images..."
docker-compose -f docker-compose.dev.yml pull

# Start services
echo "🚀 Starting development environment..."
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service status
echo "🔍 Checking service status..."
docker-compose -f docker-compose.dev.yml ps

# Wait for backend to be ready
echo "⏳ Waiting for backend service to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend service is ready!"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Backend service failed to start within 60 seconds"
        echo "📋 Check logs with: docker-compose -f docker-compose.dev.yml logs backend"
        exit 1
    fi
    echo "   Attempt $i/60... waiting 1 second"
    sleep 1
done

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s http://localhost:8000/health | jq . || echo "Health check returned non-JSON response"

# Create S3 bucket in LocalStack
echo "🪣 Setting up S3 bucket in LocalStack..."
sleep 5
aws --endpoint-url=http://localhost:4566 s3 mb s3://prethrift-dev 2>/dev/null || echo "Bucket already exists or LocalStack not ready"

echo ""
echo "🎉 Development environment is ready!"
echo ""
echo "📊 Service URLs:"
echo "  • FastAPI Backend:     http://localhost:8000"
echo "  • API Documentation:   http://localhost:8000/docs"
echo "  • Health Check:        http://localhost:8000/health"
echo "  • Jaeger Tracing:      http://localhost:16686"
echo "  • Prometheus Metrics:  http://localhost:9090"
echo "  • Grafana Dashboards:  http://localhost:3000 (admin/admin)"
echo "  • LocalStack:          http://localhost:4566"
echo ""
echo "🔧 Useful commands:"
echo "  • View logs:           docker-compose -f docker-compose.dev.yml logs -f"
echo "  • Stop environment:    docker-compose -f docker-compose.dev.yml down"
echo "  • Restart backend:     docker-compose -f docker-compose.dev.yml restart backend"
echo "  • Connect to DB:       docker-compose -f docker-compose.dev.yml exec postgres psql -U prethrift -d prethrift"
echo "  • Connect to Redis:    docker-compose -f docker-compose.dev.yml exec redis redis-cli"
echo ""
echo "📚 See docs/DEVELOPMENT.md for detailed usage instructions"
