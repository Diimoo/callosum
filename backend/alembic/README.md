# Alembic Migrations

This directory contains database migrations for the main Onyx schema using [Alembic](https://alembic.sqlalchemy.org/).

## Overview

Alembic manages schema changes for the PostgreSQL database. In multi-tenant mode, migrations can be applied to all tenant schemas or specific schemas.

## Directory Structure

```
alembic/
├── env.py              # Migration environment configuration
├── script.py.mako      # Template for new migration files
├── versions/           # Migration files
└── README.md
```

## Running Migrations

### Single-Tenant Mode

```bash
# Upgrade to the latest revision
alembic upgrade head

# Downgrade one revision
alembic downgrade -1
```

### Multi-Tenant Mode

In multi-tenant mode, you must specify migration targets:

```bash
# Upgrade all tenant schemas
alembic upgrade head -x upgrade_all_tenants=true

# Upgrade specific schemas
alembic upgrade head -x schemas=tenant_123,tenant_456

# Upgrade a range of tenants (alphabetically sorted)
alembic upgrade head -x tenant_range_start=0 -x tenant_range_end=100

# Continue on error (skip failed schemas)
alembic upgrade head -x upgrade_all_tenants=true -x continue=true
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration
alembic revision -m "description of changes"
```

## Configuration Options

Pass options via `-x key=value`:

- **`create_schema`**: Create schema if it doesn't exist (default: `true`)
- **`upgrade_all_tenants`**: Migrate all tenant schemas (default: `false`)
- **`continue`**: Continue on error for individual tenants (default: `false`)
- **`tenant_range_start`**: Start index for tenant range filtering (0-based)
- **`tenant_range_end`**: End index for tenant range filtering (exclusive)
- **`schemas`**: Comma-separated list of specific schema names to migrate

## Notes

- Kombu tables (`kombu_queue`, `kombu_message`) are excluded from migrations
- IAM authentication is supported via `USE_IAM_AUTH` environment variable
- Set `[logger_root] level=INFO` in `alembic.ini` to see migration logs
