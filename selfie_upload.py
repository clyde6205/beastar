"""
BeAstar.io — Selfie upload storage layer
===========================================
Handles the real path an uploaded selfie takes before it can be passed to
Runway/Kling as `image_url`:

  1. Validate (file type, size, dimensions)
  2. Run a content-safety pre-check (block anything that isn't a usable
     face photo before it ever reaches storage or a paid generation call)
  3. Upload to a private Supabase Storage bucket
  4. Return a signed URL — short-lived, not a permanently public file —
     since this is someone's face, not a shareable asset

This does NOT do the liveness/self-match/known-public-figure check — that
stays in the /auth/{user_id}/verify-face flow (main.py) and runs once at
verification time. This module runs on every subsequent generation upload,
where the concern is "is this a usable, safe image", not "is this really
you" (already established at verification).
"""

from __future__ import annotations

import os
import uuid
from datetime import timedelta

from PIL import Image
from supabase import Client

STORAGE_BUCKET = "user-selfies"
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MIN_DIMENSION_PX = 512   # below this, generation quality suffers badly
MAX_DIMENSION_PX = 4096  # above this, just wasted bandwidth/storage
SIGNED_URL_TTL_SECONDS = 60 * 30  # 30 minutes — long enough for a
                                  # provider to fetch it, short enough that
                                  # a leaked URL doesn't stay valid


class UploadValidationError(Exception):
    """Raised for any reason a selfie upload should be rejected before it
    reaches storage or costs a generation credit."""


def validate_image_bytes(content_type: str, file_bytes: bytes) -> Image.Image:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(
            f"Unsupported file type '{content_type}'. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise UploadValidationError(
            f"File too large ({len(file_bytes)} bytes). Max {MAX_FILE_SIZE_BYTES} bytes."
        )

    try:
        img = Image.open(io_bytes(file_bytes))
        img.verify()  # raises if not a valid image / corrupted
        img = Image.open(io_bytes(file_bytes))  # re-open: verify() consumes the file object
    except Exception as exc:
        raise UploadValidationError(f"File is not a valid image: {exc}") from exc

    width, height = img.size
    if width < MIN_DIMENSION_PX or height < MIN_DIMENSION_PX:
        raise UploadValidationError(
            f"Image too small ({width}x{height}). Minimum {MIN_DIMENSION_PX}px on each side."
        )
    if width > MAX_DIMENSION_PX or height > MAX_DIMENSION_PX:
        raise UploadValidationError(
            f"Image too large ({width}x{height}). Maximum {MAX_DIMENSION_PX}px on each side."
        )

    return img


def io_bytes(file_bytes: bytes):
    import io
    return io.BytesIO(file_bytes)


def run_content_safety_check(file_bytes: bytes) -> None:
    """
    Placeholder for a real content-moderation API call (e.g. AWS
    Rekognition Content Moderation, Google Cloud Vision SafeSearch, or
    Hive Moderation) run BEFORE storage and BEFORE any paid generation
    call. Must reject: no-face-detected images, explicit/NSFW content,
    and (per the compliance checklist) images matching a known public
    figure — the latter is enforced at verify-face time, but a defense-in-
    depth check here catches someone re-uploading a different photo later.

    Raise UploadValidationError to reject. Left unimplemented rather than
    faked — wire this to your chosen moderation vendor before launch;
    shipping without it is the single biggest content-risk gap in this app.
    """
    raise NotImplementedError(
        "Wire a real content-moderation vendor call here before accepting "
        "uploads in production."
    )


def upload_selfie(
    supabase_client: Client, user_id: str, content_type: str, file_bytes: bytes
) -> str:
    """
    Validates, safety-checks, and stores a selfie. Returns a signed URL
    suitable for passing as `image_url` to the video-gen provider layer.

    Raises UploadValidationError on any validation/safety failure — callers
    (the FastAPI endpoint) should catch this and return HTTP 400 with the
    message, not a raw 500.
    """
    validate_image_bytes(content_type, file_bytes)
    run_content_safety_check(file_bytes)

    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    storage_path = f"{user_id}/{uuid.uuid4().hex}.{ext}"

    supabase_client.storage.from_(STORAGE_BUCKET).upload(
        storage_path,
        file_bytes,
        file_options={"content-type": content_type},
    )

    signed = supabase_client.storage.from_(STORAGE_BUCKET).create_signed_url(
        storage_path, SIGNED_URL_TTL_SECONDS
    )
    return signed["signedURL"]


def delete_selfie(supabase_client: Client, storage_path: str) -> None:
    """
    Called once a generation job using this selfie completes (success or
    failure) — no reason to retain the raw uploaded image longer than the
    render needs it. Face embedding for future verification is stored
    separately (see supabase_client.mark_user_verified), not this file.
    """
    supabase_client.storage.from_(STORAGE_BUCKET).remove([storage_path])
