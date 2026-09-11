"""
BeAstar.io - Celery Worker Configuration
======================================
Complete production-ready Celery worker setup for background job processing.

Features:
- Celery worker with Redis broker
- Automatic task discovery
- Logging configuration
- Error handling
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from celery import Celery

# Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("celery_worker.log"),
    ],
)
logger = logging.getLogger(__name__)

# Create Celery app
app = Celery(
    "beastar_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=300000,  # 300MB
    # Result configuration
    result_expires=3600,  # 1 hour
    result_persistent=True,
)

# Configure logging for Celery
app.conf.update(
    worker_log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    worker_task_log_format="%(asctime)s - %(name)s - %(levelname)s - [%(task_name)s] %(message)s",
    worker_log_level="INFO",
    task_annotations={
        "beastar_tasks.process_generation_task": {
            "rate_limit": "10/m",
            "max_retries": 3,
        },
    },
)

# Import tasks to register them
from app.tasks import (
    process_generation_task,
    cleanup_expired_jobs,
    cleanup_temp_files,
)

logger.info("Celery worker configured successfully")

if __name__ == "__main__":
    # Run the worker
    logger.info("Starting Celery worker...")
    app.worker_main(argv=["worker", "--loglevel=INFO"])
