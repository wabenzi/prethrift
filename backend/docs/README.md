# Backend Documentation

This directory contains comprehensive documentation for the PreThrift backend application.

## Documentation Overview

### Setup & Development
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development environment setup, local development workflows, and debugging guides
- **[README-e2e.md](README-e2e.md)** - End-to-end testing documentation and workflows

### Implementation & Architecture
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Comprehensive overview of backend implementation, features, and architecture decisions
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Monitoring, logging, tracing, and observability stack documentation

### Additional Resources
- **[../architecture/](../architecture/)** - PlantUML diagrams and API specifications
  - `architecture.puml` - System architecture diagrams
  - `sequences.puml` - Sequence diagrams for key workflows
  - `openapi.yaml` - API specification and documentation
- **[../tests/](../tests/)** - Test suites and testing documentation

## Quick Start

1. Start with [DEVELOPMENT.md](DEVELOPMENT.md) for environment setup
2. Review [OBSERVABILITY.md](OBSERVABILITY.md) for monitoring capabilities
3. Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for feature overview
4. See [README-e2e.md](README-e2e.md) for testing workflows

## Project Structure

```
backend/
├── docs/              # Documentation (this directory)
├── app/               # Application source code
├── tests/             # Test suites
├── db/                # Database files and migrations
├── architecture/      # System diagrams and API specs
└── alembic/          # Database migration scripts
```
