"""
BeAstar.io - Complete Supabase Data Access Layer
================================================
Production-ready CRUD operations for all database tables matching schema.sql.

Features:
- Complete CRUD for users, subscriptions, generation jobs, dream threads, challenges
- Atomic operations via RPC functions
- Referral tracking
- Leaderboard queries
- Daily usage tracking
- Content moderation support
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


def get_client() -> Client:
    """Get or create Supabase client with service role key"""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        _client = create_client(url, key)
    return _client


# ==========================================================================
# USERS
# ==========================================================================

def create_user(
    email: str,
    display_name: str,
    date_of_birth: date,
    country_code: str,
    referral_code: str,
    referred_by_user_id: Optional[str],
    starting_credits: int,
) -> dict:
    """Create a new user"""
    db = get_client()
    result = db.table("users").insert({
        "email": email,
        "display_name": display_name,
        "date_of_birth": date_of_birth.isoformat(),
        "country_code": country_code.upper(),
        "referral_code": referral_code,
        "referred_by_user_id": referred_by_user_id,
        "credits": starting_credits,
        "is_verified": False,
    }).execute()
    return result.data[0]


def get_user(user_id: str) -> Optional[dict]:
    """Get user by ID"""
    db = get_client()
    result = db.table("users").select("*").eq("id", user_id).limit(1).execute()
    return result.data[0] if result.data else None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email"""
    db = get_client()
    result = db.table("users").select("*").eq("email", email).limit(1).execute()
    return result.data[0] if result.data else None


def get_user_by_referral_code(referral_code: str) -> Optional[dict]:
    """Get user by referral code"""
    db = get_client()
    result = db.table("users").select("*").eq("referral_code", referral_code).limit(1).execute()
    return result.data[0] if result.data else None


def update_user(user_id: str, **kwargs) -> Optional[dict]:
    """Update user fields"""
    db = get_client()
    result = db.table("users").update(kwargs).eq("id", user_id).execute()
    return result.data[0] if result.data else None


def increment_credits(user_id: str, amount: int) -> None:
    """Atomically increment user's credits"""
    db = get_client()
    db.rpc("increment_credits", {"uid": user_id, "amt": amount}).execute()


def mark_user_verified(user_id: str, face_embedding_id: str) -> dict:
    """Mark user as verified with face embedding ID"""
    db = get_client()
    result = db.table("users").update({
        "is_verified": True,
        "face_embedding_id": face_embedding_id,
    }).eq("id", user_id).execute()
    return result.data[0]


def get_user_tier(user_id: str) -> str:
    """Get user's current active subscription tier"""
    db = get_client()
    result = (
        db.table("subscriptions")
        .select("tier")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0]["tier"] if result.data else "free"


# ==========================================================================
# SUBSCRIPTIONS
# ==========================================================================

def create_subscription(user_id: str, tier: str = "free") -> dict:
    """Create a new subscription for user"""
    db = get_client()
    
    # Get tier limits
    tier_limits = {
        "free": {"max_resolution": "720p", "daily_cap": 3},
        "star": {"max_resolution": "1080p", "daily_cap": 10},
        "superstar": {"max_resolution": "1080p", "daily_cap": 25},
        "megastar": {"max_resolution": "4k", "daily_cap": 100},
    }
    limits = tier_limits.get(tier, tier_limits["free"])
    
    # Deactivate old subscriptions
    deactivate_user_subscriptions(user_id)
    
    result = db.table("subscriptions").insert({
        "user_id": user_id,
        "tier": tier,
        "max_resolution": limits["max_resolution"],
        "daily_generation_cap": limits["daily_cap"],
        "is_active": True,
    }).execute()
    return result.data[0]


def deactivate_user_subscriptions(user_id: str) -> None:
    """Deactivate all subscriptions for a user"""
    db = get_client()
    db.table("subscriptions").update({"is_active": False}).eq("user_id", user_id).execute()


