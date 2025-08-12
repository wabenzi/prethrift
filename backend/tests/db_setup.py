#!/usr/bin/env python3
"""
Database setup utilities for testing.

For integration tests, we use a separate test database on the same PostgreSQL instance.
For unit tests, we mock database interactions.
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add backend directory to path to import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Import after path setup (required for standalone script)
from app.db_models import Base  # noqa: E402


def create_test_database():
    """Create a separate test database for integration tests."""
    # Connect to the default database to create test database
    admin_url = "postgresql://prethrift:prethrift_dev@localhost:5433/prethrift"
    test_db_name = "prethrift_test"

    try:
        # Connect to main database with autocommit mode for DDL operations
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

        with admin_engine.connect() as conn:
            # Terminate existing connections to test database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
            """))

            # Drop test database if it exists
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))

            # Create fresh test database
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))

        admin_engine.dispose()

        # Connect to test database and enable pgvector extension
        test_url = f"postgresql://prethrift:prethrift_dev@localhost:5433/{test_db_name}"
        test_engine = create_engine(test_url)

        # Enable pgvector extension first
        with test_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

        # Now create all tables (which depend on vector types)
        Base.metadata.create_all(test_engine)

        test_engine.dispose()

        print(f"✅ Test database '{test_db_name}' created successfully")
        return test_url

    except OperationalError as e:
        print(f"❌ Failed to create test database: {e}")
        print(
            "Make sure PostgreSQL is running with Docker: "
            "docker-compose -f docker-compose.dev.yml up -d"
        )
        raise


def cleanup_test_database():
    """Clean up the test database after tests."""
    admin_url = "postgresql://prethrift:prethrift_dev@localhost:5433/prethrift"
    test_db_name = "prethrift_test"

    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

        with admin_engine.connect() as conn:
            # Terminate connections and drop database
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
            """))
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))

        admin_engine.dispose()
        print(f"✅ Test database '{test_db_name}' cleaned up")

    except OperationalError as e:
        print(f"⚠️  Warning: Could not clean up test database: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database setup for testing")
    parser.add_argument("--create", action="store_true", help="Create test database")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test database")

    args = parser.parse_args()

    if args.create:
        create_test_database()
    elif args.cleanup:
        cleanup_test_database()
    else:
        print("Use --create to create test database or --cleanup to remove it")
