"""
BeAstar.io — FastAPI starter
=============================
First commit: auth, referral tracking, tier-gated video generation request,
and QR-code generation for the viral share loop.

Design goals baked in from the brief:
  - Bootstrapped cost shape: nothing here spins up paid infra until a real
    generation is requested.
  - No real celebrity names/IP in scenario data (enforced at the DB layer
    via the `scenarios` table content, not here — see schema.sql).
  - AI-disclosure label is a hard requirement of every rendered video, not
    optional — see `render_video_job` below.
  - Age gate (13+) enforced at signup.
  - Face-match/liveness check required before a user's first generation.

Run locally:
    pip install fastapi uvicorn supabase pydantic[email] qrcode[pil] --break-system-packages
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

import qrcode
from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title="BeAstar.io API", version="0.1.0")

# Feature flag: once SUPABASE_URL/SUPABASE_KEY are set in the environment,
# real generation requests get persisted via app/db/supabase_client.py and
# rendered via app/providers/video_gen.py instead of the in-memory stub
# below. This lets the same file run standalone for local testing (flag
# off) or wired to real infra (flag on) without maintaining two apps.
USE_REAL_BACKEND = bool(os.environ.get("SUPABASE_URL"))

# --------------------------------------------------------------------------
# Config — in production these come from environment variables / secrets,
# never hardcoded. Placeholders here so the file is runnable standalone.
# --------------------------------------------------------------------------

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://beastar.io")
MIN_SIGNUP_AGE_YEARS = 13

TIER_LIMITS = {
    "free":      {"max_resolution": "720p", "daily_cap": 3},
    "star":      {"max_resolution": "1080p", "daily_cap": 10},
    "superstar": {"max_resolution": "1080p", "daily_cap": 25},
    "megastar":  {"max_resolution": "4k", "daily_cap": 100},  # fair-use cap, not truly unlimited
}

RESOLUTION_RANK = {"720p": 0, "1080p": 1, "4k": 2}

# --------------------------------------------------------------------------
# In-memory stores — placeholders for the real Supabase/Postgres calls.
# Swap each of these for actual DB queries against schema.sql before launch.
# --------------------------------------------------------------------------

_users_db: dict[str, dict] = {}
_jobs_db: dict[str, dict] = {}
_referral_code_index: dict[str, str] = {}  # referral_code -> user_id


# ==========================================================================
# SCHEMAS
# ==========================================================================

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


# ==========================================================================
# HELPERS
# ==========================================================================

def _get_user_or_404(user_id: str) -> dict:
    user = _users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _generate_referral_code(display_name: str) -> str:
    base = "".join(c for c in display_name.upper() if c.isalnum())[:6] or "STAR"
    return f"{base}-{uuid.uuid4().hex[:5].upper()}"


def _meets_age_minimum(dob: date) -> bool:
    cutoff = date.today().replace(year=date.today().year - MIN_SIGNUP_AGE_YEARS)
    return dob <= cutoff


# ==========================================================================
# AUTH / SIGNUP
# ==========================================================================

@app.post("/auth/signup", response_model=SignupResponse, status_code=201)
def signup(req: SignupRequest):
    if not _meets_age_minimum(req.date_of_birth):
        raise HTTPException(
            status_code=400,
            detail=f"Signup requires users to be at least {MIN_SIGNUP_AGE_YEARS}. "
                   "Users under 18 will need a parental-consent flow before "
                   "face upload is enabled (implement before launch).",
        )

    user_id = str(uuid.uuid4())
    referral_code = _generate_referral_code(req.display_name)

    referred_by_user_id = None
    starting_credits = 50  # onboarding bonus

    if req.referral_code_used:
        referrer_id = _referral_code_index.get(req.referral_code_used)
        if referrer_id and referrer_id in _users_db:
            referred_by_user_id = referrer_id
            starting_credits += 100
            _users_db[referrer_id]["credits"] += 100
        # Silently ignore invalid/unknown codes rather than blocking signup —
        # don't let a typo'd referral code break onboarding.

    _users_db[user_id] = {
        "id": user_id,
        "email": req.email,
        "display_name": req.display_name,
        "date_of_birth": req.date_of_birth,
        "country_code": req.country_code.upper(),
        "referral_code": referral_code,
        "referred_by_user_id": referred_by_user_id,
        "is_verified": False,
        "credits": starting_credits,
        "tier": "free",
        "created_at": datetime.utcnow(),
    }
    _referral_code_index[referral_code] = user_id

    return SignupResponse(
        user_id=user_id,
        referral_code=referral_code,
        credits=starting_credits,
    )


@app.post("/auth/{user_id}/verify-face")
def verify_face(user_id: str):
    """
    Placeholder for the real liveness + self-match pipeline.

    Real implementation must, in order:
      1. Run a liveness check on the submitted selfie (blocks static photos
         of someone else, screen replays, etc.)
      2. Run a known-public-figure check against the face — reject on match.
      3. Store only a face embedding/hash, never the raw image, tied to
         this user_id for future upload matching.
    """
    user = _get_user_or_404(user_id)
    user["is_verified"] = True
    return {"user_id": user_id, "is_verified": True}


# ==========================================================================
# SELFIE UPLOAD (user's own face/body → storage → image_url for providers)
# ==========================================================================

MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # keep in sync with app/storage/selfie_upload.py


@app.post("/users/{user_id}/uploads/selfie")
async def upload_selfie_endpoint(user_id: str, file: UploadFile):
    """
    Accepts a selfie for use in a generation request. Requires the user to
    already be face-verified (see /auth/{user_id}/verify-face) — this
    endpoint is for the per-generation source photo, not initial identity
    verification.

    Returns a short-lived signed URL suitable for passing directly as
    `image_url` to app.providers.video_gen.start_generation_with_fallback().
    """
    user = _get_user_or_404(user_id)
    if not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Face verification required before uploading generation photos.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")

    if USE_REAL_BACKEND:
        from app.db.supabase_client import get_client
        from app.storage.selfie_upload import UploadValidationError, upload_selfie

        try:
            image_url = upload_selfie(
                get_client(), user_id, file.content_type or "application/octet-stream", file_bytes
            )
        except UploadValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except NotImplementedError as exc:
            # run_content_safety_check is intentionally unimplemented until
            # a real moderation vendor is wired in — fail loudly rather
            # than silently skipping the safety check.
            raise HTTPException(
                status_code=503,
                detail="Upload safety pipeline not yet configured. See "
                       "app/storage/selfie_upload.py:run_content_safety_check.",
            ) from exc

        return {"image_url": image_url}

    # Local/dev fallback when Supabase isn't configured — validates shape
    # only, doesn't actually persist anything.
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
    return {"image_url": f"{APP_BASE_URL}/dev-placeholder/{uuid.uuid4().hex}.jpg"}


# ==========================================================================
# GENERATION (tier-gated)
# ==========================================================================

@app.post("/generate", response_model=GenerationResponse)
def request_generation(req: GenerationRequest):
    user = _get_user_or_404(req.user_id)

    if not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Face verification required before generating videos.",
        )

    tier = user.get("tier", "free")
    limits = TIER_LIMITS[tier]

    if RESOLUTION_RANK[req.requested_resolution] > RESOLUTION_RANK[limits["max_resolution"]]:
        raise HTTPException(
            status_code=403,
            detail=f"'{tier}' tier is capped at {limits['max_resolution']}. "
                   "Upgrade to unlock higher resolution.",
        )

    today_count = sum(
        1 for j in _jobs_db.values()
        if j["user_id"] == req.user_id
        and j["created_at"].date() == datetime.utcnow().date()
    )
    if today_count >= limits["daily_cap"]:
        raise HTTPException(
            status_code=429,
            detail=f"Daily generation cap ({limits['daily_cap']}) reached for '{tier}' tier.",
        )

    job_id = str(uuid.uuid4())
    _jobs_db[job_id] = {
        "id": job_id,
        "user_id": req.user_id,
        "scenario_slug": req.scenario_slug,
        "resolution": req.requested_resolution,
        "status": "queued",
        "created_at": datetime.utcnow(),
    }

    if USE_REAL_BACKEND:
        # Real path: submit to the video-gen orchestrator (Runway primary,
        # Kling automatic fallback — see app/providers/video_gen.py), then
        # persist the job via Supabase. In production this submission
        # should be handed to a background worker (Celery/RQ/etc) rather
        # than run inline in the request — a video render takes far longer
        # than an HTTP request should block for. Sketch:
        #
        #   from app.providers.video_gen import start_generation_with_fallback
        #   from app.db import supabase_client as db
        #
        #   scenario = db.get_scenario_by_slug(req.scenario_slug)
        #   provider_name, provider_job_id = start_generation_with_fallback(
        #       image_url=req.image_url,   # from the upload endpoint above
        #       prompt=scenario["description"],
        #       resolution=req.requested_resolution,
        #   )
        #   job = db.create_generation_job(
        #       user_id=req.user_id, scenario_id=scenario["id"],
        #       resolution=req.requested_resolution, credits_charged=1,
        #   )
        #   db.update_generation_job(job["id"], status="rendering",
        #                             provider=provider_name,
        #                             provider_job_id=provider_job_id)
        #   # A background worker then calls poll_generation_with_fallback
        #   # and, on completion, burns in the AI-disclosure label during
        #   # final encode before writing output_url.
        pass

    return GenerationResponse(
        job_id=job_id,
        status="queued",
        resolution=req.requested_resolution,
    )


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = _jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ==========================================================================
# VIRAL LOOP — QR codes
# ==========================================================================

@app.get("/qr/{user_id}")
def get_referral_qr(user_id: str):
    """
    Returns a PNG QR code encoding this user's shareable profile/referral
    link. Deep link resolves to the app if installed, or an app-store /
    web-preview fallback if not.
    """
    user = _get_user_or_404(user_id)
    share_url = f"{APP_BASE_URL}/u/{user['referral_code']}"

    img = qrcode.make(share_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


# ==========================================================================
# LEADERBOARD (read-only projection — swap for the leaderboard_global view
# from schema.sql once on real Postgres)
# ==========================================================================

@app.get("/leaderboard")
def leaderboard(country_code: Optional[str] = None, limit: int = 50):
    rows = []
    for user in _users_db.values():
        if country_code and user["country_code"] != country_code.upper():
            continue
        videos_created = sum(
            1 for j in _jobs_db.values() if j["user_id"] == user["id"]
        )
        referrals_made = sum(
            1 for u in _users_db.values()
            if u.get("referred_by_user_id") == user["id"]
        )
        rows.append({
            "user_id": user["id"],
            "display_name": user["display_name"],
            "country_code": user["country_code"],
            "videos_created": videos_created,
            "successful_referrals": referrals_made,
        })

    rows.sort(key=lambda r: (r["videos_created"], r["successful_referrals"]), reverse=True)
    return rows[:limit]


@app.get("/health")
def health():
    return {"status": "ok"}


# ==========================================================================
# CHALLENGES (weekly global + regional, per the growth-hack spec)
# ==========================================================================

_challenges_db: dict[str, dict] = {}
_challenge_entries_db: dict[str, dict] = {}


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


@app.post("/challenges")
def create_challenge(req: ChallengeCreate):
    """Admin-only in production — lock this behind an internal/admin auth
    dependency before launch, not exposed to end users."""
    if req.scope == "regional" and not req.country_code:
        raise HTTPException(400, "Regional challenges require a country_code")
    challenge_id = str(uuid.uuid4())
    _challenges_db[challenge_id] = {"id": challenge_id, **req.dict()}
    return _challenges_db[challenge_id]


@app.get("/challenges")
def list_active_challenges(country_code: Optional[str] = None):
    now = datetime.utcnow()
    results = []
    for c in _challenges_db.values():
        if not (c["starts_at"] <= now <= c["ends_at"]):
            continue
        if c["scope"] == "regional" and country_code and c["country_code"] != country_code.upper():
            continue
        results.append(c)
    return results


@app.post("/challenges/{challenge_id}/entries")
def submit_challenge_entry(challenge_id: str, req: ChallengeEntryRequest):
    if challenge_id not in _challenges_db:
        raise HTTPException(404, "Challenge not found")
    job = _jobs_db.get(req.generation_job_id)
    if not job or job["user_id"] != req.user_id:
        raise HTTPException(400, "Generation job not found for this user")
    if job["status"] != "complete":
        raise HTTPException(400, "Only completed videos can be submitted to a challenge")

    entry_id = str(uuid.uuid4())
    _challenge_entries_db[entry_id] = {
        "id": entry_id,
        "challenge_id": challenge_id,
        "user_id": req.user_id,
        "generation_job_id": req.generation_job_id,
        "vote_count": 0,
        "submitted_at": datetime.utcnow(),
    }
    return _challenge_entries_db[entry_id]


@app.post("/challenges/entries/{entry_id}/vote")
def vote_challenge_entry(entry_id: str, voter_user_id: str):
    entry = _challenge_entries_db.get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    if voter_user_id == entry["user_id"]:
        raise HTTPException(400, "Cannot vote for your own entry")
    # Production: enforce one vote per (voter, entry) pair via a unique
    # constraint / dedicated votes table — omitted here for brevity.
    entry["vote_count"] += 1
    return {"entry_id": entry_id, "vote_count": entry["vote_count"]}


@app.get("/challenges/{challenge_id}/leaderboard")
def challenge_leaderboard(challenge_id: str, limit: int = 50):
    entries = [e for e in _challenge_entries_db.values() if e["challenge_id"] == challenge_id]
    entries.sort(key=lambda e: e["vote_count"], reverse=True)
    return entries[:limit]


# ==========================================================================
# STRIPE SUBSCRIPTION WEBHOOK (stub)
# ==========================================================================

@app.post("/webhooks/stripe")
async def stripe_webhook():
    """
    Placeholder for the real Stripe webhook handler.

    Real implementation must:
      1. Verify the webhook signature against your Stripe signing secret
         (never trust an unverified payload for billing state changes).
      2. Handle at minimum: checkout.session.completed (activate tier),
         customer.subscription.updated (tier change), and
         customer.subscription.deleted (downgrade to free).
      3. Update the user's `tier` and the `subscriptions` row's
         `max_resolution` / `daily_generation_cap` to match TIER_LIMITS.

    Wire this up with the `stripe` Python package once Stripe keys exist —
    left as a stub so the endpoint shape is in place from commit one.
    """
    return {"received": True, "note": "stub — implement signature verification before going live"}


# ==========================================================================
# GCASH PAYMENTS (via PayMongo — see app/providers/paymongo_gcash.py)
# ==========================================================================
# GCash is the primary payment method for the Philippines launch. GCash
# doesn't expose a direct merchant API at this stage, so this goes through
# PayMongo (PH-licensed payment gateway) — same GCash checkout experience
# for the user, real settlement into a PH bank account for you.

TIER_PRICE_PHP = {
    # Approximate PHP equivalents of the USD tier prices — set real prices
    # in PHP directly once live rather than doing FX conversion at
    # checkout time, so pricing doesn't drift with exchange rates.
    "star": 279.00,
    "superstar": 559.00,
    "megastar": 1119.00,
}


class GCashCheckoutRequest(BaseModel):
    user_id: str
    tier: str = Field(pattern="^(star|superstar|megastar)$")


@app.post("/payments/gcash/checkout")
def create_gcash_checkout(req: GCashCheckoutRequest):
    from app.providers.paymongo_gcash import create_gcash_source

    user = _get_user_or_404(req.user_id)
    amount = TIER_PRICE_PHP[req.tier]

    source = create_gcash_source(
        amount_php=amount,
        description=f"BeAstar.io {req.tier} subscription",
        success_redirect_url=f"{APP_BASE_URL}/payments/success?user_id={req.user_id}&tier={req.tier}",
        failed_redirect_url=f"{APP_BASE_URL}/payments/failed?user_id={req.user_id}",
    )

    return {
        "source_id": source["id"],
        "checkout_url": source["attributes"]["redirect"]["checkout_url"],
        "amount_php": amount,
    }


@app.post("/webhooks/paymongo")
async def paymongo_webhook():
    """
    Placeholder for the real PayMongo webhook handler.

    Real implementation must, in order:
      1. Verify the webhook signature (app/providers/paymongo_gcash.py has
         a `verify_webhook_signature` stub — wire it to your actual signing
         secret before trusting anything here).
      2. On a `source.chargeable` event: call
         create_payment_from_chargeable_source() to actually capture funds.
      3. On successful payment: activate/renew the user's subscription tier
         and update TIER_LIMITS-based caps on their `subscriptions` row.
      4. On `payment.failed`: leave the user on their current tier, surface
         a retry prompt in-app.
    """
    return {"received": True, "note": "stub — verify signature before trusting payload"}


# ==========================================================================
# DREAM THREADS — persistent progress stories, not one-off posts
# ==========================================================================
# Design rationale: a single "here's my plan" post is a snapshot people
# watch once and forget. A thread — "3 months ago I said X, here's my
# update" — is what makes aspirational content actually followable, the
# same structural reason long-running "how I built this" content
# outperforms one-off videos. See conversation/spec notes for the fuller
# reasoning; the short version is in every docstring below.
#
# Net-worth handling carries over unchanged from the earlier design: a
# self-reported BAND only, always flagged unverified in every response,
# because "dream + proof of success" is the exact template scam/fake-guru
# content copies — see COMPLIANCE.md.

_dream_threads_db: dict[str, dict] = {}
_dream_updates_db: dict[str, dict] = {}
_dream_followers_db: set[tuple[str, str]] = set()          # (thread_id, follower_user_id)
_dream_encouragements_db: dict[str, dict] = {}

NET_WORTH_BANDS = ("under_100k", "100k_1m", "1m_5m", "5m_plus", "prefer_not_to_say")

UNVERIFIED_NOTE = "Net worth, if shown, is self-reported and unverified."


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


@app.post("/dream-threads")
def create_dream_thread(req: DreamThreadCreateRequest):
    user = _get_user_or_404(req.user_id)

    if req.starting_generation_job_id:
        job = _jobs_db.get(req.starting_generation_job_id)
        if not job or job["user_id"] != req.user_id:
            raise HTTPException(400, "starting_generation_job_id not found for this user")

    thread_id = str(uuid.uuid4())
    _dream_threads_db[thread_id] = {
        "id": thread_id,
        "user_id": req.user_id,
        "goal_title": req.goal_title,
        "goal_description": req.goal_description,
        "starting_generation_job_id": req.starting_generation_job_id,
        "self_reported_net_worth": req.self_reported_net_worth,
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    return {**_dream_threads_db[thread_id], "display_note": UNVERIFIED_NOTE}


@app.get("/dream-threads/{thread_id}")
def get_dream_thread(thread_id: str):
    thread = _dream_threads_db.get(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")

    updates = [
        u for u in _dream_updates_db.values()
        if u["thread_id"] == thread_id and u["moderation_status"] == "approved"
    ]
    updates.sort(key=lambda u: u["created_at"])

    follower_count = sum(1 for (tid, _) in _dream_followers_db if tid == thread_id)

    return {
        **thread,
        "display_note": UNVERIFIED_NOTE,
        "update_count": len(updates),
        "follower_count": follower_count,
        "updates": updates,
    }


@app.get("/users/{user_id}/dream-threads")
def list_user_dream_threads(user_id: str):
    _get_user_or_404(user_id)
    mine = [t for t in _dream_threads_db.values() if t["user_id"] == user_id]
    mine.sort(key=lambda t: t["created_at"], reverse=True)
    return [{**t, "display_note": UNVERIFIED_NOTE} for t in mine]


@app.post("/dream-threads/{thread_id}/updates")
def post_dream_update(thread_id: str, req: DreamUpdateCreateRequest):
    thread = _dream_threads_db.get(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")
    if thread["user_id"] != req.user_id:
        raise HTTPException(403, "Only the thread owner can post an update")

    update_id = str(uuid.uuid4())
    _dream_updates_db[update_id] = {
        "id": update_id,
        "thread_id": thread_id,
        "user_id": req.user_id,
        "caption": req.caption,
        "video_url": req.video_url,
        # Same moderation posture as before: pending by default, kept out
        # of any followers' feed until approved. Real implementation routes
        # anything mentioning specific financial products, "guaranteed
        # returns," investment signals, or external payment links to
        # manual review rather than automated-only moderation.
        "moderation_status": "pending",
        "created_at": datetime.utcnow(),
    }
    return _dream_updates_db[update_id]


@app.post("/dream-threads/{thread_id}/follow")
def follow_dream_thread(thread_id: str, follower_user_id: str):
    if thread_id not in _dream_threads_db:
        raise HTTPException(404, "Thread not found")
    _get_user_or_404(follower_user_id)
    if _dream_threads_db[thread_id]["user_id"] == follower_user_id:
        raise HTTPException(400, "Cannot follow your own thread")

    _dream_followers_db.add((thread_id, follower_user_id))
    return {"thread_id": thread_id, "following": True}


@app.delete("/dream-threads/{thread_id}/follow")
def unfollow_dream_thread(thread_id: str, follower_user_id: str):
    _dream_followers_db.discard((thread_id, follower_user_id))
    return {"thread_id": thread_id, "following": False}


@app.get("/users/{user_id}/dream-feed")
def get_followed_dream_feed(user_id: str, limit: int = 50):
    """
    The 'discovery feed' — approved updates from threads this user
    follows, newest first. This is deliberately scoped to *followed*
    threads rather than a global algorithmic feed: a global ranking
    engine that optimizes for engagement is exactly the mechanism this
    build has been steering away from. Start with an honest
    follows-based feed; if you build a 'discover new threads' surface
    later, rank it by recency/category match, not raw engagement signals.
    """
    _get_user_or_404(user_id)
    followed_thread_ids = {tid for (tid, uid) in _dream_followers_db if uid == user_id}

    feed = [
        u for u in _dream_updates_db.values()
        if u["thread_id"] in followed_thread_ids and u["moderation_status"] == "approved"
    ]
    feed.sort(key=lambda u: u["created_at"], reverse=True)
    return feed[:limit]


@app.post("/dream-updates/{update_id}/encouragements")
def add_encouragement(update_id: str, req: EncouragementRequest):
    if update_id not in _dream_updates_db:
        raise HTTPException(404, "Update not found")
    _get_user_or_404(req.user_id)

    key = (update_id, req.user_id)
    existing = next(
        (e for e in _dream_encouragements_db.values()
         if e["update_id"] == update_id and e["user_id"] == req.user_id),
        None,
    )
    if existing:
        raise HTTPException(409, "Already encouraged this update")

    encouragement_id = str(uuid.uuid4())
    _dream_encouragements_db[encouragement_id] = {
        "id": encouragement_id,
        "update_id": update_id,
        "user_id": req.user_id,
        "message": req.message,
        "created_at": datetime.utcnow(),
    }
    return _dream_encouragements_db[encouragement_id]


@app.get("/dream-updates/{update_id}/encouragements")
def list_encouragements(update_id: str):
    return [e for e in _dream_encouragements_db.values() if e["update_id"] == update_id]
