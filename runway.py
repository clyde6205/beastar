"""
BeAstar.io — Runway client
=============================
Matches Runway's documented image-to-video API:
  - Bearer token auth
  - Required `X-Runway-Version` header (documented value: 2024-11-06)
  - Async task-creation endpoint, poll for status/result
  - Accepts gen4_turbo / gen3a_turbo as the underlying model id

Docs: https://docs.dev.runwayml.com/guides/using-the-api/
Confirm current pricing/model ids on your account before launch — Runway
adds new model versions periodically (this targets gen4_turbo).
"""

from __future__ import annotations

import os

import requests

RUNWAY_API_BASE = "https://api.runwayml.com/v1"
RUNWAY_API_VERSION = "2024-11-06"

RESOLUTION_TO_RUNWAY_RATIO = {
    # Runway's image-to-video endpoint takes an aspect ratio, not an
    # arbitrary resolution — map our tier resolutions to the closest
    # supported portrait ratio for vertical (TikTok/IG/Shorts) output.
    "720p": "768:1280",
    "1080p": "1080:1920",
    "4k": "1080:1920",  # Runway caps below true 4K; see note in README on
                         # upscaling the 1080p output for the Megastar tier.
}


class RunwayClient:
    def __init__(self):
        api_key = os.environ.get("RUNWAY_API_KEY")
        if not api_key:
            raise RuntimeError("RUNWAY_API_KEY environment variable is not set")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": RUNWAY_API_VERSION,
            "Content-Type": "application/json",
        }

    def create_image_to_video_task(self, image_url: str, prompt: str, resolution: str) -> str:
        """Submits a task, returns Runway's task id for polling."""
        payload = {
            "model": "gen4_turbo",
            "promptImage": image_url,
            "promptText": prompt,
            "ratio": RESOLUTION_TO_RUNWAY_RATIO.get(resolution, "768:1280"),
        }
        resp = requests.post(
            f"{RUNWAY_API_BASE}/image_to_video",
            headers=self._headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def get_task_status(self, task_id: str) -> dict:
        """
        Returns a normalized dict: {'mapped_status', 'output_url', 'cost_usd'}.
        Runway's raw statuses (PENDING/RUNNING/SUCCEEDED/FAILED) are mapped
        to our internal ('processing'/'complete'/'failed') so the rest of
        the app doesn't need to know provider-specific vocabulary.
        """
        resp = requests.get(
            f"{RUNWAY_API_BASE}/tasks/{task_id}",
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        status_map = {
            "PENDING": "processing",
            "RUNNING": "processing",
            "SUCCEEDED": "complete",
            "FAILED": "failed",
        }
        mapped = status_map.get(data.get("status"), "processing")

        output_url = None
        if mapped == "complete":
            outputs = data.get("output", [])
            output_url = outputs[0] if outputs else None

        return {
            "mapped_status": mapped,
            "output_url": output_url,
            # Runway doesn't return per-task cost in the API response as of
            # this writing — pull actual spend from your Runway billing/usage
            # dashboard periodically and reconcile against render_cost_usd,
            # or hardcode a per-second estimate here if your plan is fixed-rate.
            "cost_usd": None,
        }
