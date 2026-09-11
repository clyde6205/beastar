"""
BeAstar.io - PayMongo/GCash Payment Integration
===============================================
Complete production-ready PayMongo API integration for GCash payments.

Features:
- GCash checkout via PayMongo
- Source creation for GCash
- Payment processing
- Webhook signature verification
- Error handling
"""

from __future__ import annotations

import hmac
import hashlib
import json
import os
from typing import Optional

import requests
from requests.exceptions import RequestException, Timeout

# Configuration
PAYMONGO_API_BASE = os.environ.get("PAYMONGO_API_BASE", "https://api.paymongo.com/v1")
PAYMONGO_SECRET_KEY = os.environ.get("PAYMONGO_SECRET_KEY")
PAYMONGO_WEBHOOK_SECRET = os.environ.get("PAYMONGO_WEBHOOK_SECRET")

# Timeout configuration
REQUEST_TIMEOUT = 30


class PayMongoError(Exception):
    """Base exception for PayMongo errors"""
    pass


class PayMongoAuthenticationError(PayMongoError):
    """Authentication failed"""
    pass


class PayMongoAPIError(PayMongoError):
    """API request failed"""
    pass


class PayMongoWebhookError(PayMongoError):
    """Webhook verification failed"""
    pass


def _get_headers() -> dict:
    """Get headers for PayMongo API requests"""
    if not PAYMONGO_SECRET_KEY:
        raise PayMongoAuthenticationError("PAYMONGO_SECRET_KEY not configured")
    
    return {
        "Authorization": f"Basic {PAYMONGO_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def _make_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make a request to PayMongo API"""
    headers = _get_headers()
    url = f"{PAYMONGO_API_BASE}{endpoint}"
    
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        
        if response.status_code == 401:
            raise PayMongoAuthenticationError("Invalid API key")
        elif response.status_code >= 400:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("message", f"HTTP {response.status_code}")
            raise PayMongoAPIError(f"PayMongo API error: {error_msg}")
        
        response.raise_for_status()
        return response.json()
        
    except Timeout as e:
        raise PayMongoAPIError(f"Request timed out: {str(e)}")
    except RequestException as e:
        raise PayMongoAPIError(f"Request failed: {str(e)}")


def create_gcash_source(
    amount_php: float,
    description: str,
    success_redirect_url: str,
    failed_redirect_url: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Create a GCash payment source via PayMongo.
    
    This is the first step in the GCash checkout flow.
    
    Args:
        amount_php: Payment amount in PHP
        description: Description of the payment
        success_redirect_url: URL to redirect to on success
        failed_redirect_url: URL to redirect to on failure
        metadata: Optional metadata to attach to the source
        
    Returns:
        Dict with source details including redirect URL
        
    Raises:
        PayMongoError: If source creation fails
    """
    payload = {
        "data": {
            "attributes": {
                "amount": int(amount_php * 100),  # Convert to cents
                "currency": "PHP",
                "description": description,
                "redirect": {
                    "success": success_redirect_url,
                    "failed": failed_redirect_url,
                },
                "type": "gcash",
            },
            "type": "sources",
        },
    }
    
    if metadata:
        payload["data"]["attributes"]["metadata"] = metadata
    
    result = _make_request("POST", "/sources", json=payload)
    
    return result.get("data", {})


def create_payment_from_chargeable_source(
    source_id: str,
    amount: float,
    description: str,
    currency: str = "PHP",
    metadata: Optional[dict] = None,
) -> dict:
    """
    Create a payment from a chargeable source.
    
    This is called when PayMongo sends a source.chargeable webhook.
    
    Args:
        source_id: ID of the chargeable source
        amount: Payment amount
        description: Payment description
        currency: Currency code
        metadata: Optional metadata
        
    Returns:
        Dict with payment details
        
    Raises:
        PayMongoError: If payment creation fails
    """
    payload = {
        "data": {
            "attributes": {
                "amount": int(amount * 100),  # Convert to cents
                "currency": currency,
                "description": description,
                "source": {
                    "id": source_id,
                    "type": "source",
                },
            },
            "type": "payments",
        },
    }
    
    if metadata:
        payload["data"]["attributes"]["metadata"] = metadata
    
    result = _make_request("POST", "/payments", json=payload)
    
    return result.get("data", {})


def get_payment(payment_id: str) -> dict:
    """
    Get payment details by ID.
    
    Args:
        payment_id: Payment ID
        
    Returns:
        Dict with payment details
    """
    result = _make_request("GET", f"/payments/{payment_id}")
    return result.get("data", {})


def get_source(source_id: str) -> dict:
    """
    Get source details by ID.
    
    Args:
        source_id: Source ID
        
    Returns:
        Dict with source details
    """
    result = _make_request("GET", f"/sources/{source_id}")
    return result.get("data", {})


def verify_webhook_signature(
    payload: bytes,
    signature: str,
) -> bool:
    """
    Verify PayMongo webhook signature.
    
    This is CRITICAL for security - never trust a webhook payload
    without verifying its signature.
    
    Args:
        payload: Raw request body bytes
        signature: Signature from the X-PayMongo-Signature header
        
    Returns:
        True if signature is valid, False otherwise
        
    Raises:
        PayMongoWebhookError: If verification cannot be performed
    """
    if not PAYMONGO_WEBHOOK_SECRET:
        raise PayMongoWebhookError("PAYMONGO_WEBHOOK_SECRET not configured")
    
    try:
        # Extract timestamp and signatures from header
        # Format: "t=1234567890,v1=signature,v0=signature"
        parts = signature.split(",")
        timestamp = None
        signatures = {}
        
        for part in parts:
            if part.startswith("t="):
                timestamp = part[2:]
            elif "=" in part:
                key, value = part.split("=", 1)
                signatures[key] = value
        
        if not timestamp or not signatures:
            raise PayMongoWebhookError("Invalid signature format")
        
        # Construct the signed payload
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        
        # Compute expected signature
        expected_signature = hmac.new(
            PAYMONGO_WEBHOOK_SECRET.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        
        # Check against v1 signature (most common)
        if "v1" in signatures:
            return hmac.compare_digest(signatures["v1"], expected_signature)
        
        # Check against v0 signature (legacy)
        if "v0" in signatures:
            return hmac.compare_digest(signatures["v0"], expected_signature)
        
        return False
        
    except Exception as e:
        raise PayMongoWebhookError(f"Webhook verification failed: {str(e)}")


def parse_webhook_payload(
    payload: bytes,
    signature: str,
) -> dict:
    """
    Parse and verify a PayMongo webhook payload.
    
    Args:
        payload: Raw request body bytes
        signature: Signature from the X-PayMongo-Signature header
        
    Returns:
        Dict with parsed webhook data
        
    Raises:
        PayMongoWebhookError: If verification fails
    """
    if not verify_webhook_signature(payload, signature):
        raise PayMongoWebhookError("Invalid webhook signature")
    
    try:
        data = json.loads(payload.decode('utf-8'))
        return data
    except json.JSONDecodeError as e:
        raise PayMongoWebhookError(f"Invalid JSON payload: {str(e)}")


# Test function for webhook verification
def test_webhook_verification():
    """Test webhook signature verification"""
    if not PAYMONGO_WEBHOOK_SECRET:
        print("PAYMONGO_WEBHOOK_SECRET not set - cannot test")
        return
    
    test_payload = b'{"type": "payment.success", "data": {"id": "test"}}'
    
    # Compute expected signature
    import time
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{test_payload.decode('utf-8')}"
    expected_signature = hmac.new(
        PAYMONGO_WEBHOOK_SECRET.encode('utf-8'),
        signed_payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    
    signature = f"t={timestamp},v1={expected_signature}"
    
    # Verify
    is_valid = verify_webhook_signature(test_payload, signature)
    print(f"Webhook verification test: {'PASSED' if is_valid else 'FAILED'}")


if __name__ == "__main__":
    test_webhook_verification()
