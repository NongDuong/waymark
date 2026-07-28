import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.dependencies import get_current_user
from ..core.subscriptions import PRODUCTS, effective_tier, entitlement, utcnow, verify_apple, verify_google
from ..database import get_db

router = APIRouter()


def _response(user, purchase=None):
    tier = effective_tier(user)
    values = entitlement(tier)
    return schemas.SubscriptionResponse(
        tier=tier,
        product_id=purchase.product_id if purchase else None,
        platform=purchase.platform if purchase else None,
        status="active" if tier != "normal" else "inactive",
        expires_at=user.subscription_expires_at if tier != "normal" else None,
        **values,
    )


@router.get("/plans", response_model=list[schemas.SubscriptionPlanResponse])
def list_plans():
    ios_standard = os.getenv("IAP_STANDARD_IOS_PRODUCT_ID", "waymark.standard.yearly")
    ios_premium = os.getenv("IAP_PREMIUM_IOS_PRODUCT_ID", "waymark.premium.yearly")
    android_standard = os.getenv("IAP_STANDARD_ANDROID_PRODUCT_ID", "waymark.standard.yearly")
    android_premium = os.getenv("IAP_PREMIUM_ANDROID_PRODUCT_ID", "waymark.premium.yearly")
    return [
        {"tier": "normal", "product_ids": {}, **entitlement("normal")},
        {"tier": "standard", "product_ids": {"apple": ios_standard, "google": android_standard}, **entitlement("standard")},
        {"tier": "premium", "product_ids": {"apple": ios_premium, "google": android_premium}, **entitlement("premium")},
    ]


@router.get("/me", response_model=schemas.SubscriptionResponse)
def my_subscription(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    purchase = db.query(models.InAppPurchase).filter(
        models.InAppPurchase.user_id == current_user.id,
        models.InAppPurchase.status == "active",
    ).order_by(models.InAppPurchase.expires_at.desc()).first()
    return _response(current_user, purchase)


@router.post("/verify", response_model=schemas.SubscriptionResponse)
def verify_purchase(body: schemas.PurchaseVerifyRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    tier = PRODUCTS.get(body.product_id)
    if not tier:
        raise HTTPException(400, "Unknown in-app purchase product_id")
    verified = verify_apple(body.product_id, body.receipt_data) if body.platform == "apple" else verify_google(body.product_id, body.purchase_token)
    if verified["expires_at"] <= utcnow():
        raise HTTPException(400, "The subscription has expired")
    purchase = db.query(models.InAppPurchase).filter_by(transaction_id=verified["transaction_id"]).first()
    if purchase and purchase.user_id != current_user.id:
        raise HTTPException(409, "This purchase belongs to another account")
    if not purchase:
        purchase = models.InAppPurchase(user_id=current_user.id, platform=body.platform, product_id=body.product_id, transaction_id=verified["transaction_id"], expires_at=verified["expires_at"])
        db.add(purchase)
    purchase.status = "active"
    purchase.purchased_at = verified["purchased_at"]
    purchase.expires_at = verified["expires_at"]
    purchase.raw_verification = verified["raw"]
    current_tier = effective_tier(current_user)
    # Verifying a Standard receipt must not accidentally remove a still-active Premium entitlement.
    if not (current_tier == "premium" and tier == "standard"):
        current_user.subscription_tier = tier
        current_user.subscription_expires_at = verified["expires_at"]
    current_user.is_vip = True
    db.commit()
    db.refresh(current_user)
    return _response(current_user, purchase)
