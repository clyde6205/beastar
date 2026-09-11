-- BeAstar.io - Migration 001: Initial Schema
-- ============================================================
-- This is the complete initial schema for BeAstar.io
-- Run this first to set up all tables, types, and indexes
-- ============================================================

-- ============================================================
-- EXTENSIONS
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- ENUM TYPES
-- ============================================================

-- Subscription tiers
CREATE TYPE subscription_tier AS ENUM ('free', 'star', 'superstar', 'megastar');

-- Job statuses
CREATE TYPE job_status AS ENUM ('queued', 'rendering', 'complete', 'failed');

-- Content status for dream threads
CREATE TYPE content_status AS ENUM ('draft', 'published', 'archived', 'deleted');

-- ============================================================
-- USERS & AUTH
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT UNIQUE NOT NULL,
    display_name        TEXT NOT NULL,
    date_of_birth       DATE NOT NULL,
    country_code        TEXT NOT NULL,
    referral_code       TEXT UNIQUE NOT NULL,
    referred_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    face_embedding_id   TEXT,
    face_embedding_vector BYTEA,
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    verification_attempts INTEGER NOT NULL DEFAULT 0,
    last_verification_at TIMESTAMPTZ,
    verification_reason TEXT,
    profile_image_url   TEXT,
    bio                 TEXT,
    net_worth_band      TEXT,
    credits             INTEGER NOT NULL DEFAULT 0,
    total_earned_credits INTEGER NOT NULL DEFAULT 0,
    total_spent_credits INTEGER NOT NULL DEFAULT 0,
    last_active_at      TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT age_minimum CHECK (date_of_birth <= (CURRENT_DATE - INTERVAL '13 years'))
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code);
CREATE INDEX IF NOT EXISTS idx_users_country ON users(country_code);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_verified ON users(is_verified);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier                subscription_tier NOT NULL DEFAULT 'free',
    max_resolution      TEXT NOT NULL DEFAULT '720p',
    daily_generation_cap INTEGER NOT NULL DEFAULT 3,
    price_php           NUMERIC(10,2),
    currency           TEXT NOT NULL DEFAULT 'PHP',
    payment_method      TEXT,
    payment_provider    TEXT,
    payment_reference   TEXT,
    renews_at           TIMESTAMPTZ,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ends_at             TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    auto_renew          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for subscriptions
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_sub_per_user ON subscriptions(user_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_tier ON subscriptions(tier);

-- ============================================================
-- SCENARIOS (Star Moment templates)
-- ============================================================

CREATE TABLE IF NOT EXISTS scenarios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    prompt_template TEXT NOT NULL,
    category    TEXT,
    thumbnail_url TEXT,
    is_premium  BOOLEAN NOT NULL DEFAULT FALSE,
    required_tier subscription_tier NOT NULL DEFAULT 'free',
    credit_cost INTEGER NOT NULL DEFAULT 1,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for scenarios
CREATE INDEX IF NOT EXISTS idx_scenarios_slug ON scenarios(slug);
CREATE INDEX IF NOT EXISTS idx_scenarios_active ON scenarios(is_active);
CREATE INDEX IF NOT EXISTS idx_scenarios_category ON scenarios(category);

-- ============================================================
-- GENERATION JOBS
-- ============================================================

CREATE TABLE IF NOT EXISTS generation_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scenario_id     UUID NOT NULL REFERENCES scenarios(id),
    input_image_url TEXT NOT NULL,
    prompt          TEXT,
    resolution      TEXT NOT NULL,
    status          job_status NOT NULL DEFAULT 'queued',
    provider        TEXT,
    provider_job_id TEXT,
    output_url      TEXT,
    watermarked_url TEXT,
    storage_path    TEXT,
    render_cost_usd NUMERIC(10,4),
    credits_charged INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    started_at      TIMESTAMPTZ
);

-- Indexes for generation jobs
CREATE INDEX IF NOT EXISTS idx_jobs_user ON generation_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_scenario ON generation_jobs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON generation_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_completed_at ON generation_jobs(completed_at);

-- ============================================================
-- DAILY USAGE TRACKING
-- ============================================================

CREATE TABLE IF NOT EXISTS daily_usage (
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    usage_date      DATE NOT NULL,
    generations_used INTEGER NOT NULL DEFAULT 0,
    credits_earned   INTEGER NOT NULL DEFAULT 0,
    credits_spent    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date)
);

-- Indexes for daily usage
CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage(user_id, usage_date);
CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON daily_usage(usage_date);

-- ============================================================
-- REFERRALS
-- ============================================================

