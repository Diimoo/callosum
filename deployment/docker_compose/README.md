# Docker Compose Deployment

This directory contains Docker Compose configurations for deploying Onyx in various environments.

## Quick Start

```bash
# Copy environment template
cp env.template .env

# Start Onyx (development)
docker compose up -d

# Start Onyx (production with SSL)
docker compose -f docker-compose.prod.yml up -d
```

## Configuration Files

| File | Description |
|------|-------------|
| `docker-compose.yml` | Default development configuration |
| `docker-compose.dev.yml` | Development overrides (exposed ports) |
| `docker-compose.prod.yml` | Production with Let's Encrypt SSL |
| `docker-compose.prod-no-letsencrypt.yml` | Production without automatic SSL |
| `docker-compose.prod-cloud.yml` | Cloud production configuration |
| `docker-compose.multitenant-dev.yml` | Multi-tenant development setup |
| `docker-compose.search-testing.yml` | Search quality testing |
| `docker-compose.model-server-test.yml` | Model server testing |
| `docker-compose.resources.yml` | Standalone resources (Postgres, Redis, etc.) |

## Environment Templates

| File | Description |
|------|-------------|
| `env.template` | Main environment variables |
| `env.prod.template` | Production-specific settings |
| `env.nginx.template` | Nginx configuration variables |
| `env.multilingual.template` | Multi-language support settings |

## Services

The default stack includes:

- **api_server**: Onyx backend API
- **background**: Background job processor
- **web_server**: Next.js frontend
- **nginx**: Reverse proxy
- **relational_db**: PostgreSQL database
- **index**: Vespa search engine
- **cache**: Redis cache
- **inference_model_server**: ML model server
- **minio**: S3-compatible object storage

## Development Mode

Expose ports for local debugging:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

This exposes:
- API server on port 8080
- PostgreSQL on port 5432
- Vespa on ports 8081, 19071
- Redis on port 6379
- MinIO on ports 9000, 9001

## Production Deployment

### With Let's Encrypt SSL

1. Configure domain in `.env`:
   ```
   DOMAIN=your-domain.com
   ```

2. Initialize certificates:
   ```bash
   ./init-letsencrypt.sh
   ```

3. Start services:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

### Without SSL (behind proxy)

```bash
docker compose -f docker-compose.prod-no-letsencrypt.yml up -d
```

## Scripts

- **`install.sh`**: Interactive installation script
- **`init-letsencrypt.sh`**: SSL certificate initialization

## Documentation

For complete deployment documentation, see: https://docs.onyx.app/deployment/overview
