#!/bin/bash

# PreThrift Development Environment Troubleshooting Script

set -e

echo "🔧 PreThrift Development Environment Troubleshooting"
echo "===================================================="

cd "$(dirname "$0")"

# Check Docker status
echo "🐳 Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "✅ Docker is running"

# Check if services are defined
echo ""
echo "📋 Checking Docker Compose configuration..."
if docker-compose -f docker-compose.dev.yml config > /dev/null 2>&1; then
    echo "✅ Docker Compose configuration is valid"
else
    echo "❌ Docker Compose configuration has errors"
    docker-compose -f docker-compose.dev.yml config
    exit 1
fi

# Show service status
echo ""
echo "📊 Current service status:"
docker-compose -f docker-compose.dev.yml ps

# Show recent logs for each service
echo ""
echo "📜 Recent logs from each service:"
echo ""

services=("postgres" "redis" "localstack" "jaeger" "prometheus" "grafana" "backend")

for service in "${services[@]}"; do
    echo "--- $service logs (last 10 lines) ---"
    docker-compose -f docker-compose.dev.yml logs --tail=10 "$service" 2>/dev/null || echo "Service $service not running"
    echo ""
done

# Check ports
echo "🔌 Checking port availability:"
ports=(5432 6379 8000 3000 9090 16686 4566)
port_names=("PostgreSQL" "Redis" "FastAPI" "Grafana" "Prometheus" "Jaeger" "LocalStack")

for i in "${!ports[@]}"; do
    port=${ports[$i]}
    name=${port_names[$i]}

    if lsof -i :$port > /dev/null 2>&1; then
        echo "✅ Port $port ($name) is in use"
    else
        echo "❌ Port $port ($name) is not in use"
    fi
done

# Check disk space
echo ""
echo "💾 Checking disk space:"
df -h /

# Check memory usage
echo ""
echo "🧠 Memory usage:"
free -h 2>/dev/null || vm_stat | head -10

# Suggest common fixes
echo ""
echo "🛠️  Common troubleshooting steps:"
echo ""
echo "1. If services won't start:"
echo "   docker-compose -f docker-compose.dev.yml down"
echo "   docker-compose -f docker-compose.dev.yml pull"
echo "   docker-compose -f docker-compose.dev.yml up -d"
echo ""
echo "2. If backend service fails:"
echo "   docker-compose -f docker-compose.dev.yml logs backend"
echo "   docker-compose -f docker-compose.dev.yml restart backend"
echo ""
echo "3. If database connection fails:"
echo "   docker-compose -f docker-compose.dev.yml exec postgres psql -U prethrift -d prethrift -c 'SELECT 1;'"
echo ""
echo "4. If port conflicts occur:"
echo "   Change port mappings in docker-compose.dev.yml"
echo ""
echo "5. Reset everything:"
echo "   docker-compose -f docker-compose.dev.yml down -v"
echo "   docker system prune -f"
echo "   ./start-dev.sh"
echo ""
echo "6. Check logs for specific service:"
echo "   docker-compose -f docker-compose.dev.yml logs -f [service-name]"
echo ""
echo "📞 If issues persist, check:"
echo "   • Docker Desktop has enough memory allocated (4GB+ recommended)"
echo "   • No firewall blocking the ports"
echo "   • docs/DEVELOPMENT.md for detailed setup instructions"
