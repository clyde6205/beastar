-- BeAstar.io — Core Database Schema
-- Target: Supabase / PostgreSQL
-- Designed for a bootstrapped launch: every table maps directly to a cost or
-- growth lever so you can see margin and virality in the data from day one.

-- ============================================================
-- USERS & AUTH
-- ============================================================

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT UNIQUE NOT NULL,
    display_name        TEXT NOT NULL,
    date_of_birth       DATE NOT NULL,               -- required for age gating, never nullable
    country_code        TEXT NOT NULL,                -- ISO 3166-1 alpha-2, drives regional challenges/leaderboards
    referral_code       TEXT UNIQUE NOT NULL,          -- this user's own shareable code
    referred_by_user_id UUID REFERENCES users(id),     -- who referred them, if anyone
    face_embedding_id   TEXT,                          -- pointer to verified selfie embedding (not raw biometric data)
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE, -- passed liveness/self-match check
    credits             INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT age_minimum CHECK (date_of_birth <= (CURRENT_DATE - INTERVAL '13 years'))
);

CREATE INDEX idx_users_referral_code ON users(referral_code);
CREATE INDEX idx_users_country ON users(country_code);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================

CREATE TYPE subscription_tier AS ENUM ('free', 'star', 'superstar', 'megastar');

CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier                subscription_tier NOT NULL DEFAULT 'free',
    max_resolution      TEXT NOT NULL DEFAULT '720p',  -- '720p' | '1080p' | '4k'
    daily_generation_cap INTEGER NOT NULL DEFAULT 3,
    renews_at           TIMESTAMPTZ,
    stripe_customer_id  TEXT,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX idx_one_active_sub_per_user ON subscriptions(user_id) WHERE is_active;

-- ============================================================
-- GENERATION JOBS (the core product + the core cost)
-- ============================================================

CREATE TYPE job_status AS ENUM ('queued', 'rendering', 'complete', 'failed');

CREATE TABLE scenarios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT UNIQUE NOT NULL,          -- e.g. 'red-carpet-arrival'
    name        TEXT NOT NULL,                  -- generic, no real-person/IP names — see brand rules
    description TEXT,
    is_premium  BOOLEAN NOT NULL DEFAULT FALSE, -- gated behind a paid tier or credit purchase
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE generation_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scenario_id     UUID NOT NULL REFERENCES scenarios(id),
    resolution      TEXT NOT NULL,              -- '720p' | '1080p' | '4k'
    status          job_status NOT NULL DEFAULT 'queued',
    provider        TEXT,                       -- which video-gen API handled this job
    provider_job_id TEXT,
    output_url      TEXT,                       -- final rendered video in object storage
    render_cost_usd NUMERIC(10,4),               -- actual billed cost from provider — THE key margin metric
    credits_charged INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_jobs_user ON generation_jobs(user_id);
CREATE INDEX idx_jobs_status ON generation_jobs(status);

-- Daily generation counter, used to enforce tier caps without scanning generation_jobs every request
CREATE TABLE daily_usage (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_date      DATE NOT NULL,
    generations_used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date)
);

-- ============================================================
-- REFERRALS
-- ============================================================

CREATE TABLE referrals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_user_id    UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    credits_awarded     INTEGER NOT NULL DEFAULT 100,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_referrals_referrer ON referrals(referrer_user_id);

-- ============================================================
-- CHALLENGES
-- ============================================================

CREATE TYPE challenge_scope AS ENUM ('global', 'regional');

CREATE TABLE challenges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hashtag         TEXT NOT NULL,               -- e.g. '#StarMeChallenge'
    scope           challenge_scope NOT NULL DEFAULT 'global',
    country_code    TEXT,                        -- set only when scope = 'regional'
    title           TEXT NOT NULL,
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ NOT NULL,
    prize_description TEXT
);

