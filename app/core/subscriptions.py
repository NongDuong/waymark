import json
import os
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import HTTPException


PRODUCTS = {
    os.getenv("IAP_STANDARD_IOS_PRODUCT_ID", "waymark.standard.yearly"): "standard",
    os.getenv("IAP_PREMIUM_IOS_PRODUCT_ID", "waymark.premium.yearly"): "premium",
    os.getenv("IAP_STANDARD_ANDROID_PRODUCT_ID", "waymark.standard.yearly"): "standard",
    os.getenv("IAP_PREMIUM_ANDROID_PRODUCT_ID", "waymark.premium.yearly"): "premium",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def effective_tier(user) -> str:
    tier = getattr(user, "subscription_tier", "normal") or "normal"
    expires_at = getattr(user, "subscription_expires_at", None)
    if tier == "normal" or not expires_at:
        return "normal"
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return tier if expires_at > utcnow() else "normal"


def entitlement(tier: str) -> dict:
    premium = tier == "premium"
    paid = tier in ("standard", "premium")
    return {
        "pin_visibility_days": 365 if paid else 30,
        "can_upload_library_photos": premium,
        "can_record_short_video": premium,
        "short_video_min_seconds": 5 if premium else None,
        "short_video_max_seconds": 10 if premium else None,
        "ads_enabled": not premium,
    }


def _parse_ms(value) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def verify_apple(product_id: str, receipt_data: Optional[str]) -> dict:
    if not receipt_data:
        raise HTTPException(400, "receipt_data is required for Apple purchases")
    payload = {"receipt-data": receipt_data, "exclude-old-transactions": True}
    secret = os.getenv("APPLE_IAP_SHARED_SECRET")
    if secret:
        payload["password"] = secret
    response = requests.post("https://buy.itunes.apple.com/verifyReceipt", json=payload, timeout=15)
    data = response.json()
    if data.get("status") == 21007:
        response = requests.post("https://sandbox.itunes.apple.com/verifyReceipt", json=payload, timeout=15)
        data = response.json()
    if data.get("status") != 0:
        raise HTTPException(400, f"Apple receipt verification failed ({data.get('status')})")
    candidates = [x for x in data.get("latest_receipt_info", []) if x.get("product_id") == product_id]
    if not candidates:
        candidates = [x for x in data.get("receipt", {}).get("in_app", []) if x.get("product_id") == product_id]
    if not candidates:
        raise HTTPException(400, "Product was not found in the Apple receipt")
    item = max(candidates, key=lambda x: int(x.get("expires_date_ms", 0)))
    return {
        "transaction_id": item.get("original_transaction_id") or item["transaction_id"],
        "purchased_at": _parse_ms(item["purchase_date_ms"]),
        "expires_at": _parse_ms(item["expires_date_ms"]),
        "raw": {"environment": data.get("environment"), "item": item},
    }


def verify_google(product_id: str, purchase_token: Optional[str]) -> dict:
    if not purchase_token:
        raise HTTPException(400, "purchase_token is required for Google purchases")
    package_name = os.getenv("GOOGLE_PLAY_PACKAGE_NAME")
    credentials_json = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
    if not package_name or not credentials_json:
        raise HTTPException(503, "Google Play verification is not configured")
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import AuthorizedSession
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/androidpublisher"]
        )
        session = AuthorizedSession(credentials)
        url = (f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
               f"{package_name}/purchases/subscriptions/{product_id}/tokens/{purchase_token}")
        response = session.get(url, timeout=15)
        if response.status_code != 200:
            raise HTTPException(400, "Google Play purchase verification failed")
        data = response.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Could not verify Google Play purchase: {exc}")
    return {
        "transaction_id": data.get("orderId") or purchase_token,
        "purchased_at": _parse_ms(data["startTimeMillis"]),
        "expires_at": _parse_ms(data["expiryTimeMillis"]),
        "raw": data,
    }
