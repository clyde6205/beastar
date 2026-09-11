"""
BeAstar.io - Celery Background Tasks
====================================
Complete production-ready Celery task definitions for background processing.

Features:
- Video generation job processing
- Cleanup of abandoned/expired jobs
- Retry logic with exponential backoff
- Error handling and logging
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from celery import Celery
from celery.schedules import crontab

logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# Create Celery app
app = Celery(
    "beastar_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    # Rate limits
    task_rate_limits={
        "process_generation_task": "10/m",  # 10 per minute
        "cleanup_expired_jobs": "1/h",      # 1 per hour
    },
)

# Import Supabase client
from app.db.supabase_client import get_client


# ==========================================================================
# VIDEO GENERATION TASKS
# ==========================================================================

@app.task(
    bind=True,
    name="process_generation_task",
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max backoff
)
def process_generation_task(
    self,
    job_id: str,
    user_id: str,
    image_url: str,
    scenario_id: str,
    resolution: str,
    prompt: str,
):
    """
    Process a video generation job in the background.
    
    This is called by the /generate endpoint and runs asynchronously.
    
    Steps:
    1. Get scenario details from database
    2. Start generation with Runway (primary) or Kling (fallback)
    3. Poll for completion
    4. Download the generated video
    5. Add AI disclosure watermark
    6. Run content moderation
    7. Upload to Supabase Storage
    8. Update job status in database
    
    Args:
        job_id: Generation job ID
        user_id: User ID
        image_url: Input image URL
        scenario_id: Scenario ID
        resolution: Output resolution
        prompt: Video prompt
        
    Returns:
        Dict with job result details
    """
    try:
        logger.info(f"Starting generation task: {job_id}")
        
        # Get database client
        db = get_client()
        
        # Update job to rendering
        db.update_generation_job(job_id, status="rendering")
        
        # Import generation functions
        from app.providers.video_gen import (
            start_generation_with_fallback,
            poll_generation_with_fallback,
            add_ai_disclosure_to_video,
            upload_to_supabase_storage,
            run_content_moderation,
        )
        
        # Step 1: Start generation with failover
        provider_name, provider_task_id, _ = start_generation_with_fallback(
            image_url=image_url,
            prompt=prompt,
            resolution=resolution,
        )
        
        # Update job with provider info
        db.update_generation_job(
            job_id,
            status="rendering",
            provider=provider_name,
            provider_job_id=provider_task_id,
        )
        
        logger.info(f"Job {job_id} queued with {provider_name}: {provider_task_id}")
        
        # Step 2: Poll for completion
        status, output_url, cost_usd = poll_generation_with_fallback(
            provider_name=provider_name,
            provider_task_id=provider_task_id,
            resolution=resolution,
        )
        
        if status != "complete":
            db.update_generation_job(job_id, status="failed")
            logger.error(f"Job {job_id} failed with {provider_name}")
            return {
                "job_id": job_id,
                "status": "failed",
                "provider": provider_name,
                "error": "Generation failed",
            }
        
        logger.info(f"Job {job_id} completed: {output_url}")
        
        # Step 3: Download and add AI disclosure
        import tempfile
        import httpx
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Download the video
            with httpx.stream("GET", output_url) as response:
                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            
            # Add AI disclosure watermark
            watermarked_path = tmp_path.replace(".mp4", "_watermarked.mp4")
            add_ai_disclosure_to_video(output_url, watermarked_path)
            
            # Step 4: Run content moderation
            if not run_content_moderation(watermarked_path, user_id, job_id):
                db.update_generation_job(job_id, status="failed")
                logger.error(f"Job {job_id} failed moderation")
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": "Content moderation failed",
                }
            
            # Step 5: Upload to Supabase Storage
            public_url = upload_to_supabase_storage(
                watermarked_path,
                user_id,
                job_id,
            )
            
            # Step 6: Update job with final status
            db.update_generation_job(
                job_id,
                status="complete",
                output_url=public_url,
                render_cost_usd=cost_usd,
            )
            
            logger.info(f"Job {job_id} completed successfully: {public_url}")
            
            return {
                "job_id": job_id,
                "status": "complete",
                "provider": provider_name,
                "output_url": public_url,
                "cost_usd": cost_usd,
            }
            
        finally:
            # Cleanup temp files
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                if os.path.exists(watermarked_path):
                    os.unlink(watermarked_path)
            except Exception:
                pass
    
    except Exception as e:
        db = get_client()
        db.update_generation_job(job_id, status="failed")
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)
        
        # Retry if it's a transient error
        if isinstance(e, (ConnectionError, TimeoutError)):
            self.retry(exc=e, countdown=60)
        
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


# ==========================================================================
# CLEANUP TASKS
# ==========================================================================

@app.task(
    name="cleanup_expired_jobs",
    max_retries=1,
)
def cleanup_expired_jobs():
    """
    Cleanup abandoned and expired generation jobs.
    
    This runs periodically to:
    - Cancel jobs that have been queued for too long
    - Delete temporary files
    - Update job statuses
    - Clean up abandoned jobs
    
    Runs daily at midnight UTC.
    """
    try:
        db = get_client()
        
        logger.info("Running cleanup of expired jobs")
        
        # Get jobs that have been queued for more than 24 hours
        from datetime import datetime, timedelta
        
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        # Query for old queued jobs
        old_jobs = db.table("generation_jobs") \
            .select("id, status, created_at") \
            .eq("status", "queued") \
            .lt("created_at", twenty_four_hours_ago.isoformat()) \
            .execute()
        
        cleaned_up = 0
        
        # Mark old queued jobs as failed
        for job in old_jobs.data or []:
            job_id = job["id"]
            db.table("generation_jobs") \
                .update({"status": "failed", "completed_at": datetime.utcnow().isoformat()}) \
                .eq("id", job_id) \
                .execute()
            logger.info(f"Cleaned up expired job: {job_id}")
            cleaned_up += 1
        
        # Get jobs that have been rendering for more than 6 hours
        six_hours_ago = datetime.utcnow() - timedelta(hours=6)
        
        old_rendering_jobs = db.table("generation_jobs") \
            .select("id, status, created_at") \
            .eq("status", "rendering") \
            .lt("created_at", six_hours_ago.isoformat()) \
            .execute()
        
        # Mark old rendering jobs as failed
        for job in old_rendering_jobs.data or []:
            job_id = job["id"]
            db.table("generation_jobs") \
                .update({"status": "failed", "completed_at": datetime.utcnow().isoformat()}) \
                .eq("id", job_id) \
                .execute()
            logger.info(f"Cleaned up stuck rendering job: {job_id}")
            cleaned_up += 1
        
        # Clean up old temporary files
        import tempfile
        import os
        import time
        
        temp_dir = tempfile.gettempdir()
        cutoff = time.time() - 3600  # 1 hour old
        deleted_files = 0
        
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                    # Check if it's a video temp file (ends with .mp4 or _watermarked.mp4)
                    if filename.endswith('.mp4') or filename.endswith('_watermarked.mp4'):
                        os.unlink(filepath)
                        deleted_files += 1
                        logger.info(f"Deleted temp file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {filepath}: {str(e)}")
        
        logger.info(f"Cleanup task completed: {cleaned_up} jobs, {deleted_files} temp files")
        
        return {
            "status": "ok",
            "jobs_cleaned_up": cleaned_up,
            "temp_files_deleted": deleted_files,
            "total_cleaned": cleaned_up + deleted_files
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}


@app.task(
    name="cleanup_temp_files",
    max_retries=1,
)
def cleanup_temp_files():
    """
    Cleanup temporary files from the server.
    
    Runs hourly to remove old temp files.
    Focuses on video generation temp files (.mp4, _watermarked.mp4)
    """
    try:
        import tempfile
        import time
        
        # Get temp directory
        temp_dir = tempfile.gettempdir()
        
        # Find and delete files older than 1 hour
        cutoff = time.time() - 3600
        deleted = 0
        
        for filename in os.listdir(temp_dir):
            filepath = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                    # Only delete video-related temp files
                    if (filename.endswith('.mp4') or 
                        filename.endswith('_watermarked.mp4') or
                        filename.endswith('.tmp') or
                        filename.startswith('tmp')):
                        os.unlink(filepath)
                        deleted += 1
                        logger.debug(f"Deleted temp file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to delete {filepath}: {str(e)}")
        
        logger.info(f"Cleaned up {deleted} temporary files")
        return {"status": "ok", "deleted": deleted}
        
    except Exception as e:
        logger.error(f"Temp file cleanup failed: {str(e)}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ==========================================================================
# SCHEDULED TASKS
# ==========================================================================

# Configure periodic tasks
app.conf.beat_schedule = {
    "cleanup-expired-jobs": {
        "task": "beastar_tasks.cleanup_expired_jobs",
        "schedule": crontab(minute=0, hour=0),  # Midnight UTC daily
    },
    "cleanup-temp-files": {
        "task": "beastar_tasks.cleanup_temp_files",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
}
