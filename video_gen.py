"""
BeAstar.io — Video generation provider layer
================================================
A single interface (`VideoGenProvider`) so the rest of the app never talks
to Runway/Kling/etc directly. `generate_with_fallback()` tries the primary
provider first and automatically fails over to the backup if the primary
errors out or times out — this is the "automatic backup provider"
requirement: a provider outage should degrade to a slower/different
renderer, not a broken app.

Primary: Runway (Gen-4 Turbo image-to-video) — real, documented API shape.
Backup:  Kling — same interface, endpoint/auth confirmed against your
         actual Kling account before going live (see KlingProvider notes).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoGenResult:
    provider_name: str
    provider_job_id: str
    status: str          # 'processing' | 'complete' | 'failed'
    output_url: Optional[str] = None
    cost_usd: Optional[float] = None


class VideoGenProvider(ABC):
    name: str

    @abstractmethod
    def start_generation(self, image_url: str, prompt: str, resolution: str) -> str:
        """Submits a generation task. Returns the provider's job id."""

    @abstractmethod
    def poll_status(self, provider_job_id: str) -> VideoGenResult:
        """Checks task status. Called repeatedly until complete/failed."""


class ProviderUnavailableError(Exception):
    """Raised when a provider is down, rate-limited, or errors out —
    signals the orchestrator to fail over to the backup provider."""


# --------------------------------------------------------------------------
# Runway (primary) — see app/providers/runway.py for the real implementation
# --------------------------------------------------------------------------

class RunwayProvider(VideoGenProvider):
    name = "runway"

    def __init__(self):
        from app.providers.runway import RunwayClient
        self._client = RunwayClient()

    def start_generation(self, image_url: str, prompt: str, resolution: str) -> str:
        try:
            return self._client.create_image_to_video_task(
                image_url=image_url, prompt=prompt, resolution=resolution
            )
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any
            # Runway failure should trigger failover, not bubble up raw.
            raise ProviderUnavailableError(f"Runway request failed: {exc}") from exc

    def poll_status(self, provider_job_id: str) -> VideoGenResult:
        try:
            status = self._client.get_task_status(provider_job_id)
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(f"Runway poll failed: {exc}") from exc

        return VideoGenResult(
            provider_name=self.name,
            provider_job_id=provider_job_id,
            status=status["mapped_status"],
            output_url=status.get("output_url"),
            cost_usd=status.get("cost_usd"),
        )


# --------------------------------------------------------------------------
# Kling (backup) — same interface. Kling's public API access/auth varies by
# account tier; confirm the exact base URL and auth scheme on your account
# before launch. Structure below follows their documented async
# task-creation + polling pattern, matching Runway's shape intentionally so
# failover is a clean swap.
# --------------------------------------------------------------------------

class KlingProvider(VideoGenProvider):
    name = "kling"

    def __init__(self):
        from app.providers.kling import KlingClient
        self._client = KlingClient()

    def start_generation(self, image_url: str, prompt: str, resolution: str) -> str:
        try:
            return self._client.create_image_to_video_task(
                image_url=image_url, prompt=prompt, resolution=resolution
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(f"Kling request failed: {exc}") from exc

    def poll_status(self, provider_job_id: str) -> VideoGenResult:
        try:
            status = self._client.get_task_status(provider_job_id)
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(f"Kling poll failed: {exc}") from exc

        return VideoGenResult(
            provider_name=self.name,
            provider_job_id=provider_job_id,
            status=status["mapped_status"],
            output_url=status.get("output_url"),
            cost_usd=status.get("cost_usd"),
        )


# --------------------------------------------------------------------------
# Orchestration: try primary, fail over to backup automatically
# --------------------------------------------------------------------------

PRIMARY: VideoGenProvider | None = None
BACKUP: VideoGenProvider | None = None


def _get_primary() -> VideoGenProvider:
    global PRIMARY
    if PRIMARY is None:
        PRIMARY = RunwayProvider()
    return PRIMARY


def _get_backup() -> VideoGenProvider:
    global BACKUP
    if BACKUP is None:
        BACKUP = KlingProvider()
    return BACKUP


def start_generation_with_fallback(image_url: str, prompt: str, resolution: str) -> tuple[str, str]:
    """
    Returns (provider_name, provider_job_id). Tries the primary provider;
    on ProviderUnavailableError, automatically retries against the backup.
    Callers should persist provider_name alongside provider_job_id so
    poll_generation_with_fallback knows which client to poll later.
    """
    try:
        job_id = _get_primary().start_generation(image_url, prompt, resolution)
        return _get_primary().name, job_id
    except ProviderUnavailableError:
        job_id = _get_backup().start_generation(image_url, prompt, resolution)
        return _get_backup().name, job_id


def poll_generation_with_fallback(
    provider_name: str, provider_job_id: str, max_attempts: int = 30, delay_seconds: float = 2.0
) -> VideoGenResult:
    """
    Polls whichever provider actually owns this job. Note: fallback only
    happens at *submission* time (start_generation_with_fallback) — once a
    job is running on a provider, we poll that same provider through to
    completion. A mid-flight provider outage on an already-running job
    should be retried as a fresh submission, not silently reassigned.
    """
    provider = _get_primary() if provider_name == "runway" else _get_backup()

    for _ in range(max_attempts):
        result = provider.poll_status(provider_job_id)
        if result.status in ("complete", "failed"):
            return result
        time.sleep(delay_seconds)

    return VideoGenResult(
        provider_name=provider_name,
        provider_job_id=provider_job_id,
        status="failed",
    )
