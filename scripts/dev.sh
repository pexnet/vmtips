#!/usr/bin/env bash
# VMTips Development Script
# Single container: backend serves both API and frontend static files
# Usage: ./scripts/dev.sh [up|down|build|logs|shell|seed|db-reset]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

cd "$PROJECT_ROOT"

case "${1:-up}" in
  up)
    echo "🚀 Starting VMTips..."
    echo "   App:      http://localhost:8000"
    echo "   API docs: http://localhost:8000/docs"
    echo "   Health:   http://localhost:8000/health"
    docker compose -f "$COMPOSE_FILE" up --build
    ;;

  down)
    echo "🛑 Stopping VMTips..."
    docker compose -f "$COMPOSE_FILE" down
    ;;

  build)
    echo "🔨 Rebuilding Docker image..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    ;;

  logs)
    echo "📋 Showing logs..."
    docker compose -f "$COMPOSE_FILE" logs -f
    ;;

  shell)
    echo "🐚 Opening shell in app container..."
    docker compose -f "$COMPOSE_FILE" exec app bash
    ;;

  seed)
    echo "🌱 Running database seed..."
    docker compose -f "$COMPOSE_FILE" exec app python seed.py
    ;;

  db-reset)
    echo "🗑️  Resetting database..."
    docker compose -f "$COMPOSE_FILE" down -v
    docker compose -f "$COMPOSE_FILE" up -d
    sleep 2
    docker compose -f "$COMPOSE_FILE" exec app python seed.py || true
    echo "✅ Database reset and seeded"
    ;;

  *)
    echo "Usage: $0 [up|down|build|logs|shell|seed|db-reset]"
    echo ""
    echo "Commands:"
    echo "  up         Start app (default)"
    echo "  down       Stop app"
    echo "  build      Rebuild Docker image"
    echo "  logs       Follow container logs"
    echo "  shell      Open shell in app container"
    echo "  seed       Run database seed"
    echo "  db-reset   Reset database and re-seed"
    exit 1
    ;;
esac
