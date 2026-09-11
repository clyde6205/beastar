#!/bin/bash
# BeAstar.io - Start Script
# ========================
# Production-ready startup script for BeAstar backend

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
    log_info "Running in Docker container"
    IN_DOCKER=true
else
    log_info "Running on host machine"
    IN_DOCKER=false
fi

# Validate environment
log_info "Validating environment variables..."

MISSING_VARS=()

# Check for required variables
if [ -z "${SUPABASE_URL:-}" ]; then
    MISSING_VARS+=("SUPABASE_URL")
fi

if [ -z "${SUPABASE_KEY:-}" ]; then
    MISSING_VARS+=("SUPABASE_KEY")
fi

if [ -z "${RUNWAY_API_KEY:-}" ]; then
    log_warning "RUNWAY_API_KEY not set - video generation will fail"
    MISSING_VARS+=("RUNWAY_API_KEY")
fi

if [ -z "${REDIS_URL:-}" ]; then
    log_warning "REDIS_URL not set - background jobs will fail"
    MISSING_VARS+=("REDIS_URL")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_warning "Missing environment variables: ${MISSING_VARS[*]}"
    log_warning "Some features may not work without these variables"
fi

# Create logs directory
mkdir -p logs
log_info "Logs directory: $(pwd)/logs"

# Check if we should run migrations
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    log_info "Running database migrations..."
    python -m app.db.supabase_client --setup
    log_success "Database migrations complete"
fi

# Check if we should setup RPC functions
if [ "${SETUP_RPC:-false}" = "true" ]; then
    log_info "Setting up RPC functions..."
    python -c "from app.db.supabase_client import setup_rpc_functions; setup_rpc_functions()"
    log_success "RPC functions setup complete"
fi

# Start the application
log_info "Starting BeAstar backend..."

if [ "${IN_DOCKER}" = "true" ]; then
    # In Docker, use the standard command
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
else
    # On host, use reload for development
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
