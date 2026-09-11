# BeAstar.io - Configuration Reference

## 📋 Overview

This document provides a **complete reference** for all environment variables and configuration options required to run BeAstar.io in **production**.

---

## 🔧 Environment Variables

### Quick Reference Table

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `APP_ENV` | No | `development` | Application environment | `production` |
| `APP_BASE_URL` | No | `https://beastar.io` | Base URL for the application | `https://api.beastar.io` |
| `DEBUG` | No | `true` | Enable debug mode | `false` |
| `SECRET_KEY` | **Yes** | - | Secret key for JWT signing | `secrets.token_urlsafe(64)` |
| `ALGORITHM` | No | `HS256` | JWT signing algorithm | `HS256` |
| `LOG_LEVEL` | No | `INFO` | Logging level | `DEBUG`, `WARNING`, `ERROR` |
| `LOG_FILE` | No | `beastar.log` | Log file path | `/var/log/beastar/beastar.log` |
| `RATE_LIMIT_ENABLED` | No | `true` | Enable rate limiting | `true` |
| `MIN_SIGNUP_AGE_YEARS` | No | `13` | Minimum age for signup (COPPA compliance) | `13` |

### Database Configuration

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `SUPABASE_URL` | **Yes** | - | Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_KEY` | **Yes** | - | Supabase anon/public key | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `SUPABASE_STORAGE_BUCKET` | No | `selfies` | Supabase Storage bucket name | `beastar-media` |

### Redis Configuration

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `REDIS_URL` | **Yes** | `redis://localhost:6379/0` | Redis connection URL | `redis://beastar-redis:6379/0` |
| `REDIS_PASSWORD` | **Yes** | - | Redis password | `secrets.token_urlsafe(32)` |

### AI Provider Configuration

#### Runway (Primary Video Generation)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `RUNWAY_API_KEY` | **Yes** | - | Runway API key | `your-runway-api-key` |

#### Kling AI (Fallback Video Generation)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `KLING_API_KEY` | No | - | Kling AI API key | `your-kling-api-key` |
| `KLING_API_BASE` | No | `https://api.kling.ai` | Kling API base URL | `https://api.kling.ai/v1` |

### Face Verification & Content Moderation

#### AWS Rekognition (Primary)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | **Yes** | - | AWS Access Key ID | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | **Yes** | - | AWS Secret Access Key | `your-secret-key` |
| `AWS_REGION` | No | `us-east-1` | AWS region | `us-west-2`, `eu-west-1` |

#### Hive AI (Fallback Moderation)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `HIVE_API_KEY` | No | - | Hive AI API key | `your-hive-api-key` |
| `HIVE_API_BASE` | No | `https://api.hive.ai` | Hive API base URL | `https://api.hive.ai/v2` |

### Payment Provider Configuration

#### PayMongo (GCash - Philippines)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `PAYMONGO_SECRET_KEY` | No | - | PayMongo secret key | `sk_test_...` |
| `PAYMONGO_WEBHOOK_SECRET` | No | - | PayMongo webhook signing secret | `whsec_...` |

#### Stripe (Global)

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `STRIPE_SECRET_KEY` | No | - | Stripe secret key | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | No | - | Stripe webhook signing secret | `whsec_...` |

### Celery Configuration

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `CELERY_BROKER_URL` | No | Uses `REDIS_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | No | Uses `REDIS_URL` | Celery result backend URL | `redis://localhost:6379/0` |
| `CELERY_WORKER_CONCURRENCY` | No | `4` | Number of worker processes | `8` |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | No | `100` | Max tasks per worker before restart | `200` |
| `CELERY_WORKER_MAX_MEMORY_PER_CHILD` | No | `500000` | Max memory per worker (bytes) | `1000000` |

### Tier Configuration (User Limits)

These can be configured directly in the code or via environment variables:

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `TIER_LIMITS` | See below | Resolution and daily caps per tier | - |
| `TIER_PRICE_PHP` | See below | Pricing in Philippine Pesos | - |

Default Tier Limits (in `backend/app/main.py`):

```python
TIER_LIMITS = {
    "free": {"max_resolution": "720p", "daily_cap": 3},
    "star": {"max_resolution": "1080p", "daily_cap": 10},
    "superstar": {"max_resolution": "1080p", "daily_cap": 25},
    "megastar": {"max_resolution": "4k", "daily_cap": 100},
}
```

Default Tier Pricing (PHP):

```python
TIER_PRICE_PHP = {
    "star": 279.00,
    "superstar": 559.00,
    "megastar": 1119.00,
}
```

### Upload Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `MAX_UPLOAD_BYTES` | `8 * 1024 * 1024` | Max upload size in bytes | `10 * 1024 * 1024` (10MB) |

---

## 📁 Configuration Files

### `.env` File Template

