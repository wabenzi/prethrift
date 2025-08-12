# Database Architecture Documentation

## Overview

PreThrift uses **PostgreSQL exclusively** for all database operations, standardized across all environments to ensure consistency and reduce complexity.

## Database Architecture

### PostgreSQL Configuration

- **Development Environment**: Docker Compose with PostgreSQL 15 + pgvector
- **Test Environment**: Separate test database on same instance for integration tests
- **Unit Tests**: Mock database interactions (no actual database connections)
- **Production**: PostgreSQL with connection pooling and read replicas

### Connection Details

| Environment | Database | Host | Port | User | Password |
|-------------|----------|------|------|------|----------|
| Development | `prethrift` | localhost | 5433 | prethrift | prethrift_dev |
| Integration Tests | `prethrift_test` | localhost | 5433 | prethrift | prethrift_dev |
| Production | `prethrift_prod` | (configured) | 5432 | (configured) | (configured) |

**Note**: Development uses port 5433 to avoid conflicts with local PostgreSQL installations.

## Database Setup

### Development Environment

1. **Start PostgreSQL with Docker Compose:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d postgres
   ```

2. **Verify connection:**
   ```bash
   docker exec -it prethrift-postgres psql -U prethrift -d prethrift
   ```

3. **Database initialization:**
   - Tables are created automatically via SQLAlchemy migrations
   - pgvector extension is enabled for vector similarity search
   - Sample data can be loaded using `backend/demo/setup_demo_data.py`

### Integration Testing

1. **Create test database:**
   ```bash
   cd backend
   python tests/db_setup.py --create
   ```

2. **Run integration tests:**
   ```bash
   python -m pytest tests/ -k "not unit"
   ```

3. **Cleanup test database:**
   ```bash
   python tests/db_setup.py --cleanup
   ```

### Unit Testing

Unit tests use mocked database interactions and do not require a real database connection. Use `pytest-mock` to mock SQLAlchemy sessions and database operations.

## Migration Management

### Alembic Configuration

Database schema migrations are managed with Alembic:

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# View migration history
alembic history
```

### Configuration Files

- `alembic.ini`: Database connection string for migrations
- `app/config.py`: Application configuration with environment-specific settings
- `app/ingest.py`: Database URL resolution logic

## Vector Search Setup

PreThrift uses pgvector for semantic similarity search:

### Extension Installation
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Vector Columns
- `image_embedding_vec VECTOR(512)`: Image feature vectors
- `description_embedding_vec VECTOR(512)`: Text description vectors
- `openai_text_embedding_vec VECTOR(1536)`: OpenAI embedding vectors

### Similarity Queries
```sql
-- Cosine similarity search
SELECT id, title, 1 - (image_embedding_vec <=> $1) AS similarity
FROM garment
ORDER BY image_embedding_vec <=> $1
LIMIT 10;
```

## Connection Management

### Environment Variables

```bash
# Primary database URL (takes precedence)
DATABASE_URL=postgresql://user:pass@host:port/dbname

# AWS Secrets Manager (for production)
DATABASE_SECRET_ARN=arn:aws:secretsmanager:region:account:secret:name

# Individual components (fallback)
DB_HOST=localhost
DB_PORT=5433
DB_NAME=prethrift
DB_USER=prethrift
DB_PASSWORD=prethrift_dev
```

### Connection Pooling

Production deployments should use connection pooling:

```python
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

## Backup and Recovery

### Development Backups

```bash
# Create backup
docker exec prethrift-postgres pg_dump -U prethrift prethrift > backup.sql

# Restore backup
docker exec -i prethrift-postgres psql -U prethrift prethrift < backup.sql
```

### Production Considerations

- Automated daily backups with point-in-time recovery
- Read replicas for analytics and reporting workloads
- Connection pooling with PgBouncer or similar
- Monitoring with native PostgreSQL statistics

## Troubleshooting

### Common Issues

1. **Port conflicts**: Development uses port 5433 to avoid conflicts
2. **Extension missing**: Ensure pgvector extension is installed
3. **Connection refused**: Verify Docker containers are running
4. **Permission denied**: Check database user permissions

### Debug Commands

```bash
# Check container status
docker-compose -f docker-compose.dev.yml ps

# View PostgreSQL logs
docker-compose -f docker-compose.dev.yml logs postgres

# Connect to database
docker exec -it prethrift-postgres psql -U prethrift -d prethrift

# Test connection from application
python -c "from app.ingest import get_database_engine; print(get_database_engine().url)"
```

## Migration from SQLite

**✅ Completed**: All SQLite dependencies have been removed:

- Removed SQLite database files (`*.db`)
- Updated default database URLs to PostgreSQL
- Modified configuration to use PostgreSQL test databases
- Updated documentation to reflect PostgreSQL-only architecture

The system now uses PostgreSQL exclusively for consistency, performance, and production readiness.
