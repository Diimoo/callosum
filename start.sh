#!/bin/bash

# Callosum Start Script
# This script starts all services needed for the Callosum application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Starting Callosum Services${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check if a port is in use
check_port() {
    if lsof -i :$1 > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Start Docker services (Postgres, Redis, MinIO, Vespa)
echo -e "\n${YELLOW}[1/4] Starting Docker services...${NC}"
if [ -f "deployment/docker_compose/docker-compose.dev.yml" ]; then
    docker compose -f deployment/docker_compose/docker-compose.dev.yml up -d postgres redis minio vespa 2>/dev/null || \
    docker-compose -f deployment/docker_compose/docker-compose.dev.yml up -d postgres redis minio vespa
    echo -e "${GREEN}Docker services started${NC}"
else
    echo -e "${YELLOW}No docker-compose.dev.yml found, skipping Docker services${NC}"
fi

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Start API Server
echo -e "\n${YELLOW}[2/4] Starting API Server...${NC}"
if check_port 8082; then
    echo -e "${YELLOW}API Server already running on port 8082${NC}"
else
    cd "$SCRIPT_DIR/backend"
    export POSTGRES_PORT=5434
    export REDIS_PORT=6381
    export S3_ENDPOINT="http://localhost:9004"
    export AWS_ACCESS_KEY_ID=minioadmin
    export AWS_SECRET_ACCESS_KEY=minioadmin
    nohup uv run uvicorn onyx.main:app --host 0.0.0.0 --port 8082 --reload > /tmp/callosum-api.log 2>&1 &
    echo -e "${GREEN}API Server starting on port 8082${NC}"
    cd "$SCRIPT_DIR"
fi

# Start Model Server
echo -e "\n${YELLOW}[3/4] Starting Model Server...${NC}"
if check_port 9002; then
    echo -e "${YELLOW}Model Server already running on port 9002${NC}"
else
    cd "$SCRIPT_DIR/backend"
    export POSTGRES_PORT=5434
    export REDIS_PORT=6381
    nohup uv run uvicorn model_server.main:app --host 0.0.0.0 --port 9002 --reload > /tmp/callosum-model.log 2>&1 &
    echo -e "${GREEN}Model Server starting on port 9002${NC}"
    cd "$SCRIPT_DIR"
fi

# Start Frontend
echo -e "\n${YELLOW}[4/4] Starting Frontend...${NC}"
if check_port 3000; then
    echo -e "${YELLOW}Frontend already running on port 3000${NC}"
else
    cd "$SCRIPT_DIR/web"
    nohup npm run dev > /tmp/callosum-frontend.log 2>&1 &
    echo -e "${GREEN}Frontend starting on port 3000${NC}"
    cd "$SCRIPT_DIR"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   All services started!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nAccess the application at: ${GREEN}http://localhost:3000${NC}"
echo -e "API Server: ${GREEN}http://localhost:8082${NC}"
echo -e "Model Server: ${GREEN}http://localhost:9002${NC}"
echo -e "\nLogs:"
echo -e "  API Server:   /tmp/callosum-api.log"
echo -e "  Model Server: /tmp/callosum-model.log"
echo -e "  Frontend:     /tmp/callosum-frontend.log"