Here's a complete `.env` file template with all required and optional variables:

```bash
# =============================================================================
# BeAstar.io - Environment Configuration
# =============================================================================
# Copy this file to .env and fill in the values
# NEVER commit this file to version control

# -------------------------------------------------------------------------
# Application Configuration
# -------------------------------------------------------------------------
APP_ENV=production
APP_BASE_URL=https://beastar.io
DEBUG=false
SECRET_KEY=your-secret-key-here-generate-with-python-secrets-token_urlsafe-64
ALGORITHM=HS256
LOG_LEVEL=INFO
LOG_FILE=/var/log/beastar/beastar.log
RATE_LIMIT_ENABLED=true
MIN_SIGNUP_AGE_YEARS=13

# -------------------------------------------------------------------------
# Database Configuration (Supabase)
# -------------------------------------------------------------------------
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_STORAGE_BUCKET=selfies

# -------------------------------------------------------------------------
# Redis Configuration
# -------------------------------------------------------------------------
REDIS_URL=redis://beastar-redis:6379/0
REDIS_PASSWORD=your-redis-password-here

# -------------------------------------------------------------------------
# AI Provider Configuration
# -------------------------------------------------------------------------

# Runway (Primary Video Generation)
RUNWAY_API_KEY=your-runway-api-key-here

# Kling AI (Fallback Video Generation)
KLING_API_KEY=your-kling-api-key-here
KLING_API_BASE=https://api.kling.ai

# -------------------------------------------------------------------------
# Face Verification & Content Moderation
# -------------------------------------------------------------------------

# AWS Rekognition (Primary)
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1

# Hive AI (Fallback Moderation)
HIVE_API_KEY=your-hive-api-key-here
HIVE_API_BASE=https://api.hive.ai

# -------------------------------------------------------------------------
# Payment Provider Configuration
# -------------------------------------------------------------------------

# PayMongo (GCash - Philippines)
PAYMONGO_SECRET_KEY=sk_test_your-paymongo-secret-key
PAYMONGO_WEBHOOK_SECRET=whsec_your-paymongo-webhook-secret

# Stripe (Global)
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=whsec_your-stripe-webhook-secret

# -------------------------------------------------------------------------
# Celery Configuration
# -------------------------------------------------------------------------
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
CELERY_WORKER_MAX_MEMORY_PER_CHILD=500000

# -------------------------------------------------------------------------
# Security Configuration
# -------------------------------------------------------------------------
# JWT Token Expiry (in minutes)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=1440

# Rate Limiting
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_AUTH=1000/minute
RATE_LIMIT_GENERATION=10/minute

# -------------------------------------------------------------------------
# Storage Configuration
# -------------------------------------------------------------------------
# Local storage path (for temporary files)
TEMP_STORAGE_PATH=/tmp/beastar
UPLOAD_STORAGE_PATH=/var/storage/beastar

# -------------------------------------------------------------------------
# Video Generation Configuration
# -------------------------------------------------------------------------
# FFmpeg path (usually just 'ffmpeg')
FFMPEG_PATH=ffmpeg

# Watermark text
AI_DISCLOSURE_TEXT="AI-Generated Content"

# Video quality settings
VIDEO_QUALITY=high
VIDEO_CRF=18

# -------------------------------------------------------------------------
# Content Moderation Configuration
# -------------------------------------------------------------------------
# Safety threshold (0.0 to 1.0)
SAFETY_THRESHOLD=0.9

# -------------------------------------------------------------------------
# Analytics Configuration (Optional)
# -------------------------------------------------------------------------
# Google Analytics
GA_TRACKING_ID=UA-XXXXXX-Y

# Sentry Error Tracking
SENTRY_DSN=your-sentry-dsn-here
SENTRY_ENVIRONMENT=production

# -------------------------------------------------------------------------
# Email Configuration (Optional - for notifications)
# -------------------------------------------------------------------------
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@beastar.io
SMTP_USE_TLS=true
```

---

## 🔐 Security Configuration

### JWT Token Configuration

| Variable | Default | Description | Recommended |
|----------|---------|-------------|-------------|
| `SECRET_KEY` | - | JWT signing secret | 64+ character random string |
| `ALGORITHM` | `HS256` | JWT signing algorithm | `HS256` or `RS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token expiry | 15-60 minutes |
| `JWT_REFRESH_TOKEN_EXPIRE_MINUTES` | `1440` | Refresh token expiry | 1-30 days |

**Generating a Secure Secret Key:**

```python
import secrets
print(secrets.token_urlsafe(64))
```

### Rate Limiting Configuration

| Variable | Default | Description | Recommended |
|----------|---------|-------------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting | `true` |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Default rate limit | Adjust based on traffic |
| `RATE_LIMIT_AUTH` | `1000/minute` | Rate limit for authenticated users | Higher than default |
| `RATE_LIMIT_GENERATION` | `10/minute` | Rate limit for generation endpoints | Prevent abuse |

### CORS Configuration

CORS (Cross-Origin Resource Sharing) is configured in `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**For Production:** Replace `allow_origins=["*"]` with your specific domains:

