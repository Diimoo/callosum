#!/bin/bash
# Onyx Stop Script - Hard stop all services and free ports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛑 Stopping Onyx services..."

# Kill Node.js processes (frontend)
echo "  Stopping frontend (Next.js)..."
pkill -f "next dev" 2>/dev/null || true
pkill -f "node.*next" 2>/dev/null || true

# Kill Python processes (backend services)
echo "  Stopping backend services..."
pkill -f "uvicorn onyx.main:app" 2>/dev/null || true
pkill -f "uvicorn model_server.main:app" 2>/dev/null || true
pkill -f "dev_run_background_jobs" 2>/dev/null || true

# Kill any remaining uvicorn processes for this project
pkill -f "uvicorn.*onyx" 2>/dev/null || true
pkill -f "uvicorn.*model_server" 2>/dev/null || true

# Force kill anything on our ports (use multiple methods for reliability)
echo "  Freeing ports 3000, 8080, 9000..."
for port in 3000 8080 9000; do
    # Method 1: lsof
    pid=$(lsof -ti :$port 2>/dev/null) || true
    if [ -n "$pid" ]; then
        echo "    Killing process on port $port (PID: $pid) via lsof"
        kill -9 $pid 2>/dev/null || true
    fi
    # Method 2: ss + awk (for processes lsof might miss)
    pids=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | sort -u)
    for p in $pids; do
        if [ -n "$p" ]; then
            echo "    Killing process on port $port (PID: $p) via ss"
            kill -9 $p 2>/dev/null || true
        fi
    done
    # Method 3: fuser (most reliable)
    fuser -k $port/tcp 2>/dev/null || true
done

# Stop Docker Compose services (all possible compose projects)
echo "  Stopping Docker Compose services..."
cd "$SCRIPT_DIR/deployment/docker_compose"
docker compose down --remove-orphans 2>/dev/null || true

# Also stop any containers with onyx/callosum in the name
echo "  Stopping any remaining Onyx containers..."
docker ps -q --filter "name=onyx" | xargs -r docker stop 2>/dev/null || true
docker ps -q --filter "name=callosum" | xargs -r docker stop 2>/dev/null || true

# Free Redis port if still in use
echo "  Freeing Redis port 6379..."
pid=$(lsof -ti :6379 2>/dev/null) || true
if [ -n "$pid" ]; then
    echo "    Killing process on port 6379 (PID: $pid)"
    kill -9 $pid 2>/dev/null || true
fi

# Wait for ports to be freed
sleep 1

echo "✅ All Onyx services stopped"
