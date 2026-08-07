from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import os
from pydantic import BaseModel
from pydantic import Field

from .. import models, schemas
from ..database import get_db
from ..core.dependencies import get_current_user

router = APIRouter()

R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

# Initialize boto3 client for Cloudflare R2
# Only init if env vars are present (to avoid crashing if not configured)
s3_client = None
if R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        's3',
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4')
    )

def get_r2_url(file_url: str) -> str:
    # If it's already a presigned URL, return it
    if "Signature=" in file_url or "X-Amz-Signature=" in file_url:
        return file_url
        
    # If it is an external non-R2 URL (like Google user profile avatar), return it as is
    if file_url.startswith(("http://", "https://")) and not (".r2.dev" in file_url or "cloudflarestorage.com" in file_url):
        return file_url
        
    # Extract object key
    object_key = None
    if ".r2.dev/" in file_url:
        object_key = file_url.split(".r2.dev/")[-1]
    elif ".cloudflarestorage.com/" in file_url:
        object_key = file_url.split(".cloudflarestorage.com/")[-1]
        # split again if bucket is in the path
        if "/" in object_key and R2_BUCKET_NAME in object_key:
            object_key = object_key.split(f"{R2_BUCKET_NAME}/")[-1]
    else:
        # fallback if it's already just the key
        object_key = file_url
        
    if object_key and s3_client:
        try:
            return s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': R2_BUCKET_NAME,
                    'Key': object_key
                },
                ExpiresIn=86400 # 24 hours
            )
        except Exception:
            pass
            
    return file_url

class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    media_type: int = 1 # 1=image, 2=video
    duration_seconds: Optional[float] = Field(None, ge=0)

class PresignedUrlResponse(BaseModel):
    upload_url: str
    public_url: str
    media_id: uuid.UUID

@router.post("/memories/{memory_id}/media/upload-url", response_model=PresignedUrlResponse)
def get_presigned_url(
    memory_id: uuid.UUID,
    req: PresignedUrlRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not s3_client:
        raise HTTPException(status_code=500, detail="R2 is not configured")

    if req.media_type not in (1, 2):
        raise HTTPException(status_code=400, detail="media_type must be 1 (image) or 2 (video)")
    content_type = req.content_type.lower()
    if req.media_type == 1 and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image content_type")
    if req.media_type == 2:
        if not content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="Invalid video content_type")
        
    memory = db.query(models.Memory).filter(models.Memory.id == memory_id).first()
    if not memory or memory.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Memory not found or unauthorized")

    media_id = uuid.uuid4()
    # Generate a unique object key
    ext = req.filename.split('.')[-1] if '.' in req.filename else 'bin'
    object_key = f"memories/{memory_id}/{media_id}.{ext}"
    
    # Generate presigned URL
    try:
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': R2_BUCKET_NAME,
                'Key': object_key,
                'ContentType': req.content_type
            },
            ExpiresIn=3600
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    public_url = f"https://pub-xxxxxx.r2.dev/{object_key}" # Replace with actual public URL domain
    
    # Save media record
    new_media = models.Media(
        id=media_id,
        memory_id=memory_id,
        user_id=current_user.id,
        media_type=req.media_type,
        file_url=public_url,
        status=1 # pending
    )
    db.add(new_media)
    db.commit()
    
    return PresignedUrlResponse(
        upload_url=presigned_url,
        public_url=public_url,
        media_id=media_id
    )

@router.put("/memories/media/{media_id}/confirm")
def confirm_upload(
    media_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    media = db.query(models.Media).filter(models.Media.id == media_id).first()
    if not media or media.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Media not found")
        
    media.status = 2 # Processed / Confirmed
    db.commit()
    
    return {"message": "Upload confirmed"}

from fastapi import UploadFile, File
@router.post("/media/upload", response_model=schemas.MediaResponse)
def upload_general_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not s3_client:
        raise HTTPException(status_code=500, detail="R2 is not configured")
        
    media_id = uuid.uuid4()
    content_type = file.content_type
    
    if content_type and content_type.startswith("image/"):
        try:
            from ..core.image_optimizer import optimize_image
            import io
            file_bytes = file.file.read()
            optimized_bytes, content_type = optimize_image(file_bytes)
            upload_file_obj = io.BytesIO(optimized_bytes)
            ext = "webp"
        except Exception:
            file.file.seek(0)
            upload_file_obj = file.file
            ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    else:
        upload_file_obj = file.file
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'

    object_key = f"general/{current_user.id}/{media_id}.{ext}"
    public_url = f"https://pub-xxxxxx.r2.dev/{object_key}"
    
    try:
        s3_client.upload_fileobj(
            upload_file_obj,
            R2_BUCKET_NAME,
            object_key,
            ExtraArgs={"ContentType": content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to R2: {str(e)}")
        
    new_media = models.Media(
        id=media_id,
        user_id=current_user.id,
        media_type=1, # 1=image
        file_url=public_url,
        status=2 # processed
    )
    db.add(new_media)
    db.commit()
    db.refresh(new_media)
    
    return new_media
