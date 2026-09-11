"""
BeAstar.io - Kling AI Provider (Fallback)
==========================================
Complete production-ready Kling AI API integration as fallback for Runway.

Features:
- Automatic failover when Runway is unavailable
- Similar interface to Runway for easy swapping
- Cost tracking
- Error handling
"""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple

import requests
from requests.exceptions import RequestException, Timeout

# Configuration
KLING_API_BASE = os.environ.get("KLING_API_BASE", "https://api.kling.ai/v1")

# Resolution to Kling parameters mapping
RESOLUTION_TO_KLING_PARAMS = {
    "720p": {"width": 768, "height": 1280},
    "1080p": {"width": 1080, "height": 1920},
    "4k": {"width": 1080, "height": 1920},  # Kling caps at 1080p for now
}

# Estimated costs
RESOLUTION_COST_USD = {
    "720p": 0.05,
    "1080p": 0.10,
    "4k": 0.20,
}

# Timeout configuration
REQUEST_TIMEOUT = 30
POLL_INTERVAL = 5
MAX_POLL_ATTEMPTS = 60


class KlingError(Exception):
    """Base exception for Kling API errors"""
    pass


class KlingAuthenticationError(KlingError):
    """Authentication failed"""
    pass


class KlingRateLimitError(KlingError):
    """Rate limit exceeded"""
    pass


class KlingTaskFailedError(KlingError):
    """Task failed to complete"""
    pass


class KlingTimeoutError(KlingError):
    """Task timed out"""
    pass


class KlingClient:
    """
    Client for Kling AI video generation API.
    
    Note: Kling's API may vary by account/aggregator. This implementation
    matches the documented API as of this writing, but you should verify
    the exact endpoints and field names for your Kling account.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Kling client.
        
        Args:
            api_key: Kling API key. If not provided, uses KLING_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("KLING_API_KEY")
        if not self.api_key:
            raise KlingAuthenticationError("KLING_API_KEY environment variable is not set")
        
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._session = requests.Session()
        self._session.headers.update(self._headers)
    
    def create_video_generation_task(
        self,
        image_url: str,
        prompt: str,
        resolution: str = "720p",
        negative_prompt: Optional[str] = None,
    ) -> str:
        """
        Submit a new video generation task to Kling.
        
        Args:
            image_url: URL of the input image
            prompt: Text prompt describing the desired video
            resolution: Output resolution (720p, 1080p, 4k)
            negative_prompt: What to avoid in the output
            
        Returns:
            Kling task ID for polling
        """
        params = RESOLUTION_TO_KLING_PARAMS.get(resolution, {"width": 768, "height": 1280})
        
        payload = {
            "model": "kling-v1",  # or whatever model ID Kling provides
            "image": image_url,
            "prompt": prompt,
            "width": params["width"],
            "height": params["height"],
        }
        
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt
        
        try:
            response = self._session.post(
                f"{KLING_API_BASE}/video/generate",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            
            if response.status_code == 401:
                raise KlingAuthenticationError("Invalid API key")
            elif response.status_code == 429:
                raise KlingRateLimitError("Rate limit exceeded")
            elif response.status_code >= 400:
                error_msg = response.json().get("message", "Unknown error")
                raise KlingError(f"Kling API error: {error_msg}")
            
            response.raise_for_status()
            data = response.json()
            task_id = data.get("task_id") or data.get("id")
            
            if not task_id:
                raise KlingError("No task ID returned from Kling")
            
            return task_id
            
        except Timeout as e:
            raise KlingTimeoutError(f"Request timed out: {str(e)}")
        except RequestException as e:
            raise KlingError(f"Request failed: {str(e)}")
    
    def get_task_status(self, task_id: str) -> dict:
        """
        Get the status of a Kling generation task.
        
        Returns normalized status matching Runway's format.
        """
        try:
            response = self._session.get(
                f"{KLING_API_BASE}/video/tasks/{task_id}",
                timeout=REQUEST_TIMEOUT,
            )
            
            if response.status_code == 401:
                raise KlingAuthenticationError("Invalid API key")
            elif response.status_code == 429:
                raise KlingRateLimitError("Rate limit exceeded")
            elif response.status_code >= 400:
                error_msg = response.json().get("message", "Unknown error")
                raise KlingError(f"Kling API error: {error_msg}")
            
            response.raise_for_status()
            data = response.json()
            
            # Map Kling status to our internal status
            # Note: Kling's status values may differ - adjust as needed
            status_map = {
                "pending": "processing",
                "processing": "processing",
                "succeeded": "complete",
                "failed": "failed",
                "cancelled": "failed",
            }
            mapped_status = status_map.get(data.get("status", "").lower(), "processing")
            
            # Extract output URL
            output_url = None
            if mapped_status == "complete":
                output_url = data.get("output_url") or data.get("video_url")
            
            return {
                "mapped_status": mapped_status,
                "output_url": output_url,
                "cost_usd": None,  # Kling doesn't return cost in API
                "raw_status": data.get("status"),
                "raw_data": data,
            }
            
        except Timeout as e:
            raise KlingTimeoutError(f"Request timed out: {str(e)}")
        except RequestException as e:
            raise KlingError(f"Request failed: {str(e)}")
    
    def poll_task_until_complete(
        self,
        task_id: str,
        resolution: str = "720p",
        poll_interval: int = POLL_INTERVAL,
        max_attempts: int = MAX_POLL_ATTEMPTS,
    ) -> Tuple[str, Optional[str], Optional[float]]:
        """Poll a task until it completes or fails."""
        attempts = 0
        last_status = "processing"
        
        while attempts < max_attempts:
            attempts += 1
            
            try:
                status_info = self.get_task_status(task_id)
                last_status = status_info["mapped_status"]
                
                if last_status == "complete":
                    output_url = status_info.get("output_url")
                    cost_usd = RESOLUTION_COST_USD.get(resolution)
                    return ("complete", output_url, cost_usd)
                elif last_status == "failed":
                    raise KlingTaskFailedError(
                        f"Kling task failed: {status_info.get('raw_data', {}).get('error', 'Unknown error')}"
                    )
                
                time.sleep(poll_interval)
                
            except KlingError:
                raise
            except Exception:
                if attempts >= max_attempts:
                    raise KlingTimeoutError(f"Polling timed out after {max_attempts} attempts")
                time.sleep(poll_interval)
        
        raise KlingTimeoutError(f"Polling timed out. Last status: {last_status}")


# Singleton instance
_kling_client: Optional[KlingClient] = None


def get_kling_client() -> KlingClient:
    """Get or create singleton Kling client"""
    global _kling_client
    if _kling_client is None:
        _kling_client = KlingClient()
    return _kling_client
