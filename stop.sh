#!/bin/bash

# Callosum Stop Script
# This script stops all Callosum services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}========================================${NC}"
echo -e "${RED}   Stopping Callosum Services${NC}"
echo -e "${RED}========================================${NC}"

# Function to kill process on port
kill_port() {
    local port=$1
    local name=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}Stopping $name on port $port...${NC}"
        lsof -ti :$port | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}$name stopped${NC}"
    else
        echo -e "${YELLOW}$name not running on port $port${NC}"
    fi
}

# Stop Frontend (port 3000)
echo -e "\n${YELLOW}[1/4] Stopping Frontend...${NC}"
kill_port 3000 "Frontend"

# Stop API Server (port 8082)
echo -e "\n${YELLOW}[2/4] Stopping API Server...${NC}"
kill_port 8082 "API Server"

# Stop Model Server (port 9002)
echo -e "\n${YELLOW}[3/4] Stopping Model Server...${NC}"
kill_port 9002 "Model Server"

# Stop Docker services
echo -e "\n${YELLOW}[4/4] Stopping Docker services...${NC}"
if [ -f "deployment/docker_compose/docker-compose.dev.yml" ]; then
    docker compose -f deployment/docker_compose/docker-compose.dev.yml down 2>/dev/null || \
    docker-compose -f deployment/docker_compose/docker-compose.dev.yml down 2>/dev/null || true
    echo -e "${GREEN}Docker services stopped${NC}"
else
    echo -e "${YELLOW}No docker-compose.dev.yml found, skipping Docker services${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   All services stopped!${NC}"
echo -e "${GREEN}========================================${NC}"
