#!/usr/bin/env bash
# VMtips Development Script
# Starts both frontend (hot reload) and backend (hot reload) in Docker
# Usage: ./scripts/dev.sh [up|down|build|logs|shell]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

cd "$PROJECT_ROOT"

case "${1:-up}" in
  up)
    echo "🚀 Starting VMtips development environment..."
    echo "   Frontend: http://localhost:5173"
    echo "   Backend:  http://localhost:8000"
    echo "   API docs: http://localhost:8000/docs"
    docker compose -f "$COMPOSE_FILE" up --build
    ;;

  down)
    echo "🛑 Stopping VMtips development environment..."
    docker compose -f "$COMPOSE_FILE" down
    ;;

  build)
    echo "🔨 Rebuilding Docker images..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    ;;

  logs)
    echo "📋 Showing logs..."
    docker compose -f "$COMPOSE_FILE" logs -f
    ;;

  shell-backend)
    echo "🐚 Opening shell in backend container..."
    docker compose -f "$COMPOSE_FILE" exec backend bash
    ;;

  shell-frontend)
    echo "🐚 Opening shell in frontend container..."
    docker compose -f "$COMPOSE_FILE" exec frontend bash
    ;;

  seed)
    echo "🌱 Running database seed..."
    docker compose -f "$COMPOSE_FILE" exec backend python seed.py
    ;;

  db-reset)
    echo "🗑️  Resetting database..."
    docker compose -f "$COMPOSE_FILE" down -v
    rm -f "$PROJECT_ROOT/data/vmtips.db"
    docker compose -f "$COMPOSE_FILE" up -d
    sleep 2
    docker compose -f "$COMPOSE_FILE" exec backend python seed.py || true
    echo "✅ Database reset and seeded"
    ;;

  *)
    echo "Usage: $0 [up|down|build|logs|shell-backend|shell-frontend|seed|db-reset]"
    echo ""
    echo "Commands:"
    echo "  up              Start dev environment (default)"
    echo "  down            Stop dev environment"
    echo "  build           Rebuild Docker images"
    echo "  logs            Follow container logs"
    echo "  shell-backend   Open shell in backend container"
    echo "  shell-frontend  Open shell in frontend container"
    echo "  seed            Run database seed script"
    echo "  db-reset        Reset database and re-seed"
    exit 1
    ;;
esac
