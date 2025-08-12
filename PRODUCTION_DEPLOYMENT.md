# Prethrift v2.0 Production Deployment Guide

## Overview

This guide covers the complete deployment of Prethrift v2.0's enhanced image search and ontology system to production. The system includes:

- **Enhanced Vector Search**: CLIP (512-dim) + OpenAI (1536-dim) embeddings
- **Rich Ontology**: 16 property columns for advanced filtering
- **Hybrid Search**: Vector similarity + metadata filtering
- **Performance Optimization**: HNSW indexing for sub-linear search

## Pre-Deployment Checklist

### 1. Database Requirements
- [ ] PostgreSQL 12+ with pgvector extension
- [ ] Sufficient storage for vector data (estimate: 8KB per garment for embeddings)
- [ ] Memory allocation for HNSW index operations (recommend 2GB+ free RAM)

### 2. Dependencies
- [ ] Python 3.8+ environment
- [ ] Required packages installed (see requirements.txt)
- [ ] CLIP model weights downloaded (~1.7GB)
- [ ] OpenAI API access configured

### 3. Infrastructure
- [ ] Application server with GPU support (recommended for CLIP)
- [ ] Redis/caching layer for frequently accessed embeddings
- [ ] CDN for image assets
- [ ] Load balancer for multiple app instances

## Deployment Steps

### Phase 1: Database Migration (Zero-Downtime)

```bash
# 1. Create database backup
pg_dump prethrift_db > backup_pre_v2_$(date +%Y%m%d_%H%M%S).sql

# 2. Run schema migrations
cd backend
alembic upgrade head

# 3. Verify schema
python -c "from app.db_models import Garment; print('Schema ready')"
```

**Expected migrations applied:**
- `0001_create_initial_tables` - Base schema
- `0002_add_vector_columns` - pgvector support
- `0003_add_hnsw_indexes` - Performance optimization
- `0004_fix_vector_dimensions` - CLIP compatibility
- `0005_add_openai_text_embeddings` - OpenAI support
- `0006_add_ontology_properties` - Rich metadata

### Phase 2: Data Migration (Scheduled Maintenance)

```bash
# 1. Test migration with dry run
python migrate_production_data.py --dry-run --batch-size 100

# 2. Migrate in batches during low traffic
python migrate_production_data.py --batch-size 50

# 3. Monitor progress
tail -f migration_*.log
```

**Migration process:**
- Generates CLIP embeddings for existing images
- Extracts ontology properties from descriptions
- Populates vector columns with proper indexing
- Maintains backward compatibility with JSON embeddings

### Phase 3: API Updates

```python
# Update search endpoints to use HybridSearchEngine
from app.hybrid_search import HybridSearchEngine

search_engine = HybridSearchEngine(session)

# Enhanced search with filtering
results = search_engine.search(
    query="blue denim jacket",
    filters={
        'category': 'outerwear',
        'price_range': (50, 200),
        'brand': ['levi', 'gap']
    },
    limit=20
)
```

### Phase 4: Performance Optimization

```sql
-- Monitor index usage
SELECT
    schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('garments', 'inventory_items');

-- Monitor query performance
EXPLAIN ANALYZE
SELECT * FROM garments
WHERE image_embedding_vec <-> '[...]' < 0.5
ORDER BY image_embedding_vec <-> '[...]' LIMIT 20;
```

## Production Configuration

### 1. Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/prethrift_prod
REDIS_URL=redis://localhost:6379/0

# API Keys
OPENAI_API_KEY=sk-...
CLIP_MODEL_PATH=/models/clip-vit-base-patch32