```python
allow_origins=[
    "https://beastar.io",
    "https://www.beastar.io",
    "https://app.beastar.io",
    "beastar://*",  # For mobile apps
],
```

---

## 🚀 Production Configuration Checklist

### Required Configuration (MUST be set for production)

- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` - 64+ character random string
- [ ] `SUPABASE_URL` - Your Supabase project URL
- [ ] `SUPABASE_KEY` - Your Supabase anon/public key
- [ ] `REDIS_URL` - Redis connection URL
- [ ] `REDIS_PASSWORD` - Redis password
- [ ] `RUNWAY_API_KEY` - Runway API key
- [ ] `AWS_ACCESS_KEY_ID` - AWS Access Key ID
- [ ] `AWS_SECRET_ACCESS_KEY` - AWS Secret Access Key
- [ ] `AWS_REGION` - AWS region
- [ ] SSL certificates configured in Nginx

### Recommended Configuration (SHOULD be set for production)

- [ ] `LOG_LEVEL=INFO` or `WARNING`
- [ ] `LOG_FILE=/var/log/beastar/beastar.log`
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] `KLING_API_KEY` - Kling AI fallback
- [ ] `HIVE_API_KEY` - Hive AI moderation fallback
- [ ] `PAYMONGO_SECRET_KEY` - PayMongo payment processing
- [ ] `PAYMONGO_WEBHOOK_SECRET` - PayMongo webhook verification
- [ ] `STRIPE_SECRET_KEY` - Stripe payment processing
- [ ] `STRIPE_WEBHOOK_SECRET` - Stripe webhook verification

### Optional Configuration (NICE to have)

- [ ] `GA_TRACKING_ID` - Google Analytics
- [ ] `SENTRY_DSN` - Sentry error tracking
- [ ] SMTP configuration - Email notifications
- [ ] Custom tier limits and pricing

---

## 📊 Tier Configuration

### Default Tier Limits

The application supports four tiers with different limits:

| Tier | Max Resolution | Daily Cap | Price (PHP) | Target Users |
|------|----------------|-----------|-------------|--------------|
| Free | 720p | 3 | Free | New users |
| Star | 1080p | 10 | ₱279 | Casual users |
| Superstar | 1080p | 25 | ₱559 | Power users |
| Megastar | 4K | 100 | ₱1,119 | Professionals |

### Customizing Tiers

To customize tier limits, modify the `TIER_LIMITS` dictionary in `backend/app/main.py`:

```python
TIER_LIMITS = {
    "free": {"max_resolution": "720p", "daily_cap": 3},
    "star": {"max_resolution": "1080p", "daily_cap": 10},
    "superstar": {"max_resolution": "1080p", "daily_cap": 25},
    "megastar": {"max_resolution": "4k", "daily_cap": 100},
    # Add custom tiers
    "vip": {"max_resolution": "4k", "daily_cap": 500},
}
```

### Customizing Pricing

To customize pricing, modify the `TIER_PRICE_PHP` dictionary in `backend/app/main.py`:

```python
TIER_PRICE_PHP = {
    "star": 279.00,
    "superstar": 559.00,
    "megastar": 1119.00,
    # Add custom pricing
    "vip": 2500.00,
}
```

---

## 🎯 Feature Flags

The application supports feature flags for gradual rollouts:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_FACE_VERIFICATION` | `true` | Enable face verification | Required for compliance |
| `ENABLE_CONTENT_MODERATION` | `true` | Enable content moderation | Required for safety |
| `ENABLE_VIDEO_GENERATION` | `true` | Enable video generation | Core feature |
| `ENABLE_DREAM_THREADS` | `true` | Enable dream threads | Social feature |
| `ENABLE_CHALLENGES` | `true` | Enable challenges | Engagement feature |
| `ENABLE_LEADERBOARDS` | `true` | Enable leaderboards | Gamification feature |
| `ENABLE_REFERRALS` | `true` | Enable referral system | Viral growth feature |

---

## 🌍 Localization Configuration

