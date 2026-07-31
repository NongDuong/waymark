from datetime import datetime, timezone


PACKAGES = {
    "standard_package": {
        "duration_days": 30,
        "benefits": [
            "Lưu giữ kỷ niệm 1 tháng trên bản đồ",
            "Không có quảng cáo",
        ],
    },
    "premium_package": {
        "duration_days": 365,
        "benefits": [
            "Lưu kỷ niệm 1 năm trên bản đồ",
            "Tải lên hình ảnh và video từ thư viện",
            "Không có quảng cáo",
        ],
    },
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def effective_package(user) -> str | None:
    package_id = getattr(user, "package_id", None)
    expires_at = getattr(user, "package_expires_at", None)
    if package_id not in PACKAGES or not expires_at:
        return None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return package_id if expires_at > utcnow() else None


def entitlement(package_id: str | None) -> dict:
    premium = package_id == "premium_package"
    paid = package_id in PACKAGES
    return {
        "pin_visibility_days": PACKAGES[package_id]["duration_days"] if paid else 30,
        "can_upload_library_photos": premium,
        "can_upload_library_videos": premium,
        "ads_enabled": not paid,
    }
