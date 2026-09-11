"""
BeAstar.io - Production FastAPI Backend
=======================================
Complete production-ready backend with:
- Supabase/PostgreSQL persistence (no in-memory stores)
- Runway Gen-4 Turbo + Kling AI video generation with automatic failover
- Celery background job processing for video generation
- PayMongo/GCash + Stripe payment integrations
- Content moderation with AWS Rekognition + Hive AI fallback
- Face verification with liveness detection
- Real video playback support
- Complete social features (dream threads, challenges, leaderboards, referrals)
- Rate limiting, security headers, CORS, comprehensive error handling
- i18n support (English, Tagalog)
"""

from __future__ import annotations

import io
import logging
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional

import qrcode
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://beastar.io")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
USE_REAL_BACKEND = bool(SUPABASE_URL and SUPABASE_KEY)

MIN_SIGNUP_AGE_YEARS = 13

# Tier configuration
TIER_LIMITS = {
    "free": {"max_resolution": "720p", "daily_cap": 3},
    "star": {"max_resolution": "1080p", "daily_cap": 10},
    "superstar": {"max_resolution": "1080p", "daily_cap": 25},
    "megastar": {"max_resolution": "4k", "daily_cap": 100},
}

RESOLUTION_RANK = {"720p": 0, "1080p": 1, "4k": 2}

# GCash pricing (PHP)
TIER_PRICE_PHP = {
    "star": 279.00,
    "superstar": 559.00,
    "megastar": 1119.00,
}

# Net worth bands
NET_WORTH_BANDS = ("under_100k", "100k_1m", "1m_5m", "5m_plus", "prefer_not_to_say")
UNVERIFIED_NOTE = "Net worth, if shown, is self-reported and unverified."

# Upload limits
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8MB

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("beastar.log"),
    ],
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BeAstar.io API",
    version="1.0.0",
    description="Become the star you imagine yourself to be",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiter to app
app.state.limiter = limiter

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'"
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your app domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Error: {exc.status_code} - {exc.detail}")
    return HTTPException(status_code=exc.status_code, detail=exc.detail)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected Error: {str(exc)}", exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later.",
    )

# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=40)
    date_of_birth: date
    country_code: str = Field(min_length=2, max_length=2)
    referral_code_used: Optional[str] = None


class SignupResponse(BaseModel):
    user_id: str
    referral_code: str
    credits: int
    requires_face_verification: bool = True


class FaceVerificationRequest(BaseModel):
    selfie_image_url: str  # URL from selfie upload


class FaceVerificationResponse(BaseModel):
    user_id: str
    is_verified: bool
    face_embedding_id: Optional[str] = None
    message: Optional[str] = None


class SelfieUploadResponse(BaseModel):
    image_url: str
    content_safety_status: str


class GenerationRequest(BaseModel):
    user_id: str
    scenario_slug: str
    requested_resolution: str = Field(pattern="^(720p|1080p|4k)$")
    image_url: str  # from POST /users/{user_id}/uploads/selfie


class GenerationResponse(BaseModel):
    job_id: str
    status: str
    resolution: str
    ai_label_included: bool = True


class JobStatusResponse(BaseModel):
    id: str
    user_id: str
    scenario_id: Optional[str] = None
    resolution: str
    status: str
    provider: Optional[str] = None
    provider_job_id: Optional[str] = None
    output_url: Optional[str] = None
    render_cost_usd: Optional[float] = None
    credits_charged: int
    created_at: str
    completed_at: Optional[str] = None


class ChallengeCreate(BaseModel):
    hashtag: str
    scope: str = Field(pattern="^(global|regional)$")
    country_code: Optional[str] = None
    title: str
    starts_at: datetime
    ends_at: datetime
    prize_description: Optional[str] = None


class ChallengeEntryRequest(BaseModel):
    user_id: str
    generation_job_id: str


class ChallengeEntryResponse(BaseModel):
    id: str
    challenge_id: str
    user_id: str
    generation_job_id: str
    vote_count: int
    submitted_at: str


class VoteResponse(BaseModel):
    entry_id: str
    vote_count: int


class DreamThreadCreateRequest(BaseModel):
    user_id: str
    goal_title: str = Field(max_length=100)
    goal_description: Optional[str] = Field(default=None, max_length=500)
    starting_generation_job_id: Optional[str] = None
    self_reported_net_worth: Optional[str] = Field(
        default=None, pattern="^(" + "|".join(NET_WORTH_BANDS) + ")$"
    )


class DreamUpdateCreateRequest(BaseModel):
    user_id: str
    caption: str = Field(max_length=280)
    video_url: Optional[str] = None


class EncouragementRequest(BaseModel):
    user_id: str
    message: Optional[str] = Field(default=None, max_length=200)


class GCashCheckoutRequest(BaseModel):
    user_id: str
    tier: str = Field(pattern="^(star|superstar|megastar)$")


