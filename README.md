# BeAstar.io — First Commit

Lean starter for a bootstrapped launch. Nothing here requires paid infra
until you actually run it against real hosting.

## What's included

- **`schema.sql`** — full Postgres schema (users, subscriptions, generation
  jobs, referrals, challenges, leaderboards) designed for Supabase's free
  tier. Includes an age-gate constraint (13+) and a `render_cost_usd`
  column on every job so you can track real margin per tier once live.
- **`app/main.py`** — FastAPI app covering:
  - `POST /auth/signup` — age-gated signup, referral code generation,
    referral credit payout
  - `POST /auth/{user_id}/verify-face` — placeholder for the real
    liveness + self-match + known-public-figure check (see docstring —
    this is the piece that keeps the app off the "unauthorized deepfake"
    list and needs a real vendor, e.g. a liveness-detection API, wired in
    before launch)
  - `POST /generate` — tier-gated generation request (blocks
    unverified users, enforces resolution caps and daily caps per tier)
  - `GET /qr/{user_id}` — returns a PNG QR code for the viral share loop
  - `GET /leaderboard` — global/country leaderboard projection

The data layer is in-memory dicts right now (`_users_db`, `_jobs_db`) so
you can run and test the API shape immediately. Swap those for real
Supabase calls against `schema.sql` as the next step — the function
signatures won't need to change.

## What's now real vs. what's a documented stub

**Real, matches documented vendor APIs, will work with real keys:**
- `app/providers/runway.py` — Runway Gen-4 Turbo image-to-video, correct
  auth/versioning/task-polling shape
- `app/providers/paymongo_gcash.py` — PayMongo Source-resource GCash flow
- `app/db/supabase_client.py` — full CRUD matching `schema.sql`
- `app/storage/selfie_upload.py` — validation + Supabase Storage upload,
  signed URLs
- `app/i18n/translator.py` — locale resolution + catalog lookup, with
  English and Tagalog catalogs populated

**Stubbed on purpose, not faked — each has a clear TODO and won't need
restructuring, just filling in with your account details:**
- `app/providers/kling.py` — backup provider; exact endpoint/fields vary
  by Kling account/aggregator, confirm before launch
- `verify_webhook_signature()` (PayMongo) — needs your live signing secret
- `run_content_safety_check()` (selfie upload) — needs a real moderation
  vendor (AWS Rekognition, Hive, etc.) chosen and wired in
- Liveness/face-match/known-public-figure check in `/auth/{id}/verify-face`
  — needs a real liveness-detection vendor
- Background job worker to actually run queued generations to completion
  (currently sketched in a comment in `/generate` — needs Celery/RQ or
  similar, not just inline code)

**Deliberately out of scope for this backend-only build:**
- Any mobile (iOS/Android) or web frontend — nothing to translate UI
  copy into yet beyond the framework itself
- Translated string content beyond English + Tagalog (the two that matter
  for a PH soft launch) — add locale JSON files under `app/i18n/locales/`
  as real UI copy exists to translate
- Load testing, security audit, app store submission — all real, all
  needed before "global commercial platform," none of them code

## Run it locally

```bash
pip install -r requirements.txt --break-system-packages
uvicorn app.main:app --reload
```

Then hit `http://localhost:8000/docs` for interactive API docs (FastAPI
generates this automatically).