CREATE TABLE IF NOT EXISTS referrals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_user_id    UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    credits_awarded     INTEGER NOT NULL DEFAULT 100,
    is_paid            BOOLEAN NOT NULL DEFAULT FALSE,
    paid_at            TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for referrals
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_user_id);
CREATE INDEX IF NOT EXISTS idx_referrals_created_at ON referrals(created_at);

-- ============================================================
-- DREAM THREADS
-- ============================================================

CREATE TABLE IF NOT EXISTS dream_threads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    goal            TEXT,
    category        TEXT,
    status          content_status NOT NULL DEFAULT 'draft',
    total_views     INTEGER NOT NULL DEFAULT 0,
    total_encouragements INTEGER NOT NULL DEFAULT 0,
    total_shares    INTEGER NOT NULL DEFAULT 0,
    is_featured     BOOLEAN NOT NULL DEFAULT FALSE,
    featured_at     TIMESTAMPTZ,
    pinned_update_id UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for dream threads
CREATE INDEX IF NOT EXISTS idx_dream_threads_user ON dream_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_dream_threads_status ON dream_threads(status);
CREATE INDEX IF NOT EXISTS idx_dream_threads_created_at ON dream_threads(created_at);
CREATE INDEX IF NOT EXISTS idx_dream_threads_total_views ON dream_threads(total_views);

-- ============================================================
-- DREAM UPDATES
-- ============================================================

CREATE TABLE IF NOT EXISTS dream_updates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id       UUID NOT NULL REFERENCES dream_threads(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    media_urls      TEXT[],
    video_url       TEXT,
    thumbnail_url   TEXT,
    status          content_status NOT NULL DEFAULT 'published',
    total_encouragements INTEGER NOT NULL DEFAULT 0,
    total_comments  INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for dream updates
CREATE INDEX IF NOT EXISTS idx_dream_updates_thread ON dream_updates(thread_id);
CREATE INDEX IF NOT EXISTS idx_dream_updates_user ON dream_updates(user_id);
CREATE INDEX IF NOT EXISTS idx_dream_updates_created_at ON dream_updates(created_at);

-- ============================================================
-- FOLLOWS (Users following Dream Threads)
-- ============================================================

CREATE TABLE IF NOT EXISTS dream_thread_follows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id       UUID NOT NULL REFERENCES dream_threads(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, thread_id)
);

-- Indexes for follows
CREATE INDEX IF NOT EXISTS idx_follows_user ON dream_thread_follows(user_id);
CREATE INDEX IF NOT EXISTS idx_follows_thread ON dream_thread_follows(thread_id);
CREATE INDEX IF NOT EXISTS idx_follows_user_thread ON dream_thread_follows(user_id, thread_id);

-- ============================================================
-- ENCOURAGEMENTS (Likes on Dream Updates)
-- ============================================================

CREATE TABLE IF NOT EXISTS encouragements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    update_id       UUID NOT NULL REFERENCES dream_updates(id) ON DELETE CASCADE,
    thread_id       UUID NOT NULL REFERENCES dream_threads(id) ON DELETE CASCADE,
    message         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, update_id)
);

-- Indexes for encouragements
CREATE INDEX IF NOT EXISTS idx_encouragements_user ON encouragements(user_id);
CREATE INDEX IF NOT EXISTS idx_encouragements_update ON encouragements(update_id);
CREATE INDEX IF NOT EXISTS idx_encouragements_thread ON encouragements(thread_id);
CREATE INDEX IF NOT EXISTS idx_encouragements_created_at ON encouragements(created_at);

-- ============================================================
-- COMMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    update_id       UUID NOT NULL REFERENCES dream_updates(id) ON DELETE CASCADE,
    thread_id       UUID NOT NULL REFERENCES dream_threads(id) ON DELETE CASCADE,
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    is_pinned       BOOLEAN NOT NULL DEFAULT FALSE,
    total_replies   INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for comments
CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_update ON comments(update_id);
CREATE INDEX IF NOT EXISTS idx_comments_thread ON comments(thread_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON comments(parent_comment_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- ============================================================
-- CHALLENGES
-- ============================================================

CREATE TABLE IF NOT EXISTS challenges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    country_code    TEXT,
    required_tier   subscription_tier DEFAULT 'free',
    prize_description TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for challenges
CREATE INDEX IF NOT EXISTS idx_challenges_slug ON challenges(slug);
CREATE INDEX IF NOT EXISTS idx_challenges_active ON challenges(is_active);
CREATE INDEX IF NOT EXISTS idx_challenges_dates ON challenges(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_challenges_country ON challenges(country_code);

-- ============================================================
-- CHALLENGE PARTICIPATION
-- ============================================================

CREATE TABLE IF NOT EXISTS challenge_participations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id    UUID NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    thread_id       UUID REFERENCES dream_threads(id) ON DELETE CASCADE,
    update_id       UUID REFERENCES dream_updates(id) ON DELETE CASCADE,
    submission_url  TEXT,
    status          TEXT NOT NULL DEFAULT 'submitted',
    score           INTEGER,
    rank            INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (challenge_id, user_id)
);

-- Indexes for challenge participations
CREATE INDEX IF NOT EXISTS idx_participations_challenge ON challenge_participations(challenge_id);
CREATE INDEX IF NOT EXISTS idx_participations_user ON challenge_participations(user_id);
CREATE INDEX IF NOT EXISTS idx_participations_status ON challenge_participations(status);
CREATE INDEX IF NOT EXISTS idx_participations_score ON challenge_participations(score);

-- ============================================================
-- LEADERBOARDS
-- ============================================================

CREATE TABLE IF NOT EXISTS leaderboards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    slug            TEXT UNIQUE NOT NULL,
    description     TEXT,
    country_code    TEXT,
    time_period     TEXT NOT NULL DEFAULT 'all_time',
    metric          TEXT NOT NULL DEFAULT 'total_encouragements',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for leaderboards
CREATE INDEX IF NOT EXISTS idx_leaderboards_slug ON leaderboards(slug);
CREATE INDEX IF NOT EXISTS idx_leaderboards_active ON leaderboards(is_active);
CREATE INDEX IF NOT EXISTS idx_leaderboards_country ON leaderboards(country_code);

-- ============================================================
-- LEADERBOARD ENTRIES
-- ============================================================

CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    leaderboard_id  UUID NOT NULL REFERENCES leaderboards(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rank            INTEGER NOT NULL,
    score           INTEGER NOT NULL DEFAULT 0,
    display_name    TEXT NOT NULL,
    profile_image_url TEXT,
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (leaderboard_id, user_id, period_start)
);

-- Indexes for leaderboard entries
CREATE INDEX IF NOT EXISTS idx_entries_leaderboard ON leaderboard_entries(leaderboard_id);
CREATE INDEX IF NOT EXISTS idx_entries_user ON leaderboard_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_entries_rank ON leaderboard_entries(rank);
CREATE INDEX IF NOT EXISTS idx_entries_period ON leaderboard_entries(period_start, period_end);

-- ============================================================
-- PAYMENTS
-- ============================================================

CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
CREATE TYPE payment_provider AS ENUM ('stripe', 'paymongo', 'gcash', 'manual');

CREATE TABLE IF NOT EXISTS payments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount          NUMERIC(10,2) NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'PHP',
    provider        payment_provider NOT NULL,
    provider_reference TEXT NOT NULL,
    status          payment_status NOT NULL DEFAULT 'pending',
    description     TEXT,
    metadata        JSONB,
    webhook_data    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- Indexes for payments
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_subscription ON payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_payments_provider ON payments(provider);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_reference ON payments(provider_reference);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TYPE notification_type AS ENUM (
    'follow', 'encouragement', 'comment', 'challenge', 
    'payment_success', 'payment_failed', 'subscription_started', 
    'subscription_ending', 'referral_earned', 'system'
);

CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            notification_type NOT NULL,
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    data            JSONB,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications(created_at);

-- ============================================================
-- AUDIT LOG (For compliance and debugging)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    old_value       JSONB,
    new_value       JSONB,
    ip_address      TEXT,
    user_agent      TEXT,
    status          TEXT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- ============================================================
-- STORAGE METADATA
-- ============================================================

CREATE TABLE IF NOT EXISTS storage_metadata (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    storage_path    TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    content_size    BIGINT NOT NULL,
    file_name       TEXT,
    file_type       TEXT NOT NULL,
    is_public       BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMPTZ,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for storage metadata
CREATE INDEX IF NOT EXISTS idx_storage_user ON storage_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_storage_path ON storage_metadata(storage_path);
CREATE INDEX IF NOT EXISTS idx_storage_created_at ON storage_metadata(created_at);

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_generation_jobs_updated_at BEFORE UPDATE ON generation_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dream_threads_updated_at BEFORE UPDATE ON dream_threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dream_updates_updated_at BEFORE UPDATE ON dream_updates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_challenges_updated_at BEFORE UPDATE ON challenges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_challenge_participations_updated_at BEFORE UPDATE ON challenge_participations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leaderboards_updated_at BEFORE UPDATE ON leaderboards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS
-- ============================================================

-- View for user statistics
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    u.id,
    u.display_name,
    u.email,
    u.country_code,
    u.is_verified,
    u.credits,
    s.tier,
    s.is_active as subscription_active,
    (SELECT COUNT(*) FROM dream_threads dt WHERE dt.user_id = u.id) as thread_count,
    (SELECT COUNT(*) FROM dream_updates du WHERE du.user_id = u.id) as update_count,
    (SELECT COUNT(*) FROM generation_jobs gj WHERE gj.user_id = u.id AND gj.status = 'complete') as generation_count,
    (SELECT COUNT(*) FROM referrals r WHERE r.referrer_user_id = u.id) as referrals_count,
    (SELECT COUNT(DISTINCT thread_id) FROM dream_thread_follows f WHERE f.user_id = u.id) as following_count,
    (SELECT COUNT(*) FROM dream_thread_follows f WHERE f.thread_id IN (SELECT id FROM dream_threads WHERE user_id = u.id)) as followers_count,
    u.created_at,
    u.last_active_at
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.is_active = TRUE;

-- View for leaderboard
CREATE OR REPLACE VIEW global_leaderboard AS
SELECT 
    u.id,
    u.display_name,
    u.profile_image_url,
    u.country_code,
    COUNT(DISTINCT dt.id) as thread_count,
    COUNT(DISTINCT du.id) as update_count,
    SUM(du.total_encouragements) as total_encouragements,
    COUNT(DISTINCT f.user_id) as followers_count,
    u.created_at
FROM users u
LEFT JOIN dream_threads dt ON u.id = dt.user_id
LEFT JOIN dream_updates du ON u.id = du.user_id
LEFT JOIN dream_thread_follows f ON dt.id = f.thread_id
WHERE u.is_active = TRUE
GROUP BY u.id, u.display_name, u.profile_image_url, u.country_code, u.created_at
ORDER BY total_encouragements DESC;

-- View for daily active users
CREATE OR REPLACE VIEW daily_active_users AS
SELECT 
    DATE(u.last_active_at) as day,
    COUNT(DISTINCT u.id) as active_users,
    COUNT(DISTINCT CASE WHEN u.country_code = 'PH' THEN u.id END) as ph_users,
    COUNT(DISTINCT CASE WHEN u.is_verified = TRUE THEN u.id END) as verified_users
FROM users u
WHERE u.last_active_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(u.last_active_at)
ORDER BY day DESC;

-- ============================================================
-- INITIAL DATA
-- ============================================================

-- Insert initial scenarios if they don't exist
INSERT INTO scenarios (slug, name, description, prompt_template, category, is_premium, required_tier, credit_cost, is_active, sort_order)
VALUES 
    ('red-carpet-arrival', 'Red Carpet Arrival', 'Walk the red carpet like a Hollywood star', 'A {gender} celebrity walking the red carpet, elegant, confident, paparazzi flashing cameras, luxury event, cinematic lighting', 'celebrity', FALSE, 'free', 1, TRUE, 1),
    ('music-video-star', 'Music Video Star', 'Be the center of attention in a music video', 'A {gender} pop star performing on stage, colorful lights, backup dancers, energetic, cinematic', 'music', FALSE, 'free', 1, TRUE, 2),
    ('fashion-show', 'Fashion Show', 'Strut down the runway like a top model', 'A {gender} fashion model walking the runway, designer clothes, confident pose, fashion week atmosphere', 'fashion', FALSE, 'free', 1, TRUE, 3),
    ('action-hero', 'Action Hero', 'Be the hero of your own action movie', 'A {gender} action hero in a high-stakes scene, dramatic lighting, intense expression, movie poster style', 'movie', FALSE, 'free', 1, TRUE, 4),
    ('business-mogul', 'Business Mogul', 'Command the boardroom like a CEO', 'A {gender} business executive in a boardroom, confident, professional, power pose, corporate setting', 'business', FALSE, 'free', 1, TRUE, 5),
    ('social-media-influencer', 'Social Media Influencer', 'Be an influencer with millions of followers', 'A {gender} social media influencer taking a selfie, stylish outfit, perfect pose, smartphone in hand, trendy background', 'social', FALSE, 'free', 1, TRUE, 6),
    ('sports-champion', 'Sports Champion', 'Celebrate victory like a champion athlete', 'A {gender} athlete celebrating victory, sports uniform, trophy in hand, stadium background, triumphant pose', 'sports', FALSE, 'free', 1, TRUE, 7),
    ('movie-premiere', 'Movie Premiere', 'Attend a glamorous movie premiere', 'A {gender} movie star at a premiere, elegant outfit, red carpet, flashing cameras, movie poster in background', 'celebrity', FALSE, 'free', 1, TRUE, 8)
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- COMMENTS
-- ============================================================

-- BeAstar.io Initial Schema Migration Complete
-- Run this migration first to set up the complete database structure
-- ============================================================