def get_user_subscription(user_id: str) -> Optional[dict]:
    """Get user's active subscription"""
    db = get_client()
    result = (
        db.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ==========================================================================
# SCENARIOS
# ==========================================================================

def get_scenario_by_slug(slug: str) -> Optional[dict]:
    """Get scenario by slug"""
    db = get_client()
    result = db.table("scenarios").select("*").eq("slug", slug).eq("is_active", True).limit(1).execute()
    return result.data[0] if result.data else None


def get_all_active_scenarios() -> list[dict]:
    """Get all active scenarios"""
    db = get_client()
    result = db.table("scenarios").select("*").eq("is_active", True).execute()
    return result.data or []


# ==========================================================================
# GENERATION JOBS
# ==========================================================================

def create_generation_job(
    user_id: str,
    scenario_id: str,
    resolution: str,
    credits_charged: int,
) -> dict:
    """Create a new generation job"""
    db = get_client()
    result = db.table("generation_jobs").insert({
        "user_id": user_id,
        "scenario_id": scenario_id,
        "resolution": resolution,
        "status": "queued",
        "credits_charged": credits_charged,
    }).execute()
    return result.data[0]


def get_generation_job(job_id: str) -> Optional[dict]:
    """Get generation job by ID"""
    db = get_client()
    result = db.table("generation_jobs").select("*").eq("id", job_id).limit(1).execute()
    return result.data[0] if result.data else None


def update_generation_job(
    job_id: str,
    status: str,
    provider: Optional[str] = None,
    provider_job_id: Optional[str] = None,
    output_url: Optional[str] = None,
    render_cost_usd: Optional[float] = None,
) -> dict:
    """Update generation job status and metadata"""
    db = get_client()
    update = {"status": status}
    if provider is not None:
        update["provider"] = provider
    if provider_job_id is not None:
        update["provider_job_id"] = provider_job_id
    if output_url is not None:
        update["output_url"] = output_url
    if render_cost_usd is not None:
        update["render_cost_usd"] = render_cost_usd
    if status in ("complete", "failed"):
        update["completed_at"] = datetime.utcnow().isoformat()

    result = db.table("generation_jobs").update(update).eq("id", job_id).execute()
    return result.data[0]


def count_generations_today(user_id: str) -> int:
    """Count how many generations user has done today"""
    db = get_client()
    today = date.today().isoformat()
    result = (
        db.table("daily_usage")
        .select("generations_used")
        .eq("user_id", user_id)
        .eq("usage_date", today)
        .limit(1)
        .execute()
    )
    return result.data[0]["generations_used"] if result.data else 0


def increment_daily_usage(user_id: str) -> None:
    """Increment user's daily generation usage"""
    db = get_client()
    db.rpc("increment_daily_usage", {"uid": user_id}).execute()


def get_user_generation_jobs(user_id: str, limit: int = 50) -> list[dict]:
    """Get all generation jobs for a user"""
    db = get_client()
    result = (
        db.table("generation_jobs")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ==========================================================================
# REFERRALS
# ==========================================================================

def create_referral(referrer_user_id: str, referred_user_id: str, credits_awarded: int) -> dict:
    """Create a referral record"""
    db = get_client()
    result = db.table("referrals").insert({
        "referrer_user_id": referrer_user_id,
        "referred_user_id": referred_user_id,
        "credits_awarded": credits_awarded,
    }).execute()
    return result.data[0]


def get_referrals_by_user(user_id: str) -> list[dict]:
    """Get all referrals made by a user"""
    db = get_client()
    result = (
        db.table("referrals")
        .select("*")
        .eq("referrer_user_id", user_id)
        .execute()
    )
    return result.data or []


def count_successful_referrals(user_id: str) -> int:
    """Count successful referrals for a user"""
    db = get_client()
    result = (
        db.table("referrals")
        .select("id")
        .eq("referrer_user_id", user_id)
        .execute()
    )
    return len(result.data or [])


# ==========================================================================
# LEADERBOARD
# ==========================================================================

def get_leaderboard(country_code: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Get global or country-specific leaderboard"""
    db = get_client()
    query = db.table("leaderboard_global").select("*")
    if country_code:
        query = query.eq("country_code", country_code.upper())
    result = query.order("videos_created", desc=True).limit(limit).execute()
    return result.data or []


# ==========================================================================
# CHALLENGES
# ==========================================================================

def create_challenge(
    id: str,
    hashtag: str,
    scope: str,
    country_code: Optional[str],
    title: str,
    starts_at: datetime,
    ends_at: datetime,
    prize_description: Optional[str],
) -> dict:
    """Create a new challenge"""
    db = get_client()
    result = db.table("challenges").insert({
        "id": id,
        "hashtag": hashtag,
        "scope": scope,
        "country_code": country_code,
        "title": title,
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "prize_description": prize_description,
    }).execute()
    return result.data[0]


def get_challenge(challenge_id: str) -> Optional[dict]:
    """Get challenge by ID"""
    db = get_client()
    result = db.table("challenges").select("*").eq("id", challenge_id).limit(1).execute()
    return result.data[0] if result.data else None


def list_active_challenges(country_code: Optional[str] = None) -> list[dict]:
    """List all active challenges"""
    db = get_client()
    now = datetime.utcnow().isoformat()
    query = db.table("challenges").select("*").lte("starts_at", now).gte("ends_at", now)
    if country_code:
        query = query.eq("country_code", country_code.upper())
    result = query.execute()
    return result.data or []


# ==========================================================================
# CHALLENGE ENTRIES
# ==========================================================================

def create_challenge_entry(
    challenge_id: str,
    user_id: str,
    generation_job_id: str,
) -> dict:
    """Create a new challenge entry"""
    db = get_client()
    result = db.table("challenge_entries").insert({
        "challenge_id": challenge_id,
        "user_id": user_id,
        "generation_job_id": generation_job_id,
        "vote_count": 0,
    }).execute()
    return result.data[0]


def get_challenge_entry(entry_id: str) -> Optional[dict]:
    """Get challenge entry by ID"""
    db = get_client()
    result = db.table("challenge_entries").select("*").eq("id", entry_id).limit(1).execute()
    return result.data[0] if result.data else None


def get_challenge_entry_by_user(challenge_id: str, user_id: str) -> Optional[dict]:
    """Get challenge entry by user and challenge"""
    db = get_client()
    result = (
        db.table("challenge_entries")
        .select("*")
        .eq("challenge_id", challenge_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_challenge_leaderboard(challenge_id: str, limit: int = 50) -> list[dict]:
    """Get leaderboard for a specific challenge"""
    db = get_client()
    result = (
        db.table("challenge_entries")
        .select("*")
        .eq("challenge_id", challenge_id)
        .order("vote_count", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def increment_challenge_entry_votes(entry_id: str) -> None:
    """Increment vote count for a challenge entry"""
    db = get_client()
    db.rpc("increment_entry_votes", {"entry_id": entry_id}).execute()


# ==========================================================================
# VOTES
# ==========================================================================

def create_vote(entry_id: str, voter_user_id: str) -> dict:
    """Create a vote record"""
    db = get_client()
    result = db.table("votes").insert({
        "entry_id": entry_id,
        "voter_user_id": voter_user_id,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
    
    # Increment the vote count
    increment_challenge_entry_votes(entry_id)
    
    return result.data[0]


def get_vote(entry_id: str, voter_user_id: str) -> Optional[dict]:
    """Get vote by entry and voter"""
    db = get_client()
    result = (
        db.table("votes")
        .select("*")
        .eq("entry_id", entry_id)
        .eq("voter_user_id", voter_user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# ==========================================================================
# DREAM THREADS
# ==========================================================================

def create_dream_thread(
    user_id: str,
    goal_title: str,
    goal_description: Optional[str],
    starting_generation_job_id: Optional[str],
    self_reported_net_worth: Optional[str],
) -> dict:
    """Create a new dream thread"""
    db = get_client()
    result = db.table("dream_threads").insert({
        "user_id": user_id,
        "goal_title": goal_title,
        "goal_description": goal_description,
        "starting_generation_job_id": starting_generation_job_id,
        "self_reported_net_worth": self_reported_net_worth,
        "is_active": True,
    }).execute()
    return result.data[0]


def get_dream_thread(thread_id: str) -> Optional[dict]:
    """Get dream thread by ID"""
    db = get_client()
    result = db.table("dream_threads").select("*").eq("id", thread_id).limit(1).execute()
    return result.data[0] if result.data else None


def get_user_dream_threads(user_id: str) -> list[dict]:
    """Get all dream threads for a user"""
    db = get_client()
    result = (
        db.table("dream_threads")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def update_dream_thread(thread_id: str, **kwargs) -> Optional[dict]:
    """Update dream thread fields"""
    db = get_client()
    result = db.table("dream_threads").update(kwargs).eq("id", thread_id).execute()
    return result.data[0] if result.data else None


# ==========================================================================
# DREAM UPDATES
# ==========================================================================

def create_dream_update(
    thread_id: str,
    user_id: str,
    caption: str,
    video_url: Optional[str],
    moderation_status: str = "pending",
) -> dict:
    """Create a new dream update"""
    db = get_client()
    result = db.table("dream_updates").insert({
        "thread_id": thread_id,
        "user_id": user_id,
        "caption": caption,
        "video_url": video_url,
        "moderation_status": moderation_status,
    }).execute()
    return result.data[0]


def get_dream_update(update_id: str) -> Optional[dict]:
    """Get dream update by ID"""
    db = get_client()
    result = db.table("dream_updates").select("*").eq("id", update_id).limit(1).execute()
    return result.data[0] if result.data else None


def get_dream_thread_updates(thread_id: str, status: Optional[str] = None) -> list[dict]:
    """Get all updates for a dream thread"""
    db = get_client()
    query = db.table("dream_updates").select("*").eq("thread_id", thread_id)
    if status:
        query = query.eq("moderation_status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data or []


def update_dream_update(update_id: str, **kwargs) -> Optional[dict]:
    """Update dream update fields"""
    db = get_client()
    result = db.table("dream_updates").update(kwargs).eq("id", update_id).execute()
    return result.data[0] if result.data else None


def update_dream_update_moderation_status(update_id: str, status: str) -> Optional[dict]:
    """Update moderation status of a dream update"""
    db = get_client()
    result = db.table("dream_updates").update({"moderation_status": status}).eq("id", update_id).execute()
    return result.data[0] if result.data else None


# ==========================================================================
# DREAM THREAD FOLLOWS
# ==========================================================================

def create_dream_thread_follow(thread_id: str, follower_user_id: str) -> dict:
    """Follow a dream thread"""
    db = get_client()
    result = db.table("dream_followers").insert({
        "thread_id": thread_id,
        "follower_user_id": follower_user_id,
    }).execute()
    return result.data[0]


def get_dream_thread_follow(thread_id: str, follower_user_id: str) -> Optional[dict]:
    """Get follow record"""
    db = get_client()
    result = (
        db.table("dream_followers")
        .select("*")
        .eq("thread_id", thread_id)
        .eq("follower_user_id", follower_user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_dream_thread_follow(thread_id: str, follower_user_id: str) -> None:
    """Unfollow a dream thread"""
    db = get_client()
    db.table("dream_followers").delete().eq("thread_id", thread_id).eq("follower_user_id", follower_user_id).execute()


def count_dream_thread_followers(thread_id: str) -> int:
    """Count followers of a dream thread"""
    db = get_client()
    result = (
        db.table("dream_followers")
        .select("id")
        .eq("thread_id", thread_id)
        .execute()
    )
    return len(result.data or [])


def get_followed_thread_ids(user_id: str) -> list[str]:
    """Get all thread IDs that a user follows"""
    db = get_client()
    result = (
        db.table("dream_followers")
        .select("thread_id")
        .eq("follower_user_id", user_id)
        .execute()
    )
    return [row["thread_id"] for row in (result.data or [])]


def get_dream_feed(user_id: str, followed_thread_ids: list[str], status: str = "approved", limit: int = 50) -> list[dict]:
    """Get feed of dream updates from followed threads"""
    db = get_client()
    result = (
        db.table("dream_updates")
        .select("*")
        .in_("thread_id", followed_thread_ids)
        .eq("moderation_status", status)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


# ==========================================================================
# ENCOURAGEMENTS
# ==========================================================================

def create_encouragement(
    update_id: str,
    user_id: str,
    message: Optional[str],
) -> dict:
    """Create an encouragement for a dream update"""
    db = get_client()
    result = db.table("encouragements").insert({
        "update_id": update_id,
        "user_id": user_id,
        "message": message,
    }).execute()
    return result.data[0]


def get_encouragement(update_id: str, user_id: str) -> Optional[dict]:
    """Get encouragement by update and user"""
    db = get_client()
    result = (
        db.table("encouragements")
        .select("*")
        .eq("update_id", update_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_dream_update_encouragements(update_id: str) -> list[dict]:
    """Get all encouragements for a dream update"""
    db = get_client()
    result = (
        db.table("encouragements")
        .select("*")
        .eq("update_id", update_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


# ==========================================================================
# RPC FUNCTIONS (for atomic operations)
# ==========================================================================
# These should be created in your Supabase database using schema.sql
# or via the Supabase dashboard

RPC_FUNCTIONS = {
    "increment_credits": """
    create or replace function increment_credits(uid uuid, amt int)
    returns void as $$
    begin
        update users set credits = credits + amt where id = uid;
    end;
    $$ language plpgsql;
    """,
    "increment_daily_usage": """
    create or replace function increment_daily_usage(uid uuid)
    returns void as $$
    begin
        insert into daily_usage (user_id, usage_date, generations_used)
        values (uid, current_date, 1)
        on conflict (user_id, usage_date)
        do update set generations_used = daily_usage.generations_used + 1;
    end;
    $$ language plpgsql;
    """,
    "increment_entry_votes": """
    create or replace function increment_entry_votes(entry_id uuid)
    returns void as $$
    begin
        update challenge_entries set vote_count = vote_count + 1 where id = entry_id;
    end;
    $$ language plpgsql;
    """,
}


def setup_rpc_functions():
    """Setup required RPC functions in the database"""
    db = get_client()
    for name, sql in RPC_FUNCTIONS.items():
        try:
            db.execute(sql)
        except Exception as e:
            # Function might already exist
            pass
