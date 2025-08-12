# PreThrift Local Development Environment

This Docker Compose setup provides a complete local development environment that simulates AWS services for the PreThrift application.

## Services Included

### Core Application Services
- **PostgreSQL 15**: Main database with pgvector extension for AI embeddings
- **Redis**: Caching layer for embeddings and search results
- **FastAPI Backend**: PreThrift API service with observability

### AWS Service Simulation
- **LocalStack**: Simulates AWS services (S3, CloudWatch, X-Ray) locally

### Observability Stack
- **Jaeger**: Distributed tracing collection and visualization
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Metrics visualization and dashboards

## Quick Start

1. **Start all services:**
   ```bash
   cd backend
   docker-compose -f docker-compose.dev.yml up -d
   ```

2. **View logs:**
   ```bash
   # All services
   docker-compose -f docker-compose.dev.yml logs -f

   # Specific service
   docker-compose -f docker-compose.dev.yml logs -f backend
   ```

3. **Stop services:**
   ```bash
   docker-compose -f docker-compose.dev.yml down
   ```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| FastAPI Backend | http://localhost:8000 | Main API service |
| API Docs | http://localhost:8000/docs | Interactive API documentation |
| Health Check | http://localhost:8000/health | Application health status |
| PostgreSQL | localhost:5432 | Database (user: prethrift, db: prethrift) |
| Redis | localhost:6379 | Caching layer |
| Jaeger UI | http://localhost:16686 | Distributed tracing dashboard |
| Prometheus | http://localhost:9090 | Metrics collection interface |
| Grafana | http://localhost:3000 | Metrics visualization (admin/admin) |
| LocalStack | http://localhost:4566 | AWS services simulation |

## Environment Configuration

The setup uses environment variables defined in `docker-compose.dev.yml`. Key configurations:

### Database
- Host: `postgres`
- Port: `5432`
- Database: `prethrift`
- User: `prethrift`
- Password: `prethrift_dev`

### Redis
- Host: `redis`
- Port: `6379`
- No authentication in dev mode

### LocalStack (AWS Simulation)
- S3 endpoint: `http://localstack:4566`
- Bucket: `prethrift-dev`
- Region: `us-east-1`

### Observability
- Jaeger endpoint: `http://jaeger:14268/api/traces`
- Prometheus endpoint: `http://prometheus:9090`
- Log level: `DEBUG`

## Development Workflow

### Making Code Changes
The backend service uses volume mounting, so code changes are automatically reflected:

1. Edit files in `backend/app/`
2. The FastAPI server will auto-reload
3. Check logs: `docker-compose -f docker-compose.dev.yml logs -f backend`

### Database Operations
Connect to PostgreSQL for debugging:
```bash
docker-compose -f docker-compose.dev.yml exec postgres psql -U prethrift -d prethrift
```

### Redis Operations
Connect to Redis for cache inspection:
```bash
docker-compose -f docker-compose.dev.yml exec redis redis-cli
```

### Testing Observability

1. **Generate some traffic:**
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/docs
   ```

2. **View traces in Jaeger:**
   - Open http://localhost:16686
   - Select "prethrift-api" service
   - Click "Find Traces"

3. **View metrics in Prometheus:**
   - Open http://localhost:9090
   - Try queries like `http_requests_total` or `process_resident_memory_bytes`

4. **View dashboards in Grafana:**
   - Open http://localhost:3000 (admin/admin)
   - Import or create dashboards for FastAPI metrics

### AWS Service Testing

Test S3 operations with LocalStack:
```bash
# Create bucket (if not auto-created)
aws --endpoint-url=http://localhost:4566 s3 mb s3://prethrift-dev

# List buckets
aws --endpoint-url=http://localhost:4566 s3 ls

# Upload a test file
echo "test content" | aws --endpoint-url=http://localhost:4566 s3 cp - s3://prethrift-dev/test.txt

# List objects
aws --endpoint-url=http://localhost:4566 s3 ls s3://prethrift-dev/
```

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   - Ensure ports 5432, 6379, 8000, 3000, 9090, 16686, 4566 are available
   - Modify port mappings in docker-compose.dev.yml if needed

2. **Database connection errors:**
   - Wait for PostgreSQL to fully start (check logs)
   - Verify pgvector extension is loaded

3. **LocalStack not responding:**
   - Check LocalStack logs: `docker-compose -f docker-compose.dev.yml logs localstack`
   - Ensure AWS CLI is configured with dummy credentials

4. **Memory issues:**
   - The full stack requires ~4GB RAM
   - Reduce services if needed by commenting them out

### Logs and Debugging

View comprehensive logs:
```bash
# All services with timestamps
docker-compose -f docker-compose.dev.yml logs -f -t

# Filter by service
docker-compose -f docker-compose.dev.yml logs -f backend | grep ERROR

# Follow specific container
docker logs -f prethrift_backend_dev
```

### Health Checks

Monitor service health:
```bash
# Check all container status
docker-compose -f docker-compose.dev.yml ps

# Test backend health endpoint
curl -s http://localhost:8000/health | jq .

# Test database connectivity
curl -s http://localhost:8000/health/ready | jq .
```

## Production Differences

This development environment differs from production in:

- **Security**: No authentication, open ports, default credentials
- **Performance**: Not optimized for high throughput
- **Persistence**: Data is ephemeral unless volumes are configured
- **Networking**: Services communicate via Docker network names
- **AWS Services**: LocalStack simulates AWS instead of real services

When deploying to production, refer to `ARCHITECTURE_STRATEGY.md` for the recommended AWS Fargate setup.

## Extending the Environment

### Adding New Services

1. Add service definition to `docker-compose.dev.yml`
2. Configure networking and environment variables
3. Update this README with new service details

### Custom Dashboards

1. Access Grafana at http://localhost:3000
2. Create dashboards for your metrics
3. Export dashboard JSON and commit to version control

### Environment Variables

Add new environment variables to the backend service in `docker-compose.dev.yml`:
```yaml
environment:
  - NEW_SETTING=value
```

## Cleanup

Remove all containers and volumes:
```bash
docker-compose -f docker-compose.dev.yml down -v --remove-orphans
docker system prune -f
```
