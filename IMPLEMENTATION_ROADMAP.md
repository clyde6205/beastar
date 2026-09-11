# BeAstar - Production Implementation Roadmap

## Executive Summary

This document outlines the complete implementation plan to turn the existing BeAstar codebase into a production-ready, globally scalable social mobile application.

**Current State**: ~60-70% complete with critical gaps in security, video generation, and storage.
**Target State**: 100% production-ready with all features working end-to-end.

## Phase 1: Critical Security & Core Pipeline (PRIORITY)

### 1.1 Face Verification System (SECURITY CRITICAL)
**Status**: ❌ NOT IMPLEMENTED - Currently just simulates success
**Impact**: Security vulnerability - anyone can bypass verification

**Implementation Plan**:
- [ ] Integrate AWS Rekognition for liveness detection
- [ ] Implement face matching against uploaded selfie
- [ ] Add known public figure database check
- [ ] Store face embedding ID (not raw biometric data)
- [ ] Implement retry handling and failure states
- [ ] Add audit logging

**Files to Modify**:
- `backend/app/main.py` - `verify_face()` endpoint
- `backend/app/providers/face_verification.py` - NEW FILE
- `backend/requirements.txt` - Add boto3

**Dependencies**:
- AWS Rekognition API key
- Face comparison algorithm

---

### 1.2 Video Generation Pipeline
**Status**: ⚠️ PARTIALLY IMPLEMENTED - Core structure exists but key functions are stubs

**Sub-tasks**:

#### 1.2.1 AI Disclosure Watermarking
**Status**: ❌ NOT IMPLEMENTED - Just copies file without watermark
**Files**: `backend/app/providers/video_gen.py`

**Implementation**:
```python
# Use FFmpeg to burn disclosure into video
ffmpeg -i input.mp4 -vf "drawtext=text='AI-Generated Content':x=w-tw-10:y=h-th-10:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.5" output.mp4
```

#### 1.2.2 Supabase Storage Upload
**Status**: ❌ NOT IMPLEMENTED - Returns placeholder URL
**Files**: `backend/app/providers/video_gen.py`, `backend/app/storage/selfie_upload.py`

**Implementation**:
- Use Supabase Storage Python SDK
- Generate signed URLs for secure access
- Implement proper file naming convention

#### 1.2.3 Content Moderation
**Status**: ⚠️ STUBBED - Providers exist but not configured
**Files**: `backend/app/providers/content_moderation.py`

**Implementation**:
- Configure AWS Rekognition (primary)
- Configure Hive AI (fallback)
- Add local development mode
- Implement video frame extraction for moderation

---

### 1.3 Background Job Processing
**Status**: ⚠️ PARTIALLY WORKING - Celery configured but cleanup tasks are placeholders

**Implementation**:
- [ ] Complete `cleanup_expired_jobs()` with actual database queries
- [ ] Implement job timeout handling
- [ ] Add job retry with exponential backoff
- [ ] Implement abandoned job cleanup

---

## Phase 2: Mobile App Completion

### 2.1 Video Upload for Dream Updates
**Status**: ❌ NOT WORKING - Passes local URI instead of uploaded URL
**File**: `mobile/src/screens/PostDreamUpdateScreen.tsx`

**Implementation**:
- Add video upload function similar to `uploadSelfie`
- Upload video to storage before creating dream update
- Pass storage URL to backend

### 2.2 Follow State Persistence
**Status**: ⚠️ LOCAL ONLY - Follow state not persisted from server
**File**: `mobile/src/screens/DreamThreadScreen.tsx`

**Implementation**:
- Add backend endpoint to check if user follows a thread
- Modify mobile to fetch real follow state
- Sync local state with server

### 2.3 Verification State Persistence
**Status**: ❌ NOT PERSISTED - Verification state lost on app restart
**File**: `mobile/src/context/AuthContext.tsx`

**Implementation**:
- Save verification state to SecureStore
- Restore on app launch
- Sync with backend

---

## Phase 3: Webhook Security

### 3.1 Stripe Webhook Signature Verification
**Status**: ❌ COMMENTED OUT - Security vulnerability
**File**: `backend/app/main.py`

**Implementation**:
- Uncomment and implement signature verification
- Use STRIPE_WEBHOOK_SECRET environment variable
- Reject unauthenticated webhooks

### 3.2 PayMongo Webhook Signature Verification
**Status**: ❌ COMMENTED OUT - Security vulnerability
**File**: `backend/app/main.py`

