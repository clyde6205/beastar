"""
BeAstar.io — GCash payments via PayMongo
===========================================
GCash itself doesn't offer a direct public merchant API for an app at your
stage — access goes through a licensed payment gateway. PayMongo is the
standard route for Philippines-based apps (PH-based company, PHP settlement,
GCash/GrabPay/Maya/cards/over-the-counter all through one integration).

Flow (matches PayMongo's documented Source-resource pattern):
  1. Create a Source (amount + currency + type='gcash' + redirect URLs)
  2. Redirect the user to source.checkout_url — they authorize in GCash
  3. GCash redirects back to your success/failed URL
  4. PayMongo sends a webhook when the source becomes 'chargeable'
  5. On that webhook, create a Payment against the chargeable source to
     actually capture the funds

Docs: https://developers.paymongo.com/v1/docs/accepting-gcash-payments
Requires a PayMongo account (PH business registration needed to go live —
sandbox/test keys work without it for development).
"""

from __future__ import annotations

import base64
import os

import requests

PAYMONGO_API_BASE = "https://api.paymongo.com/v1"


def _auth_header() -> dict:
    secret_key = os.environ.get("PAYMONGO_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("PAYMONGO_SECRET_KEY environment variable is not set")
    encoded = base64.b64encode(f"{secret_key}:".encode()).decode()
    return {"Authorization": f"Basic {encoded}", "Content-Type": "application/json"}


def create_gcash_source(
    amount_php: float,
    description: str,
    success_redirect_url: str,
    failed_redirect_url: str,
) -> dict:
    """
    Creates a GCash payment Source. Returns the PayMongo source object —
    redirect the user to result['attributes']['redirect']['checkout_url'].

    amount_php is in whole pesos (e.g. 4.99 USD tier priced at ~279 PHP);
    PayMongo expects the amount in centavos (smallest unit), so this
    multiplies by 100.
    """
    payload = {
        "data": {
            "attributes": {
                "amount": int(round(amount_php * 100)),
                "redirect": {
                    "success": success_redirect_url,
                    "failed": failed_redirect_url,
                },
                "type": "gcash",
                "currency": "PHP",
                "description": description,
            }
        }
    }
    resp = requests.post(
        f"{PAYMONGO_API_BASE}/sources",
        headers=_auth_header(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def create_payment_from_chargeable_source(source_id: str, amount_php: float, description: str) -> dict:
    """
    Call this from your webhook handler once PayMongo notifies you the
    source's status is 'chargeable' — this is the step that actually
    captures the funds.
    """
    payload = {
        "data": {
            "attributes": {
                "amount": int(round(amount_php * 100)),
                "currency": "PHP",
                "description": description,
                "source": {"id": source_id, "type": "source"},
            }
        }
    }
    resp = requests.post(
        f"{PAYMONGO_API_BASE}/payments",
        headers=_auth_header(),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    PayMongo signs webhooks with HMAC-SHA256 using your webhook signing
    secret. ALWAYS verify before trusting a webhook payload — this is what
    stops someone from POSTing a fake "payment succeeded" event at your
    endpoint to get free credits.

    Implementation left as a TODO wired to `hmac.compare_digest` once you
    have your actual webhook signing secret from the PayMongo dashboard —
    the exact header parsing (PayMongo sends `t=<timestamp>,te=<test sig>`
    or `t=<timestamp>,li=<live sig>`) should be copied verbatim from their
    current webhook docs at integration time, since signature formats are
    exactly the kind of detail that must match precisely.
    """
    raise NotImplementedError(
        "Wire this to PayMongo's documented webhook signature verification "
        "before accepting any webhook as trusted."
    )
