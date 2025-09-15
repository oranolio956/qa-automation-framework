#!/bin/bash
# Deploy Chatbot Orchestrator Service

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
CHAT_API_TOKEN="${CHAT_API_TOKEN:-$(openssl rand -hex 32)}"
RATE_LIMIT_PER_MIN="${RATE_LIMIT_PER_MIN:-100}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Deploying Chatbot Orchestrator Service..."

# Build Docker image
log "Building Docker image..."
docker build -t orchestrator-bot "$SCRIPT_DIR"

# Stop existing container if running
docker stop orchestrator-bot 2>/dev/null || true
docker rm orchestrator-bot 2>/dev/null || true

# Run the container
log "Starting orchestrator service..."
docker run -d \
    --name orchestrator-bot \
    -e REDIS_URL="$REDIS_URL" \
    -e CHAT_API_TOKEN="$CHAT_API_TOKEN" \
    -e RATE_LIMIT_PER_MIN="$RATE_LIMIT_PER_MIN" \
    -p 5000:5000 \
    --restart unless-stopped \
    orchestrator-bot

log "Waiting for service to start..."
sleep 5

# Test the service
if curl -f http://localhost:5000/health >/dev/null 2>&1; then
    log "✅ Chatbot Orchestrator Service deployed successfully"
    log "🔗 API available at: http://localhost:5000"
    log "🔑 API Token: $CHAT_API_TOKEN"
    log "📊 Health: http://localhost:5000/health"
else
    log "❌ Service failed to start properly"
    docker logs orchestrator-bot
    exit 1
fi

log "Phase 14B complete: Chatbot orchestrator deployed."