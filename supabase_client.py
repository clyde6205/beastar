"""
BeAstar.io — Supabase data-access layer
=========================================
Real query functions against schema.sql, replacing the in-memory dicts used
in the first commit. Function signatures match what main.py already calls,
so wiring this in is a drop-in swap, not a rewrite.

Requires:
    SUPABASE_URL, SUPABASE_KEY (service role key — this runs server-side)
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from supabase import Client, create_client

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
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
    db = get_client()
    result = db.table("users").select("*").eq("id", user_id).limit(1).execute()
    return result.data[0] if result.data else None


def find_user_by_referral_code(referral_code: str) -> Optional[dict]:
    db = get_client()
    result = db.table("users").select("*").eq("referral_code", referral_code).limit(1).execute()
    return result.data[0] if result.data else None


def increment_credits(user_id: str, amount: int) -> None:
    # Prefer an atomic RPC (Postgres function) over read-modify-write to
    # avoid a race when two referral payouts land at once:
    #   create function increment_credits(uid uuid, amt int) returns void
    #   as $$ update users set credits = credits + amt where id = uid $$
    #   language sql;
    db = get_client()
    db.rpc("increment_credits", {"uid": user_id, "amt": amount}).execute()


def mark_user_verified(user_id: str, face_embedding_id: str) -> dict:
    db = get_client()
    result = db.table("users").update({
        "is_verified": True,
        "face_embedding_id": face_embedding_id,
    }).eq("id", user_id).execute()
    return result.data[0]


def get_user_tier(user_id: str) -> str:
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
# GENERATION JOBS
# ==========================================================================

def get_scenario_by_slug(slug: str) -> Optional[dict]:
    db = get_client()
    result = db.table("scenarios").select("*").eq("slug", slug).eq("is_active", True).limit(1).execute()
    return result.data[0] if result.data else None


def count_generations_today(user_id: str) -> int:
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
    # Atomic upsert via RPC recommended for the same race-condition reason
    # as increment_credits above:
    #   create function increment_daily_usage(uid uuid) returns void as $$
    #     insert into daily_usage (user_id, usage_date, generations_used)
    #     values (uid, current_date, 1)
    #     on conflict (user_id, usage_date)
    #     do update set generations_used = daily_usage.generations_used + 1
    #   $$ language sql;
    db = get_client()
    db.rpc("increment_daily_usage", {"uid": user_id}).execute()


def create_generation_job(
    user_id: str, scenario_id: str, resolution: str, credits_charged: int
) -> dict:
    db = get_client()
    result = db.table("generation_jobs").insert({
        "user_id": user_id,
        "scenario_id": scenario_id,
        "resolution": resolution,
        "status": "queued",
        "credits_charged": credits_charged,
    }).execute()
    return result.data[0]


def update_generation_job(
    job_id: str,
    status: str,
    provider: Optional[str] = None,
    provider_job_id: Optional[str] = None,
    output_url: Optional[str] = None,
    render_cost_usd: Optional[float] = None,
) -> dict:
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


def get_generation_job(job_id: str) -> Optional[dict]:
    db = get_client()
    result = db.table("generation_jobs").select("*").eq("id", job_id).limit(1).execute()
    return result.data[0] if result.data else None


# ==========================================================================
# LEADERBOARD — just query the views defined in schema.sql directly
# ==========================================================================

def get_leaderboard(country_code: Optional[str] = None, limit: int = 50) -> list[dict]:
    db = get_client()
    query = db.table("leaderboard_global").select("*")
    if country_code:
        query = query.eq("country_code", country_code.upper())
    result = query.order("videos_created", desc=True).limit(limit).execute()
    return result.data
