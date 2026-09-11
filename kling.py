"""
BeAstar.io — Kling client (BACKUP provider)
==============================================
Kling AI's direct API access and pricing tiers vary by account/region, and
several teams access it through aggregators (e.g. PiAPI, fal.ai) rather
than a single stable public endpoint. Rather than guess at exact field
names and risk shipping a broken integration, this client is structured to
match the *same interface* as RunwayClient — same method signatures, same
normalized status vocabulary — so swapping in the real endpoint/payload
shape is a small, contained change once you've confirmed it against
whichever Kling access path you sign up for (direct account vs.
aggregator).

Action item before launch: confirm with your actual Kling account/vendor:
  1. Base URL and auth scheme (API key header vs. signed request)
  2. Exact image-to-video payload field names
  3. Task status field names and enum values
Then fill in the three TODOs below — everything else (failover logic,
status normalization contract) is already correct and won't need to change.
"""

from __future__ import annotations

import os

import requests


class KlingClient:
    def __init__(self):
        api_key = os.environ.get("KLING_API_KEY")
        if not api_key:
            raise RuntimeError("KLING_API_KEY environment variable is not set")
        self._api_key = api_key
        # TODO: confirm actual base URL for your Kling access path
        self._base_url = os.environ.get("KLING_API_BASE", "https://api.klingai.com/v1")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def create_image_to_video_task(self, image_url: str, prompt: str, resolution: str) -> str:
        # TODO: confirm exact payload field names against your Kling account docs
        payload = {
            "image_url": image_url,
            "prompt": prompt,
            "resolution": resolution,
        }
        resp = requests.post(
            f"{self._base_url}/image2video",
            headers=self._headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["task_id"]

    def get_task_status(self, task_id: str) -> dict:
        resp = requests.get(
            f"{self._base_url}/image2video/{task_id}",
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        # TODO: confirm actual status enum values from your Kling account
        status_map = {
            "submitted": "processing",
            "processing": "processing",
            "succeed": "complete",
            "failed": "failed",
        }
        mapped = status_map.get(data.get("task_status"), "processing")

        return {
            "mapped_status": mapped,
            "output_url": data.get("video_url") if mapped == "complete" else None,
            "cost_usd": None,
        }
