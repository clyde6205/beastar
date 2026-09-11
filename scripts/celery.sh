#!/bin/bash
# BeAstar.io - Celery Worker Start Script
# =====================================
# Production-ready script for starting Celery workers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in Docker
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
else
    IN_DOCKER=false
fi

# Validate environment
log_info "Validating Celery environment..."

if [ -z "${REDIS_URL:-}" ]; then
    log_error "REDIS_URL is required for Celery"
    exit 1
fi

if [ -z "${SUPABASE_URL:-}" ]; then
    log_error "SUPABASE_URL is required"
    exit 1
fi

if [ -z "${SUPABASE_KEY:-}" ]; then
    log_error "SUPABASE_KEY is required"
    exit 1
fi

# Set default concurrency
CONCURRENCY=${CELERY_CONCURRENCY:-4}
log_info "Celery concurrency: ${CONCURRENCY}"

# Set log level
LOG_LEVEL=${CELERY_LOG_LEVEL:-INFO}
log_info "Celery log level: ${LOG_LEVEL}"

# Start Celery worker
log_info "Starting Celery worker..."

exec celery \
    -A app.worker \
    worker \
    --loglevel=${LOG_LEVEL} \
    --concurrency=${CONCURRENCY} \
    --queues=celery,high_priority \
    --prefetch-multiplier=1 \
    --max-tasks-per-child=100 \
    --max-memory-per-child=300000