# Performance
VECTOR_SEARCH_CACHE_TTL=3600
BATCH_SIZE=50
MAX_CONCURRENT_EMBEDDINGS=4
```

### 2. Monitoring and Alerts

```yaml
# prometheus-alerts.yml
groups:
  - name: prethrift-v2
    rules:
      - alert: VectorSearchLatency
        expr: histogram_quantile(0.95, vector_search_duration_seconds) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Vector search response time high"

      - alert: EmbeddingGenerationFailed
        expr: increase(embedding_generation_failures_total[5m]) > 10
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Multiple embedding generation failures"
```

### 3. Scaling Considerations

**Horizontal Scaling:**
- Stateless application servers
- Shared database with read replicas
- Distributed CLIP inference (GPU instances)

**Vertical Scaling:**
- HNSW index memory requirements grow with data
- CLIP model inference benefits from GPU acceleration
- Consider model quantization for cost optimization

## Performance Benchmarks

### Expected Performance (10K garments):

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Vector similarity search | <50ms | 500 QPS |
| Hybrid search (with filters) | <100ms | 200 QPS |
| CLIP embedding generation | ~200ms | 5 RPS |
| Ontology property extraction | ~50ms | 20 RPS |

### Memory Usage:
- Base application: ~500MB
- CLIP model: ~1.7GB
- HNSW indexes: ~100MB per 10K vectors
- PostgreSQL buffers: 2GB+ recommended

## Rollback Plan

If issues arise, execute rollback in reverse order:

```bash
# 1. Revert API endpoints to use JSON embeddings
git checkout v1.9-stable
python manage.py deploy

# 2. Disable vector columns (data preserved)
ALTER TABLE garments ALTER COLUMN image_embedding_vec SET DEFAULT NULL;
ALTER TABLE garments ALTER COLUMN openai_text_embedding_vec SET DEFAULT NULL;

# 3. Full rollback (if necessary)
pg_restore backup_pre_v2_*.sql
```

## Monitoring Dashboard

Key metrics to track:

### Search Performance
- Vector search latency (p50, p95, p99)
- Search result relevance scores
- Cache hit rates for embeddings

### Data Quality
- Ontology extraction confidence scores
- CLIP embedding consistency
- Missing embedding rates

### System Health
- PostgreSQL connection pool usage
- Memory usage for HNSW operations
- GPU utilization for CLIP inference

## Troubleshooting

### Common Issues

**Vector dimension mismatch:**
```bash
# Check vector dimensions in database
SELECT
    array_length(image_embedding_vec, 1) as clip_dim,
    array_length(openai_text_embedding_vec, 1) as openai_dim
FROM garments
WHERE image_embedding_vec IS NOT NULL
LIMIT 5;

# Expected: clip_dim=512, openai_dim=1536
```

**HNSW index performance:**
```sql
-- Rebuild HNSW index if performance degrades
DROP INDEX CONCURRENTLY garments_image_embedding_vec_hnsw_idx;
CREATE INDEX CONCURRENTLY garments_image_embedding_vec_hnsw_idx
ON garments USING hnsw (image_embedding_vec vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

**Memory issues:**
```bash
# Monitor PostgreSQL memory usage
SELECT
    setting as shared_buffers_mb
FROM pg_settings
WHERE name = 'shared_buffers';

# Increase if needed (requires restart)
ALTER SYSTEM SET shared_buffers = '4GB';
SELECT pg_reload_conf();
```

## Security Considerations

### Vector Data Protection
- Embeddings contain semantic information about inventory
- Consider encryption at rest for sensitive fashion data
- Implement rate limiting for embedding generation endpoints

### API Security
- Authentication required for search endpoints
- Input validation for search queries and filters
- Monitoring for unusual search patterns

## Success Metrics

### Week 1 (Stability)
- [ ] Zero critical errors in production logs
- [ ] Search latency within expected ranges
- [ ] Database migration 100% complete

### Week 2-4 (Performance)
- [ ] Search relevance improved by 20%+ (user feedback)
- [ ] Filter usage increased by 50%+
- [ ] Page load times maintained or improved

### Month 1+ (Business Impact)
- [ ] User engagement metrics improved
- [ ] Conversion rates on filtered searches increased
- [ ] Reduced support queries about search relevance

## Next Phase Planning

### Advanced Features (v2.1)
- **Multi-modal search**: "Find me something like this image but in red"
- **Style transfer**: "Show me this dress in a different color"
- **Trend analysis**: Embedding-based fashion trend detection
- **Personalization**: User preference vectors for recommendation

### Architecture Evolution (v2.2)
- **Real-time updates**: Streaming embedding updates
- **Edge computing**: CLIP inference at CDN edge
- **Federated search**: Multi-tenant vector search
- **MLOps pipeline**: Automated model updates and A/B testing

---

**Deployment Lead**: [Your Team]
**Emergency Contact**: [On-call Engineer]
**Rollback Authority**: [Technical Lead]

*This guide represents the production deployment of a comprehensive vector search and ontology system. Follow each phase carefully and monitor system health throughout the process.*
