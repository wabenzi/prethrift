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

## 📋 Documentation Index

- **[Quick Start Guide](DEVELOPMENT.md)** - Get the development environment running
- **[Database Architecture](DATABASE.md)** - PostgreSQL setup, testing, and configuration
- **[Observability Guide](OBSERVABILITY.md)** - Monitoring, tracing, and metrics
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Complete technical overview
- **[End-to-End Testing](README-e2e.md)** - Integration testing workflows

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
