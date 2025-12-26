# Onyx

Onyx is an open-source AI-powered knowledge assistant that connects to your organization's data sources and provides intelligent search and chat capabilities.

## Features

- **Unified Search**: Search across all your connected data sources
- **AI Chat**: Ask questions and get answers with citations from your documents
- **100+ Connectors**: Connect to Slack, Google Drive, Confluence, GitHub, and more
- **Enterprise Ready**: Multi-tenant support, SSO, and role-based access control
- **Self-Hosted**: Deploy on your own infrastructure for full data control

## Quick Start

### Using Docker Compose

```bash
cd deployment/docker_compose
cp env.template .env
docker compose up -d
```

Visit `http://localhost:3000` to access Onyx.

### Using Helm (Kubernetes)

```bash
cd deployment/helm
helm dependency update ./charts/onyx
helm install onyx ./charts/onyx --namespace onyx --create-namespace
```

## Documentation

- [Official Documentation](https://docs.onyx.app)
- [Deployment Guide](https://docs.onyx.app/deployment/overview)
- [API Reference](https://docs.onyx.app/apis)

## Project Structure

```text
onyx/
├── backend/           # Python FastAPI backend
│   ├── onyx/          # Main application code
│   ├── alembic/       # Database migrations
│   └── tests/         # Backend tests
├── web/               # Next.js frontend
├── deployment/        # Deployment configurations
│   ├── docker_compose/
│   ├── helm/
│   └── terraform/
├── desktop/           # Desktop application (Tauri)
├── examples/          # Example integrations
└── tools/             # Developer tools
```

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed setup instructions.

### Prerequisites

- Python 3.11
- Node.js 22+
- Docker (for external services)

### Quick Setup

```bash
# Backend setup
uv venv .venv --python 3.11
source .venv/bin/activate
uv sync --all-extras

# Frontend setup
cd web && npm install

# Start external services
cd deployment/docker_compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d index relational_db cache minio

# Run database migrations
cd backend && alembic upgrade head
```

### Running Locally

Start these services in separate terminals:

```bash
# Frontend (port 3000)
cd web && npm run dev

# Model server (port 9000)
cd backend && uvicorn model_server.main:app --reload --port 9000

# Background jobs
cd backend && python ./scripts/dev_run_background_jobs.py

# API server (port 8080)
cd backend && AUTH_TYPE=disabled uvicorn onyx.main:app --reload --port 8080
```

Visit `http://localhost:3000` to access the application.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, Celery
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Search Engine**: Vespa
- **Database**: PostgreSQL
- **Cache**: Redis
- **File Storage**: S3-compatible (MinIO)

## Community

- [Discord](https://discord.gg/4NA5SbzrWb)
- [GitHub Issues](https://github.com/onyx-dot-app/onyx/issues)

## License

MIT License - see [LICENSE](./LICENSE) for details.

Enterprise features under `ee/` directories are separately licensed.