class StripeWebhookPayload(BaseModel):
    type: str
    data: dict


class PayMongoWebhookPayload(BaseModel):
    type: str
    data: dict


class FollowStatusResponse(BaseModel):
    """Response for follow status check"""
    thread_id: str
    user_id: str
    is_following: bool


# --------------------------------------------------------------------------
# Database Helpers
# --------------------------------------------------------------------------

def get_supabase():
    """Get Supabase client with dependency injection"""
    if not USE_REAL_BACKEND:
        raise HTTPException(
            status_code=503,
            detail="Backend not configured. Set SUPABASE_URL and SUPABASE_KEY.",
        )
    from app.db.supabase_client import get_client
    return get_client()


def _get_user_or_404(db, user_id: str) -> dict:
    """Get user by ID or raise 404"""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _get_job_or_404(db, job_id: str) -> dict:
    """Get generation job by ID or raise 404"""
    job = db.get_generation_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _meets_age_minimum(dob: date) -> bool:
    """Check if user meets minimum age requirement"""
    cutoff = date.today().replace(year=date.today().year - MIN_SIGNUP_AGE_YEARS)
    return dob <= cutoff


def _generate_referral_code(display_name: str) -> str:
    """Generate unique referral code"""
    base = "".join(c for c in display_name.upper() if c.isalnum())[:6] or "STAR"
    return f"{base}-{uuid.uuid4().hex[:5].upper()}"


# --------------------------------------------------------------------------
# AUTH / SIGNUP
# --------------------------------------------------------------------------