**Implementation**:
- Uncomment and implement signature verification
- Use PAYMONGO_WEBHOOK_SECRET environment variable
- Reject unauthenticated webhooks

---

## Phase 4: Production Infrastructure

### 4.1 Docker Configuration
- [ ] Create Dockerfile for backend
- [ ] Create docker-compose.yml for local development
- [ ] Configure multi-stage builds
- [ ] Add health checks

### 4.2 CI/CD Pipeline
- [ ] GitHub Actions workflows
- [ ] Automated testing
- [ ] Docker image building
- [ ] Deployment scripts

### 4.3 Monitoring & Observability
- [ ] Add Prometheus metrics
- [ ] Configure structured logging
- [ ] Add error tracking (Sentry)
- [ ] Implement health checks

---

## Phase 5: Testing

### 5.1 Backend Tests
- [ ] Unit tests for all providers
- [ ] Integration tests for API endpoints
- [ ] Database migration tests
- [ ] Authentication tests

### 5.2 Mobile Tests
- [ ] Component tests
- [ ] API integration tests
- [ ] Navigation tests
- [ ] E2E tests with Detox

---

## Phase 6: Documentation

### 6.1 Deployment Documentation
- [ ] Local development setup guide
- [ ] Production deployment guide
- [ ] Configuration reference
- [ ] Environment variables documentation

### 6.2 API Documentation
- [ ] Complete OpenAPI/Swagger docs
- [ ] Webhook documentation
- [ ] Integration guides

---

## Implementation Priority Matrix

| Priority | Category | Items | Estimated Time |
|----------|----------|-------|----------------|
| P0 (CRITICAL) | Security | Face verification, webhook signing | 2-3 days |
| P0 (CRITICAL) | Core Feature | Video generation pipeline | 2-3 days |
| P1 (HIGH) | Core Feature | Content moderation, storage upload | 1-2 days |
| P1 (HIGH) | Mobile | Video upload, follow state | 1-2 days |
| P2 (MEDIUM) | Infrastructure | Docker, CI/CD | 1-2 days |
| P2 (MEDIUM) | Testing | Backend tests | 1 day |
| P3 (LOW) | Polish | Mobile tests, documentation | 1-2 days |

---

## Success Criteria

### MVP (Minimum Viable Production)
- [ ] Face verification works with real liveness detection
- [ ] Video generation completes end-to-end
- [ ] Videos can be played in mobile app
- [ ] Content moderation prevents unsafe content
- [ ] Webhooks are secure
- [ ] All core user journeys work

### Full Production
- [ ] All features implemented
- [ ] All tests passing
- [ ] Security audit complete
- [ ] Performance optimized
- [ ] Documentation complete

---

## Risk Assessment

### High Risk Items
1. **Face verification vendor selection** - Need to choose and integrate a liveness detection service
2. **AI provider costs** - Runway/Kling costs need to be monitored and controlled
3. **Content moderation accuracy** - False positives/negatives affect user experience

### Medium Risk Items
1. **Video generation reliability** - Provider API changes could break integration
2. **Mobile app performance** - Video processing on mobile devices
3. **Storage costs** - Video storage can be expensive at scale

### Mitigation Strategies
1. Implement provider failover (Runway → Kling)
2. Add cost tracking and rate limiting
3. Use multiple moderation vendors for redundancy
4. Implement comprehensive monitoring

---

## Next Steps

1. **Start with Phase 1** - Critical security and core pipeline
2. **Implement face verification** - This is the biggest security gap
3. **Complete video generation** - This is the core product feature
4. **Fix storage upload** - Required for video playback
5. **Secure webhooks** - Critical for payments
6. **Complete mobile wiring** - Connect all screens to real backend
7. **Add infrastructure** - Docker, CI/CD, monitoring
8. **Add tests** - Ensure reliability
9. **Document everything** - For deployment and maintenance

---

## Resource Requirements

### External Services Required
- AWS Rekognition (or alternative liveness detection)
- Runway ML API key
- Kling AI API key (fallback)
- AWS S3 or Supabase Storage
- Redis for Celery
- Stripe account
- PayMongo account

### Development Resources
- Docker
- GitHub Actions
- Testing frameworks (pytest, jest)
- Monitoring tools (Prometheus, Sentry)

---

## Timeline Estimate

**Total Estimated Time**: 10-14 days
- Phase 1: 4-6 days
- Phase 2: 2-3 days
- Phase 3: 1 day
- Phase 4: 1-2 days
- Phase 5: 1-2 days
- Phase 6: 1 day

**Team Size**: 1-2 engineers (full-stack + mobile)
