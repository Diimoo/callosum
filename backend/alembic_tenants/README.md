# Alembic Tenant Migrations

This directory contains database migrations for the **public schema** models using [Alembic](https://alembic.sqlalchemy.org/).

## Overview

While the main `alembic/` directory handles per-tenant schema migrations, this directory specifically manages migrations for models that exist in the public schema (shared across all tenants). These are models defined using `PublicBase`.

## Directory Structure

```text
alembic_tenants/
├── env.py              # Migration environment configuration
├── script.py.mako      # Template for new migration files
├── versions/           # Migration files for public schema
└── README.md
```

## Configuration

This directory is configured as `[schema_private]` in the main `alembic.ini` file:

```ini
[schema_private]
script_location = alembic_tenants
```

## Running Migrations

The main `alembic/` migrations handle both tenant and public schemas. Run from the `backend/` directory:

```bash
# Show current revision
alembic current

# Upgrade to latest
alembic upgrade head
```

## When to Use This vs `alembic/`

- **`alembic/`**: For tenant-specific models (per-schema tables)
- **`alembic_tenants/`**: For shared/public schema models that are common across all tenants

## Notes

- Kombu tables (`kombu_queue`, `kombu_message`) are excluded from migrations
- Migrations target `PublicBase.metadata` models only
