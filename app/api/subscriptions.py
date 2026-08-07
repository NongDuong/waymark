from datetime import timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.dependencies import get_current_user
from ..core.subscriptions import PACKAGES, effective_package, entitlement, utcnow
from ..database import get_db

router = APIRouter()


def _response(user):
    package_id = effective_package(user)
    values = entitlement(package_id)
    remaining_days = 0
    if package_id and user.package_expires_at:
        expires_at = user.package_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        remaining_days = max(0, ceil((expires_at - utcnow()).total_seconds() / 86400))
    return schemas.SubscriptionResponse(
        package_id=package_id,
        status="active" if package_id else "inactive",
        expires_at=user.package_expires_at if package_id else None,
        remaining_days=remaining_days,
        benefits=PACKAGES[package_id]["benefits"] if package_id else [],
        **values,
    )


@router.get("/packages", response_model=list[schemas.PackageResponse])
def list_packages():
    return [
        {"package_id": package_id, "benefits": package["benefits"], **entitlement(package_id)}
        for package_id, package in PACKAGES.items()
    ]


@router.get("/me", response_model=schemas.SubscriptionResponse)
def my_subscription(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return _response(current_user)


@router.post("/activate", response_model=schemas.SubscriptionResponse)
def activate_package(body: schemas.PackageActivateRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Restoring the same active package must not renew it on every app launch.
    active_package = effective_package(current_user)
    if active_package == body.package_id:
        expires_at = current_user.package_expires_at
    else:
        expires_at = utcnow() + timedelta(days=PACKAGES[body.package_id]["duration_days"])
    current_user.package_id = body.package_id
    current_user.package_expires_at = expires_at
    current_user.is_vip = True
    db.query(models.Memory).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.deleted_at.is_(None),
    ).update(
        {models.Memory.visibility_expires_at: expires_at},
        synchronize_session=False,
    )
    db.commit()
    db.refresh(current_user)
    return _response(current_user)