The application supports internationalization (i18n) with the following configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_LOCALE` | `en` | Default locale | `en`, `tl`, etc. |
| `SUPPORTED_LOCALES` | `en, tl` | Supported locales | Comma-separated list |

### Adding a New Locale

1. Create a new JSON file in `backend/app/i18n/locales/` (e.g., `es.json`)
2. Add translations for all keys
3. Update `SUPPORTED_LOCALES` to include the new locale

---

## 📈 Performance Configuration

### Caching Configuration

| Variable | Default | Description | Recommended |
|----------|---------|-------------|-------------|
| `CACHE_ENABLED` | `true` | Enable caching | `true` for production |
| `CACHE_TTL` | `300` | Cache TTL in seconds | 300-3600 |
| `CACHE_MAX_SIZE` | `1000` | Max cache entries | 1000-10000 |

### Video Processing Configuration

| Variable | Default | Description | Recommended |
|----------|---------|-------------|-------------|
| `FFMPEG_PATH` | `ffmpeg` | Path to FFmpeg binary | `/usr/bin/ffmpeg` |
| `VIDEO_QUALITY` | `high` | Video quality preset | `low`, `medium`, `high` |
| `VIDEO_CRF` | `18` | FFmpeg CRF value | 18-28 (lower = better quality) |
| `MAX_VIDEO_DURATION` | `60` | Max video duration in seconds | 30-120 |

---

## 🔄 Migration Configuration

### Database Migrations

The application uses Supabase's built-in migration system. To apply migrations:

1. Place SQL migration files in `backend/migrations/`
2. Run migrations using the Supabase CLI or dashboard

### Running Migrations

```bash
# Using Supabase CLI
supabase db push

# Or apply SQL directly
psql -h your-db-host -U postgres -d your-db-name -f backend/schema.sql
```

---

## 📝 Configuration Validation

The application validates configuration on startup. If required configuration is missing, the application will fail to start with a clear error message.

### Validation Checks

1. **Required Variables:** All variables marked as "Required" must be set
2. **Format Validation:** Variables are validated for correct format
3. **Connectivity Checks:** Database and Redis connections are tested
4. **API Key Validation:** AI provider API keys are validated

### Debugging Configuration Issues

If the application fails to start:

```bash
# Check logs for configuration errors
docker-compose -f docker-compose.prod.yml logs backend

# Test configuration manually
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

# Check required variables
required = ['SUPABASE_URL', 'SUPABASE_KEY', 'REDIS_URL', 'RUNWAY_API_KEY']
missing = [v for v in required if not os.environ.get(v)]
if missing:
    print(f'Missing required variables: {missing}')
else:
    print('All required variables are set')
"
```

---

## 📚 Examples

### Minimal Production Configuration

```bash
# .env for minimal production setup
APP_ENV=production
DEBUG=false
SECRET_KEY=your-secret-key

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-redis-password

RUNWAY_API_KEY=your-runway-key

AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
```

### Full Production Configuration

```bash
# .env for full production setup with all features
APP_ENV=production
APP_BASE_URL=https://beastar.io
DEBUG=false
SECRET_KEY=your-very-secure-secret-key
ALGORITHM=HS256
LOG_LEVEL=INFO
LOG_FILE=/var/log/beastar/beastar.log
RATE_LIMIT_ENABLED=true

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_STORAGE_BUCKET=beastar-media

# Redis
REDIS_URL=redis://beastar-redis:6379/0
REDIS_PASSWORD=your-redis-password

# AI Providers
RUNWAY_API_KEY=your-runway-key
KLING_API_KEY=your-kling-key

# AWS
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1

# Hive AI
HIVE_API_KEY=your-hive-key

# Payments
PAYMONGO_SECRET_KEY=your-paymongo-key
PAYMONGO_WEBHOOK_SECRET=your-paymongo-webhook-secret
STRIPE_SECRET_KEY=your-stripe-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret

# Celery
CELERY_WORKER_CONCURRENCY=8
CELERY_WORKER_MAX_TASKS_PER_CHILD=200
CELERY_WORKER_MAX_MEMORY_PER_CHILD=1000000

# Security
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_MINUTES=1440

# Analytics
GA_TRACKING_ID=UA-XXXXXX-Y
SENTRY_DSN=your-sentry-dsn
SENTRY_ENVIRONMENT=production
```

---

## 🔗 Related Documents

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) - Development roadmap
- [backend/schema.sql](backend/schema.sql) - Database schema
- [Makefile](Makefile) - Build commands
- [.env.example](.env.example) - Environment variable template

---

## 📞 Support

For configuration questions or issues:

1. Check this document for the variable you're configuring
2. Review the [DEPLOYMENT.md](DEPLOYMENT.md) for deployment-specific guidance
3. Check the logs for error messages
4. Verify all required variables are set
5. Test connectivity to external services (Supabase, Redis, etc.)

---

## 🎉 Summary

You now have a complete reference for all configuration options in BeAstar.io. This document should serve as your **single source of truth** for all environment variables and configuration settings.

**Remember:**
- Never commit `.env` files to version control
- Use strong, unique passwords and API keys
- Rotate credentials regularly
- Monitor configuration changes in production
- Test configuration changes in staging before deploying to production
