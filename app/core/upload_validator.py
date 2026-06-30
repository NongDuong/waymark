from fastapi import HTTPException, UploadFile

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/jpg", "image/png",
    "image/webp", "image/gif", "image/heic", "image/heif"
}


def validate_image_upload(image: UploadFile) -> bytes:
    """Validate image file type and size. Returns file bytes (resets seek to 0)."""
    if not image or not image.filename:
        raise HTTPException(status_code=400, detail="Không có file được chọn.")

    content_type = (image.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Loại file không hỗ trợ: {content_type}. Chỉ chấp nhận: JPEG, PNG, WebP, GIF, HEIC."
        )

    contents = image.file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File quá lớn ({len(contents) // 1024 // 1024}MB). Tối đa 50MB."
        )

    image.file.seek(0)
    return contents