CREATE TABLE challenge_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id    UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    generation_job_id UUID REFERENCES generation_jobs(id),
    vote_count      INTEGER NOT NULL DEFAULT 0,
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (challenge_id, user_id, generation_job_id)
);

-- ============================================================
-- LEADERBOARDS (materialized from real activity, not stored counters that drift)
-- ============================================================

CREATE VIEW leaderboard_global AS
SELECT
    u.id AS user_id,
    u.display_name,
    u.country_code,
    COUNT(gj.id) AS videos_created,
    COALESCE(SUM(ce.vote_count), 0) AS total_votes,
    COUNT(r.id) AS successful_referrals
FROM users u
LEFT JOIN generation_jobs gj ON gj.user_id = u.id AND gj.status = 'complete'
LEFT JOIN challenge_entries ce ON ce.user_id = u.id
LEFT JOIN referrals r ON r.referrer_user_id = u.id
GROUP BY u.id, u.display_name, u.country_code;

CREATE VIEW leaderboard_by_country AS
SELECT * FROM leaderboard_global;  -- filter by country_code at query time

-- ============================================================
-- DREAM THREADS ("what's your big dream, and your progress toward it")
-- ============================================================
-- Replaces a single disconnected "aspiration post" with a persistent,
-- ongoing thread per user goal — the structural difference between a
-- snapshot (forgettable) and a followable story (what actually brings
-- people back). See app/main.py docstrings for the full reasoning.

CREATE TYPE net_worth_band AS ENUM ('under_100k', '100k_1m', '1m_5m', '5m_plus', 'prefer_not_to_say');

CREATE TABLE dream_threads (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_title          TEXT NOT NULL CHECK (char_length(goal_title) <= 100),
    goal_description    TEXT CHECK (char_length(goal_description) <= 500),
    starting_generation_job_id UUID REFERENCES generation_jobs(id), -- the star-moment video that sparked this
    self_reported_net_worth net_worth_band,  -- optional, at thread creation only — see note below
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_dream_threads_user ON dream_threads(user_id);

CREATE TABLE dream_updates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id           UUID NOT NULL REFERENCES dream_threads(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    caption             TEXT NOT NULL CHECK (char_length(caption) <= 280),
    video_url           TEXT,             -- optional short update video
    moderation_status   TEXT NOT NULL DEFAULT 'pending', -- 'pending' | 'approved' | 'rejected'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_dream_updates_thread ON dream_updates(thread_id);
CREATE INDEX idx_dream_updates_status ON dream_updates(moderation_status);

CREATE TABLE dream_thread_followers (
    thread_id           UUID NOT NULL REFERENCES dream_threads(id) ON DELETE CASCADE,
    follower_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, follower_user_id)
);

CREATE TABLE dream_update_encouragements (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    update_id           UUID NOT NULL REFERENCES dream_updates(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message             TEXT CHECK (char_length(message) <= 200), -- NULL = a plain reaction, no text
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (update_id, user_id) -- one encouragement per person per update, not a like-farm counter
);

-- ============================================================
-- NOTES
-- ============================================================
-- 1. age_minimum CHECK enforces 13+ at signup; add a stricter parental-consent
--    flow in the app layer for 13-17 rather than relaxing this constraint.
-- 2. face_embedding_id stores a pointer/hash, never raw biometric imagery in
--    this table — keep actual face data in a separate, access-controlled store.
-- 3. render_cost_usd is what lets you catch a mispriced tier with real data
--    instead of guessing — query margin per tier weekly once live.
-- 4. dream_threads.self_reported_net_worth is a BAND, never an exact
--    figure, and must always render in the app labeled "self-reported" —
--    never "verified" — see COMPLIANCE.md for the scam-content rationale.
-- 5. dream_update_encouragements has a UNIQUE(update_id, user_id) constraint
--    deliberately — one genuine encouragement per person, not a like-count
--    that can be farmed or bought. Keep it that way even under growth
--    pressure to inflate engagement metrics.
