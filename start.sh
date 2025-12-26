#!/bin/bash
# Onyx Start Script - Start all services from scratch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Starting Onyx..."

# Run stop script first to ensure clean state
echo "📋 Running stop.sh to ensure clean state..."
"$SCRIPT_DIR/stop.sh"

echo ""
echo "🐳 Starting Docker Compose services..."
cd "$SCRIPT_DIR/deployment/docker_compose"
# Start core services - use dev ports for db/index/minio but not cache (6379 often in use)
docker compose -f docker-compose.yml up -d index relational_db cache minio
# Expose dev ports for services we need to access
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d index relational_db minio

# Wait for services to be ready
echo "  Waiting for services to be ready..."
sleep 5

# Check if database is ready
echo "  Checking database connection..."
for i in {1..30}; do
    if docker compose exec -T relational_db pg_isready -U postgres >/dev/null 2>&1; then
        echo "  ✅ Database is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}  ❌ Database failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Get the postgres port
POSTGRES_PORT=$(docker port "$(docker compose ps -q relational_db)" 5432 2>/dev/null | head -1 | cut -d: -f2)
if [ -z "$POSTGRES_PORT" ]; then
    POSTGRES_PORT=5432
fi
echo "  Database running on port $POSTGRES_PORT"

# Ensure Python dependencies are installed (including model_server extras)
echo ""
echo "📦 Ensuring Python dependencies are installed..."
cd "$SCRIPT_DIR"
uv sync --all-extras --quiet 2>/dev/null || uv sync --all-extras

# Run migrations
echo ""
echo "📦 Running database migrations..."
cd "$SCRIPT_DIR/backend"
POSTGRES_PORT=$POSTGRES_PORT uv run alembic upgrade head

# Start backend services in background
echo ""
echo "🔧 Starting backend services..."
cd "$SCRIPT_DIR/backend"

# Export environment variables
export POSTGRES_PORT=$POSTGRES_PORT
export POSTGRES_HOST=localhost
export VESPA_HOST=localhost
export REDIS_HOST=localhost
export MODEL_SERVER_HOST=localhost
export AUTH_TYPE=disabled
# MinIO/S3 credentials (default dev credentials)
# MinIO API is on port 9004 (remapped from 9000 to avoid conflict with model server)
MINIO_PORT=$(docker port onyx-minio-1 9000 2>/dev/null | head -1 | cut -d: -f2)
MINIO_PORT=${MINIO_PORT:-9004}
export S3_ENDPOINT_URL=http://localhost:$MINIO_PORT
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin

# Model server (port 9000)
echo "  Starting model server on port 9000..."
nohup uv run uvicorn model_server.main:app --host 0.0.0.0 --port 9000 > "$SCRIPT_DIR/logs/model_server.log" 2>&1 &
sleep 3

# Background jobs
echo "  Starting background jobs..."
nohup uv run python ./scripts/dev_run_background_jobs.py > "$SCRIPT_DIR/logs/background_jobs.log" 2>&1 &
sleep 2

# API server (port 8080)
echo "  Starting API server on port 8080..."
nohup uv run uvicorn onyx.main:app --host 0.0.0.0 --port 8080 > "$SCRIPT_DIR/logs/api_server.log" 2>&1 &
sleep 3

# Start frontend
echo ""
echo "🌐 Starting frontend..."
cd "$SCRIPT_DIR/web"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies..."
    npm install
fi

echo "  Starting Next.js dev server on port 3000..."
nohup npm run dev > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &

# Wait for services to fully start
echo ""
echo "⏳ Waiting for services to start (15 seconds)..."
sleep 15

# Verify services are running
echo ""
echo "🔍 Verifying services..."

check_port() {
    local port=$1
    local name=$2
    if ss -tlnp 2>/dev/null | grep -q ":$port " || lsof -i :$port >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ $name (port $port)${NC}"
        return 0
    else
        echo -e "  ${RED}❌ $name (port $port) - NOT RUNNING${NC}"
        return 1
    fi
}

all_ok=true
check_port 9000 "Model Server" || all_ok=false
check_port 8080 "API Server" || all_ok=false
check_port 3000 "Frontend" || all_ok=false

echo ""
if [ "$all_ok" = true ]; then
    echo -e "${GREEN}✅ Onyx is running!${NC}"
    echo ""
    echo "  🌐 Frontend:     http://localhost:3000"
    echo "  🔌 API Server:   http://localhost:8080"
    echo "  🤖 Model Server: http://localhost:9000"
    echo ""
    echo "  📁 Logs are in: $SCRIPT_DIR/logs/"
    echo ""
    echo "  To stop: ./stop.sh"
else
    echo -e "${YELLOW}⚠️  Some services may not have started properly${NC}"
    echo "  Check logs in: $SCRIPT_DIR/logs/"
fi