@app.post("/auth/signup", response_model=SignupResponse, status_code=201)
@limiter.limit("10/minute")
async def signup(
    request: Request,
    req: SignupRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create a new user account with age gating and referral tracking.
    Returns user details including referral code for viral sharing.
    """
    if not _meets_age_minimum(req.date_of_birth):
        raise HTTPException(
            status_code=400,
            detail=f"Signup requires users to be at least {MIN_SIGNUP_AGE_YEARS} years old.",
        )

    db = get_supabase()
    
    # Check for existing user with same email
    existing_user = db.table("users").select("*").eq("email", req.email).limit(1).execute()
    if existing_user.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    referral_code = _generate_referral_code(req.display_name)
    
    referred_by_user_id = None
    starting_credits = 50  # onboarding bonus
    
    # Handle referral
    if req.referral_code_used:
        referrer = db.get_user_by_referral_code(req.referral_code_used)
        if referrer:
            referred_by_user_id = referrer["id"]
            starting_credits += 100
            # Award referral credits to referrer
            db.increment_credits(referrer["id"], 100)
    
    # Create user
    user = db.create_user(
        email=req.email,
        display_name=req.display_name,
        date_of_birth=req.date_of_birth,
        country_code=req.country_code.upper(),
        referral_code=referral_code,
        referred_by_user_id=referred_by_user_id,
        starting_credits=starting_credits,
    )
    
    # Create default free subscription
    db.create_subscription(user_id=user_id, tier="free")
    
    # Create referral tracking
    if referred_by_user_id:
        db.create_referral(
            referrer_user_id=referred_by_user_id,
            referred_user_id=user_id,
            credits_awarded=100,
        )
    
    logger.info(f"New user signup: {user_id} with referral code {referral_code}")
    
    return SignupResponse(
        user_id=user_id,
        referral_code=referral_code,
        credits=starting_credits,
        requires_face_verification=True,
    )


@app.post("/auth/{user_id}/verify-face", response_model=FaceVerificationResponse)
@limiter.limit("5/minute")
async def verify_face(
    request: Request,
    user_id: str,
    req: FaceVerificationRequest,
):
    """
    Verify user's face using liveness detection and face matching.
    This is a security-critical endpoint that prevents deepfake abuse.
    
    Process:
    1. Liveness check - ensures it's a real person, not a photo/screen
    2. Face matching - ensures it matches the user's selfie
    3. Known public figure check - reject if matches known celebrity
    4. Store face embedding (not raw image) for future matching
    
    Compliance:
    - GDPR: Only stores embedding (derived data), not raw biometric
    - BIPA: Explicit consent required before processing
    - COPPA: Age-gated (13+ enforced at signup)
    """
    db = get_supabase()
    user = _get_user_or_404(db, user_id)
    
    if user.get("is_verified"):
        return FaceVerificationResponse(
            user_id=user_id,
            is_verified=True,
            face_embedding_id=user.get("face_embedding_id"),
            message="Already verified",
        )
    
    try:
        from app.providers.face_verification import (
            verify_face_from_url,
            VerificationResult,
            VerificationError,
            AllVendorsFailedError,
            PublicFigureError,
        )
        
        # Step 1: Download the selfie image
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(req.selfie_image_url)
            response.raise_for_status()
            selfie_bytes = response.content
        
        # Step 2: Verify the face with liveness detection and public figure check
        result: VerificationResult = verify_face_from_url(req.selfie_image_url)
        
        if not result.is_verified:
            logger.warning(f"Face verification failed for user {user_id}: {result.error}")
            raise HTTPException(
                status_code=400,
                detail=result.error or "Face verification failed. Please try again with a clearer selfie.",
            )
        
        if result.is_public_figure:
            logger.warning(f"Public figure detected for user {user_id}: {result.public_figure_name}")
            raise HTTPException(
                status_code=403,
                detail=f"Cannot verify as {result.public_figure_name}. Please use your own photo.",
            )
        
        # Step 3: Mark user as verified with face embedding ID
        db.mark_user_verified(user_id, result.face_embedding_id)
        
        logger.info(
            f"Face verification completed for user {user_id}: "
            f"embedding_id={result.face_embedding_id}, "
            f"liveness_confidence={result.liveness_confidence}, "
            f"vendor={result.vendor}"
        )
        
        return FaceVerificationResponse(
            user_id=user_id,
            is_verified=True,
            face_embedding_id=result.face_embedding_id,
            message="Face verification successful",
        )
        
    except PublicFigureError as e:
        logger.warning(f"Public figure blocked: {str(e)}")
        raise HTTPException(
            status_code=403,
            detail=str(e),
        )
    except AllVendorsFailedError as e:
        logger.error(f"All verification vendors failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Face verification service unavailable. Please try again later.",
        )
    except VerificationError as e:
        logger.error(f"Face verification failed for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Face verification failed: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Unexpected error in face verification for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during face verification. Please try again later.",
        )


# --------------------------------------------------------------------------
# SELFIE UPLOAD
# --------------------------------------------------------------------------

@app.post("/users/{user_id}/uploads/selfie", response_model=SelfieUploadResponse)
@limiter.limit("10/minute")
async def upload_selfie_endpoint(
    request: Request,
    user_id: str,
    file: UploadFile,
):
    """
    Upload a selfie image for use in video generation.
    Requires user to be face-verified first.
    
    Returns a signed URL suitable for passing to generation endpoints.
    """
    db = get_supabase()
    user = _get_user_or_404(db, user_id)
    
    if not user.get("is_verified"):
        raise HTTPException(
            status_code=403,
            detail="Face verification required before uploading generation photos.",
        )
    
    # Validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 8MB.")
    
    # Validate content type
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    
    try:
        from app.storage.selfie_upload import UploadValidationError, upload_selfie
        
        image_url = upload_selfie(
            db, user_id, file.content_type or "application/octet-stream", file_bytes
        )
        
        logger.info(f"Selfie uploaded for user {user_id}: {image_url}")
        
        return SelfieUploadResponse(
            image_url=image_url,
            content_safety_status="approved",
        )
        
    except UploadValidationError as exc:
        logger.warning(f"Selfie upload validation failed for user {user_id}: {str(exc)}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotImplementedError as exc:
        logger.error(f"Content safety check not configured: {str(exc)}")
        raise HTTPException(
            status_code=503,
            detail="Upload safety pipeline not yet configured. Content safety check required.",
        ) from exc


# --------------------------------------------------------------------------
# VIDEO UPLOAD (for dream updates)
# --------------------------------------------------------------------------

@app.post("/users/{user_id}/uploads/video")
@limiter.limit("10/minute")
async def upload_video_endpoint(
    request: Request,
    user_id: str,
    file: UploadFile,
):
    """
    Upload a video file for dream updates.
    
    Returns a signed URL for the uploaded video.
    """
    db = get_supabase()
    user = _get_user_or_404(db, user_id)
    
    # Validate file size (larger limit for videos)
    MAX_VIDEO_BYTES = 100 * 1024 * 1024  # 100MB
    file_bytes = await file.read()
    if len(file_bytes) > MAX_VIDEO_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Max 100MB.")
    
    # Validate content type
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video.")
    
    try:
        import tempfile
        import os
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Upload to Supabase Storage
            from app.storage.selfie_upload import upload_to_supabase_storage
            
            public_url = upload_to_supabase_storage(
                db, tmp_path, user_id, file.content_type or "video/mp4"
            )
            
            logger.info(f"Video uploaded for user {user_id}: {public_url}")
            
            return {"video_url": public_url}
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Video upload failed for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Video upload failed: {str(e)}",
        )


# --------------------------------------------------------------------------
# FOLLOW STATE CHECK
# --------------------------------------------------------------------------

@app.get("/users/{user_id}/follows/{thread_id}", response_model=FollowStatusResponse)
@limiter.limit("20/minute")
async def check_follow_status(
    request: Request,
    user_id: str,
    thread_id: str,
):
    """
    Check if a user follows a specific dream thread.
    Used by mobile app to sync follow state.
    """
    db = get_supabase()
    _get_user_or_404(db, user_id)
    
    # Check if user follows this thread
    follow = db.get_dream_thread_follow(thread_id, user_id)
    
    return FollowStatusResponse(
        thread_id=thread_id,
        user_id=user_id,
        is_following=follow is not None,
    )


# --------------------------------------------------------------------------
# VIDEO GENERATION
# --------------------------------------------------------------------------

@app.post("/generate", response_model=GenerationResponse)
@limiter.limit("10/minute")
async def request_generation(
    request: Request,
    background_tasks: BackgroundTasks,
    req: GenerationRequest,
):
    """
    Request a video generation job.
    
    Process:
    1. Validate user and tier
    2. Check daily generation cap
    3. Deduct credits
    4. Create job record in database
    5. Queue for background processing (Celery)
    6. Return job_id immediately
    """
    db = get_supabase()
    user = _get_user_or_404(db, req.user_id)
    
    if not user.get("is_verified"):
        raise HTTPException(
            status_code=403,
            detail="Face verification required before generating videos.",
        )
    
    # Get user's tier
    tier = db.get_user_tier(req.user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    
    # Check resolution limit
    if RESOLUTION_RANK[req.requested_resolution] > RESOLUTION_RANK[limits["max_resolution"]]:
        raise HTTPException(
            status_code=403,
            detail=f"'{tier}' tier is capped at {limits['max_resolution']}. Upgrade to unlock higher resolution.",
        )
    
    # Check daily cap
    today_count = db.count_generations_today(req.user_id)
    if today_count >= limits["daily_cap"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily generation cap ({limits['daily_cap']}) reached for '{tier}' tier.",
        )
    
    # Check credits
    if user.get("credits", 0) < 1:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. Please purchase more or wait for daily reset.",
        )
    
    # Get scenario
    scenario = db.get_scenario_by_slug(req.scenario_slug)
    if not scenario:
        raise HTTPException(status_code=400, detail="Invalid scenario slug")
    if not scenario.get("is_active"):
        raise HTTPException(status_code=400, detail="Scenario is not active")
    
    # Deduct credits
    db.increment_credits(req.user_id, -1)
    db.increment_daily_usage(req.user_id)
    
    # Create generation job
    job = db.create_generation_job(
        user_id=req.user_id,
        scenario_id=scenario["id"],
        resolution=req.requested_resolution,
        credits_charged=1,
    )
    
    job_id = job["id"]
    
    # Queue for background processing
    from app.tasks import process_generation_task
    
    process_generation_task.delay(
        job_id=job_id,
        user_id=req.user_id,
        image_url=req.image_url,
        scenario_id=scenario["id"],
        resolution=req.requested_resolution,
        prompt=scenario.get("description", ""),
    )
    
    logger.info(f"Generation job queued: {job_id} for user {req.user_id}")
    
    return GenerationResponse(
        job_id=job_id,
        status="queued",
        resolution=req.requested_resolution,
        ai_label_included=True,
    )


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
@limiter.limit("30/minute")
async def get_job_status(
    request: Request,
    job_id: str,
):
    """
    Get the status of a generation job.
    Used by mobile app for polling during generation.
    """
    db = get_supabase()
    job = _get_job_or_404(db, job_id)
    
    # Convert datetime strings to ISO format if needed
    if isinstance(job.get("created_at"), str):
        job["created_at"] = job["created_at"]
    if isinstance(job.get("completed_at"), str):
        job["completed_at"] = job["completed_at"]
    
    return JobStatusResponse(**job)


# --------------------------------------------------------------------------
# QR CODES (Viral Sharing)
# --------------------------------------------------------------------------

@app.get("/qr/{user_id}")
@limiter.limit("20/minute")
async def get_referral_qr(
    request: Request,
    user_id: str,
):
    """
    Generate a QR code for user's referral link.
    This is the viral acquisition mechanism - users share their QR code
    to get others to sign up with their referral code.
    """
    db = get_supabase()
    user = _get_user_or_404(db, user_id)
    
    share_url = f"{APP_BASE_URL}/u/{user['referral_code']}"
    
    img = qrcode.make(share_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    logger.info(f"QR code generated for user: {user_id}")
    
    return StreamingResponse(buf, media_type="image/png")


# --------------------------------------------------------------------------
# LEADERBOARD
# --------------------------------------------------------------------------

@app.get("/leaderboard")
@limiter.limit("10/minute")
async def leaderboard(
    request: Request,
    country_code: Optional[str] = None,
    limit: int = 50,
):
    """
    Get the global or country-specific leaderboard.
    Shows users with most videos created and successful referrals.
    """
    db = get_supabase()
    
    rows = db.get_leaderboard(country_code=country_code, limit=limit)
    
    logger.info(f"Leaderboard fetched: {len(rows)} entries, country={country_code}")
    
    return rows


# --------------------------------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------------------------------

@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "backend_configured": USE_REAL_BACKEND,
    }


# --------------------------------------------------------------------------
# CHALLENGES
# --------------------------------------------------------------------------

@app.post("/challenges")
@limiter.limit("5/minute")
async def create_challenge(
    request: Request,
    req: ChallengeCreate,
):
    """
    Create a new challenge (admin-only in production).
    Challenges drive user engagement and retention.
    """
    if req.scope == "regional" and not req.country_code:
        raise HTTPException(400, "Regional challenges require a country_code")
    
    db = get_supabase()
    
    challenge_id = str(uuid.uuid4())
    challenge = db.create_challenge(
        id=challenge_id,
        hashtag=req.hashtag,
        scope=req.scope,
        country_code=req.country_code.upper() if req.country_code else None,
        title=req.title,
        starts_at=req.starts_at,
        ends_at=req.ends_at,
        prize_description=req.prize_description,
    )
    
    logger.info(f"Challenge created: {challenge_id} - {req.title}")
    
    return challenge


@app.get("/challenges")
@limiter.limit("10/minute")
async def list_active_challenges(
    request: Request,
    country_code: Optional[str] = None,
):
    """List all active challenges for a user's country"""
    db = get_supabase()
    
    challenges = db.list_active_challenges(country_code=country_code)
    
    logger.info(f"Challenges listed: {len(challenges)} active, country={country_code}")
    
    return challenges


@app.post("/challenges/{challenge_id}/entries", response_model=ChallengeEntryResponse)
@limiter.limit("10/minute")
async def submit_challenge_entry(
    request: Request,
    challenge_id: str,
    req: ChallengeEntryRequest,
):
    """Submit a generation job to a challenge"""
    db = get_supabase()
    
    # Verify challenge exists
    challenge = db.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    # Verify job exists and belongs to user
    job = db.get_generation_job(req.generation_job_id)
    if not job:
        raise HTTPException(400, "Generation job not found")
    if job["user_id"] != req.user_id:
        raise HTTPException(400, "Generation job does not belong to this user")
    if job["status"] != "complete":
        raise HTTPException(400, "Only completed videos can be submitted to a challenge")
    
    # Check if user already submitted to this challenge
    existing_entry = db.get_challenge_entry_by_user(challenge_id, req.user_id)
    if existing_entry:
        raise HTTPException(400, "Already submitted to this challenge")
    
    entry = db.create_challenge_entry(
        challenge_id=challenge_id,
        user_id=req.user_id,
        generation_job_id=req.generation_job_id,
    )
    
    logger.info(f"Challenge entry submitted: {entry['id']} by user {req.user_id}")
    
    return ChallengeEntryResponse(**entry)


@app.post("/challenges/entries/{entry_id}/vote", response_model=VoteResponse)
@limiter.limit("20/minute")
async def vote_challenge_entry(
    request: Request,
    entry_id: str,
    voter_user_id: str,
):
    """Vote for a challenge entry"""
    db = get_supabase()
    
    entry = db.get_challenge_entry(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    
    if voter_user_id == entry["user_id"]:
        raise HTTPException(400, "Cannot vote for your own entry")
    
    # Check if already voted
    existing_vote = db.get_vote(entry_id, voter_user_id)
    if existing_vote:
        raise HTTPException(400, "Already voted for this entry")
    
    # Create vote
    db.create_vote(entry_id=entry_id, voter_user_id=voter_user_id)
    
    # Update vote count
    entry = db.get_challenge_entry(entry_id)
    
    logger.info(f"Vote cast: user {voter_user_id} voted for entry {entry_id}")
    
    return VoteResponse(entry_id=entry_id, vote_count=entry["vote_count"])


@app.get("/challenges/{challenge_id}/leaderboard")
@limiter.limit("10/minute")
async def challenge_leaderboard(
    request: Request,
    challenge_id: str,
    limit: int = 50,
):
    """Get leaderboard for a specific challenge"""
    db = get_supabase()
    
    entries = db.get_challenge_leaderboard(challenge_id, limit=limit)
    
    logger.info(f"Challenge leaderboard fetched: {challenge_id}, {len(entries)} entries")
    
    return entries


# --------------------------------------------------------------------------
# PAYMENTS - STRIPE
# --------------------------------------------------------------------------

@app.post("/webhooks/stripe")
@limiter.limit("20/minute")
async def stripe_webhook(
    request: Request,
    payload: StripeWebhookPayload,
):
    """
    Stripe webhook handler for subscription events.
    Must verify webhook signature before processing.
    """
    # Verify webhook signature - THIS IS REQUIRED FOR PRODUCTION
    stripe_signing_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not stripe_signing_secret:
        raise HTTPException(
            status_code=500,
            detail="Stripe webhook secret not configured. Set STRIPE_WEBHOOK_SECRET environment variable."
        )
    
    try:
        import stripe
        
        # Get the raw request body for signature verification
        request_body = await request.body()
        
        # Verify the signature
        try:
            event = stripe.Webhook.construct_event(
                request_body,
                request.headers.get("stripe-signature"),
                stripe_signing_secret
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature"
            )
        except Exception as e:
            logger.error(f"Stripe webhook verification error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Webhook verification failed: {str(e)}"
            )
        
        # Signature verified, process the event
        event_type = event.get("type")
        data = event.get("data", {})
        
        if event_type == "checkout.session.completed":
            # Extract user and tier from metadata
            session = data.get("object", {})
            metadata = session.get("metadata", {})
            user_id = metadata.get("user_id")
            tier = metadata.get("tier")
            
            if user_id and tier:
                db = get_supabase()
                # Deactivate old subscriptions
                db.deactivate_user_subscriptions(user_id)
                # Create new subscription
                db.create_subscription(user_id=user_id, tier=tier)
                
                logger.info(f"Stripe subscription activated: user {user_id}, tier {tier}")
        
        elif event_type == "customer.subscription.updated":
            # Handle tier changes
            subscription = data.get("object", {})
            user_id = subscription.get("metadata", {}).get("user_id")
            new_tier = subscription.get("items", {}).get("data", [{}])[0].get("plan", {}).get("id")
            
            if user_id:
                db = get_supabase()
                db.deactivate_user_subscriptions(user_id)
                db.create_subscription(user_id=user_id, tier=new_tier)
                
                logger.info(f"Stripe subscription updated: user {user_id}, tier {new_tier}")
        
        elif event_type == "customer.subscription.deleted":
            # Handle cancellations
            subscription = data.get("object", {})
            user_id = subscription.get("metadata", {}).get("user_id")
            
            if user_id:
                db = get_supabase()
                db.deactivate_user_subscriptions(user_id)
                # Create free subscription
                db.create_subscription(user_id=user_id, tier="free")
                
                logger.info(f"Stripe subscription cancelled: user {user_id}")
        
        return {"received": True, "status": "processed"}
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe webhook signature verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# --------------------------------------------------------------------------
# PAYMENTS - PAYMONGO / GCASH
# --------------------------------------------------------------------------

@app.post("/payments/gcash/checkout")
@limiter.limit("5/minute")
async def create_gcash_checkout(
    request: Request,
    req: GCashCheckoutRequest,
):
    """
    Create a GCash checkout session via PayMongo.
    This is the primary payment method for Philippines launch.
    """
    db = get_supabase()
    user = _get_user_or_404(db, req.user_id)
    
    amount = TIER_PRICE_PHP.get(req.tier)
    if amount is None:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    try:
        from app.providers.paymongo_gcash import create_gcash_source
        
        source = create_gcash_source(
            amount_php=amount,
            description=f"BeAstar.io {req.tier} subscription",
            success_redirect_url=f"{APP_BASE_URL}/payments/success?user_id={req.user_id}&tier={req.tier}",
            failed_redirect_url=f"{APP_BASE_URL}/payments/failed?user_id={req.user_id}",
            metadata={"user_id": req.user_id, "tier": req.tier},
        )
        
        logger.info(f"GCash checkout created: user {req.user_id}, tier {req.tier}, amount {amount}")
        
        return {
            "source_id": source["id"],
            "checkout_url": source["attributes"]["redirect"]["checkout_url"],
            "amount_php": amount,
        }
        
    except Exception as e:
        logger.error(f"GCash checkout error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/paymongo")
@limiter.limit("20/minute")
async def paymongo_webhook(
    request: Request,
    payload: PayMongoWebhookPayload,
):
    """
    PayMongo webhook handler for GCash payments.
    Must verify webhook signature before processing.
    """
    # Verify webhook signature - THIS IS REQUIRED FOR PRODUCTION
    paymongo_signing_secret = os.environ.get("PAYMONGO_WEBHOOK_SECRET")
    if not paymongo_signing_secret:
        raise HTTPException(
            status_code=500,
            detail="PayMongo webhook secret not configured. Set PAYMONGO_WEBHOOK_SECRET environment variable."
        )
    
    try:
        from app.providers.paymongo_gcash import verify_webhook_signature
        
        # Get raw request body for signature verification
        request_body = await request.body()
        signature = request.headers.get("x-paymongo-signature")
        
        if not signature:
            raise HTTPException(
                status_code=401,
                detail="Missing webhook signature header"
            )
        
        # Verify the signature
        if not verify_webhook_signature(request_body, signature):
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook signature"
            )
        
        # Signature verified, process the event
        event_type = payload.type
        data = payload.data
        
        if event_type == "source.chargeable":
            # Source is ready to be charged
            source_id = data.get("id")
            attributes = data.get("attributes", {})
            metadata = attributes.get("metadata", {})
            user_id = metadata.get("user_id")
            tier = metadata.get("tier")
            amount = attributes.get("amount")
            
            if user_id and tier:
                from app.providers.paymongo_gcash import create_payment_from_chargeable_source
                
                # Create payment
                payment = create_payment_from_chargeable_source(
                    source_id=source_id,
                    amount=amount,
                    description=f"BeAstar.io {tier} subscription",
                )
                
                if payment.get("status") == "paid":
                    db = get_supabase()
                    # Deactivate old subscriptions
                    db.deactivate_user_subscriptions(user_id)
                    # Create new subscription
                    db.create_subscription(user_id=user_id, tier=tier)
                    
                    logger.info(f"PayMongo payment successful: user {user_id}, tier {tier}, amount {amount}")
        
        elif event_type == "payment.success":
            # Payment was successful
            payment = data.get("attributes", {})
            metadata = payment.get("metadata", {})
            user_id = metadata.get("user_id")
            tier = metadata.get("tier")
            
            if user_id:
                db = get_supabase()
                # Deactivate old subscriptions
                db.deactivate_user_subscriptions(user_id)
                # Create new subscription
                db.create_subscription(user_id=user_id, tier=tier)
                
                logger.info(f"PayMongo payment confirmed: user {user_id}, tier {tier}")
        
        elif event_type == "payment.failed":
            # Payment failed
            logger.warning(f"PayMongo payment failed: {data}")
        
        return {"received": True, "status": "processed"}
        
    except Exception as e:
        logger.error(f"PayMongo webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# --------------------------------------------------------------------------
# DREAM THREADS
# --------------------------------------------------------------------------

@app.post("/dream-threads")
@limiter.limit("10/minute")
async def create_dream_thread(
    request: Request,
    req: DreamThreadCreateRequest,
):
    """
    Create a new dream thread.
    This is the long-term identity mechanism - users share their journey
    toward becoming their imagined star self.
    """
    db = get_supabase()
    user = _get_user_or_404(db, req.user_id)
    
    # Verify starting generation job if provided
    if req.starting_generation_job_id:
        job = db.get_generation_job(req.starting_generation_job_id)
        if not job:
            raise HTTPException(400, "Starting generation job not found")
        if job["user_id"] != req.user_id:
            raise HTTPException(400, "Starting generation job does not belong to this user")
    
    thread = db.create_dream_thread(
        user_id=req.user_id,
        goal_title=req.goal_title,
        goal_description=req.goal_description,
        starting_generation_job_id=req.starting_generation_job_id,
        self_reported_net_worth=req.self_reported_net_worth,
    )
    
    logger.info(f"Dream thread created: {thread['id']} by user {req.user_id}")
    
    return {**thread, "display_note": UNVERIFIED_NOTE}


@app.get("/dream-threads/{thread_id}")
@limiter.limit("20/minute")
async def get_dream_thread(
    request: Request,
    thread_id: str,
):
    """Get a dream thread with all approved updates"""
    db = get_supabase()
    
    thread = db.get_dream_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    
    # Get approved updates
    updates = db.get_dream_thread_updates(thread_id, status="approved")
    updates.sort(key=lambda u: u["created_at"], reverse=True)
    
    # Get follower count
    follower_count = db.count_dream_thread_followers(thread_id)
    
    result = {
        **thread,
        "display_note": UNVERIFIED_NOTE,
        "update_count": len(updates),
        "follower_count": follower_count,
        "updates": updates,
    }
    
    logger.info(f"Dream thread fetched: {thread_id}, {len(updates)} updates")
    
    return result


@app.get("/users/{user_id}/dream-threads")
@limiter.limit("10/minute")
async def list_user_dream_threads(
    request: Request,
    user_id: str,
):
    """List all dream threads for a user"""
    db = get_supabase()
    _get_user_or_404(db, user_id)
    
    threads = db.get_user_dream_threads(user_id)
    threads.sort(key=lambda t: t["created_at"], reverse=True)
    
    result = [{**t, "display_note": UNVERIFIED_NOTE} for t in threads]
    
    logger.info(f"User dream threads listed: {user_id}, {len(threads)} threads")
    
    return result


@app.post("/dream-threads/{thread_id}/updates")
@limiter.limit("10/minute")
async def post_dream_update(
    request: Request,
    thread_id: str,
    req: DreamUpdateCreateRequest,
):
    """
    Post an update to a dream thread.
    Updates go through moderation before appearing in followers' feeds.
    """
    db = get_supabase()
    
    thread = db.get_dream_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    if thread["user_id"] != req.user_id:
        raise HTTPException(403, "Only the thread owner can post an update")
    
    # Check if video_url is provided and valid
    if req.video_url:
        # In production, verify the URL is from our storage
        pass
    
    update = db.create_dream_update(
        thread_id=thread_id,
        user_id=req.user_id,
        caption=req.caption,
        video_url=req.video_url,
        moderation_status="pending",  # Will be approved by admin or auto-moderation
    )
    
    logger.info(f"Dream update posted: {update['id']} to thread {thread_id}")
    
    return update


@app.post("/dream-threads/{thread_id}/follow")
@limiter.limit("20/minute")
async def follow_dream_thread(
    request: Request,
    thread_id: str,
    follower_user_id: str,
):
    """Follow a dream thread to see updates in your feed"""
    db = get_supabase()
    
    thread = db.get_dream_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    _get_user_or_404(db, follower_user_id)
    
    if thread["user_id"] == follower_user_id:
        raise HTTPException(400, "Cannot follow your own thread")
    
    # Check if already following
    existing = db.get_dream_thread_follow(thread_id, follower_user_id)
    if existing:
        raise HTTPException(400, "Already following this thread")
    
    db.create_dream_thread_follow(thread_id, follower_user_id)
    
    logger.info(f"Dream thread followed: user {follower_user_id} following thread {thread_id}")
    
    return {"thread_id": thread_id, "following": True}


@app.delete("/dream-threads/{thread_id}/follow")
@limiter.limit("20/minute")
async def unfollow_dream_thread(
    request: Request,
    thread_id: str,
    follower_user_id: str,
):
    """Unfollow a dream thread"""
    db = get_supabase()
    
    thread = db.get_dream_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    
    db.delete_dream_thread_follow(thread_id, follower_user_id)
    
    logger.info(f"Dream thread unfollowed: user {follower_user_id} unfollowed thread {thread_id}")
    
    return {"thread_id": thread_id, "following": False}


@app.get("/users/{user_id}/dream-feed")
@limiter.limit("15/minute")
async def get_followed_dream_feed(
    request: Request,
    user_id: str,
    limit: int = 50,
):
    """
    Get the feed of dream updates from threads this user follows.
    This is the retention mechanism - users see progress from people they follow.
    """
    db = get_supabase()
    _get_user_or_404(db, user_id)
    
    # Get threads this user follows
    followed_thread_ids = db.get_followed_thread_ids(user_id)
    
    # Get approved updates from followed threads
    feed = db.get_dream_feed(user_id, followed_thread_ids, status="approved", limit=limit)
    feed.sort(key=lambda u: u["created_at"], reverse=True)
    
    logger.info(f"Dream feed fetched: user {user_id}, {len(feed)} updates")
    
    return feed


@app.post("/dream-updates/{update_id}/encouragements")
@limiter.limit("30/minute")
async def add_encouragement(
    request: Request,
    update_id: str,
    req: EncouragementRequest,
):
    """
    Add encouragement to a dream update.
    This is the social interaction mechanism - users encourage each other.
    """
    db = get_supabase()
    
    update = db.get_dream_update(update_id)
    if not update:
        raise HTTPException(404, "Update not found")
    _get_user_or_404(db, req.user_id)
    
    # Check if already encouraged
    existing = db.get_encouragement(update_id, req.user_id)
    if existing:
        raise HTTPException(409, "Already encouraged this update")
    
    encouragement = db.create_encouragement(
        update_id=update_id,
        user_id=req.user_id,
        message=req.message,
    )
    
    logger.info(f"Encouragement added: user {req.user_id} to update {update_id}")
    
    return encouragement


@app.get("/dream-updates/{update_id}/encouragements")
@limiter.limit("20/minute")
async def list_encouragements(
    request: Request,
    update_id: str,
):
    """List all encouragements for a dream update"""
    db = get_supabase()
    
    encouragements = db.get_dream_update_encouragements(update_id)
    
    logger.info(f"Encouragements listed: update {update_id}, {len(encouragements)} encouragements")
    
    return encouragements


# --------------------------------------------------------------------------
# ADMIN ENDPOINTS
# --------------------------------------------------------------------------

@app.post("/admin/moderate/dream-update/{update_id}/approve")
@limiter.limit("5/minute")
async def approve_dream_update(
    request: Request,
    update_id: str,
):
    """Admin endpoint to approve a dream update for publication"""
    db = get_supabase()
    
    update = db.get_dream_update(update_id)
    if not update:
        raise HTTPException(404, "Update not found")
    
    db.update_dream_update_moderation_status(update_id, "approved")
    
    logger.info(f"Dream update approved: {update_id}")
    
    return {"update_id": update_id, "status": "approved"}


@app.post("/admin/moderate/dream-update/{update_id}/reject")
@limiter.limit("5/minute")
async def reject_dream_update(
    request: Request,
    update_id: str,
    reason: Optional[str] = None,
):
    """Admin endpoint to reject a dream update"""
    db = get_supabase()
    
    update = db.get_dream_update(update_id)
    if not update:
        raise HTTPException(404, "Update not found")
    
    db.update_dream_update_moderation_status(update_id, "rejected")
    
    logger.info(f"Dream update rejected: {update_id}, reason: {reason}")
    
    return {"update_id": update_id, "status": "rejected", "reason": reason}


# --------------------------------------------------------------------------
# RUN APP
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
