from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from typing import List
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user

router = APIRouter()

def populate_dynamic_profile_stats(profile_response: schemas.UserProfileResponse, user_id: uuid.UUID, db: Session):
    # Total memories
    mem_count = db.query(func.count(models.Memory.id)).filter(
        models.Memory.user_id == user_id,
        models.Memory.deleted_at.is_(None)
    ).scalar() or 0
    profile_response.memories_count = mem_count
    
    # Total likes received across all memories
    likes_count = db.query(func.count(models.Like.user_id)).join(
        models.Memory, models.Memory.id == models.Like.memory_id
    ).filter(
        models.Memory.user_id == user_id,
        models.Memory.deleted_at.is_(None)
    ).scalar() or 0
    profile_response.total_likes_received = likes_count
    
    # Followers count
    followers = db.query(func.count(models.UserRelationship.id)).filter_by(
        target_user_id=user_id,
        relation_type=1 # follow
    ).scalar() or 0
    profile_response.followers_count = followers
    
    # Following count
    following = db.query(func.count(models.UserRelationship.id)).filter_by(
        source_user_id=user_id,
        relation_type=1 # follow
    ).scalar() or 0
    profile_response.following_count = following

@router.get("/me", response_model=schemas.UserProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    
    # If profile doesn't exist, create it (lazy initialization)
    if not profile:
        profile = models.UserProfile(
            user_id=current_user.id,
            display_name=current_user.username
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    avatar_url = None
    if profile.avatar_media_id:
        avatar_media = db.query(models.Media).filter(models.Media.id == profile.avatar_media_id).first()
        if avatar_media:
            from .media import get_r2_url
            avatar_url = get_r2_url(avatar_media.file_url)

    result = schemas.UserProfileResponse.model_validate(profile)
    result.username = current_user.username
    result.avatar_url = avatar_url
    
    is_super_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_any_permission = any(perms.values()) if isinstance(perms, dict) else False
    
    result.is_admin = is_super_admin or has_any_permission
    result.is_super_admin = is_super_admin
    result.is_vip = getattr(current_user, "is_vip", False)
    
    populate_dynamic_profile_stats(result, current_user.id, db)
    return result

@router.put("/me", response_model=schemas.UserProfileResponse)
def update_my_profile(
    profile_in: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = models.UserProfile(
            user_id=current_user.id,
            display_name=current_user.username
        )
        db.add(profile)
        db.commit()

    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
        
    db.commit()
    db.refresh(profile)

    avatar_url = None
    if profile.avatar_media_id:
        avatar_media = db.query(models.Media).filter(models.Media.id == profile.avatar_media_id).first()
        if avatar_media:
            from .media import get_r2_url
            avatar_url = get_r2_url(avatar_media.file_url)

    result = schemas.UserProfileResponse.model_validate(profile)
    result.username = current_user.username
    result.avatar_url = avatar_url
    
    is_super_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_any_permission = any(perms.values()) if isinstance(perms, dict) else False
    
    result.is_admin = is_super_admin or has_any_permission
    result.is_super_admin = is_super_admin
    result.is_vip = getattr(current_user, "is_vip", False)
    
    populate_dynamic_profile_stats(result, current_user.id, db)
    return result

@router.post("/me/avatar", response_model=schemas.UserProfileResponse)
def upload_avatar(
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = models.UserProfile(
            user_id=current_user.id,
            display_name=current_user.username
        )
        db.add(profile)
        db.commit()

    if not avatar.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    media_id = uuid.uuid4()
    content_type = avatar.content_type
    
    if content_type and content_type.startswith("image/"):
        try:
            from ..core.image_optimizer import optimize_image
            import io
            avatar_bytes = avatar.file.read()
            # Avatars are small, downscale aggressively to max 400x400 for speed and space saving
            optimized_bytes, content_type = optimize_image(avatar_bytes, max_width=400, max_height=400, quality=80)
            upload_file_obj = io.BytesIO(optimized_bytes)
            ext = "webp"
        except Exception:
            avatar.file.seek(0)
            upload_file_obj = avatar.file
            ext = avatar.filename.split('.')[-1] if '.' in avatar.filename else 'jpg'
    else:
        upload_file_obj = avatar.file
        ext = avatar.filename.split('.')[-1] if '.' in avatar.filename else 'jpg'

    object_key = f"avatars/{current_user.id}/{media_id}.{ext}"
    public_url = f"https://pub-xxxxxx.r2.dev/{object_key}"

    from .media import s3_client, R2_BUCKET_NAME, get_r2_url
    if s3_client:
        try:
            s3_client.upload_fileobj(
                upload_file_obj,
                R2_BUCKET_NAME,
                object_key,
                ExtraArgs={"ContentType": content_type}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")

    new_media = models.Media(
        id=media_id,
        user_id=current_user.id,
        media_type=1,
        file_url=public_url,
        status=2
    )
    db.add(new_media)
    
    profile.avatar_media_id = media_id
    db.commit()
    db.refresh(profile)

    avatar_url = get_r2_url(new_media.file_url)
    
    result = schemas.UserProfileResponse.model_validate(profile)
    result.username = current_user.username
    result.avatar_url = avatar_url
    
    is_super_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_any_permission = any(perms.values()) if isinstance(perms, dict) else False
    
    result.is_admin = is_super_admin or has_any_permission
    result.is_super_admin = is_super_admin
    result.is_vip = getattr(current_user, "is_vip", False)
    
    populate_dynamic_profile_stats(result, current_user.id, db)
    return result

@router.get("/{user_id}", response_model=schemas.UserProfileResponse)
def get_user_profile(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()
    if not profile:
        profile = models.UserProfile(
            user_id=user.id,
            display_name=user.username
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    avatar_url = None
    if profile.avatar_media_id:
        avatar_media = db.query(models.Media).filter(models.Media.id == profile.avatar_media_id).first()
        if avatar_media:
            from .media import get_r2_url
            avatar_url = get_r2_url(avatar_media.file_url)

    is_following = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id,
        target_user_id=user_id,
        relation_type=1 # follow
    ).first() is not None

    is_blocked = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id,
        target_user_id=user_id,
        relation_type=4 # block
    ).first() is not None

    result = schemas.UserProfileResponse.model_validate(profile)
    result.username = user.username
    result.avatar_url = avatar_url
    result.is_following = is_following
    result.is_blocked = is_blocked
    
    is_super_admin = getattr(user, "is_admin", False)
    perms = getattr(user, "permissions", None) or {}
    has_any_permission = any(perms.values()) if isinstance(perms, dict) else False
    
    result.is_admin = is_super_admin or has_any_permission
    result.is_super_admin = is_super_admin
    result.is_vip = getattr(user, "is_vip", False)
    
    populate_dynamic_profile_stats(result, user_id, db)
    return result

@router.get("/{user_id}/memories", response_model=List[schemas.MemoryResponse])
def get_user_memories(
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Retrieve user's memories based on privacy settings
    # We query memory and its coordinates separately to avoid WKBElement serialization issues
    query = db.query(
        models.Memory,
        func.ST_Y(models.Memory.location).label('lat'),
        func.ST_X(models.Memory.location).label('lng')
    ).filter(models.Memory.user_id == user_id)
    
    # If not the owner, filter out private memories
    if user_id != current_user.id:
        i_follow = db.query(models.UserRelationship).filter_by(
            source_user_id=current_user.id,
            target_user_id=user_id,
            relation_type=1 # follow
        ).first() is not None
        
        they_follow = db.query(models.UserRelationship).filter_by(
            source_user_id=user_id,
            target_user_id=current_user.id,
            relation_type=1 # follow
        ).first() is not None
        
        is_friend = i_follow and they_follow
        if is_friend:
            query = query.filter(
                (models.Memory.privacy_level == 2) |
                ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.utcnow()))
            )
        else:
            query = query.filter(
                (models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.utcnow())
            )
        
    memories_data = query.order_by(models.Memory.taken_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for memory, lat, lng in memories_data:
        likes_count = db.query(func.count(models.Like.memory_id)).filter(models.Like.memory_id == memory.id).scalar() or 0
        comments_count = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == memory.id).scalar() or 0
        is_liked = db.query(models.Like).filter(
            models.Like.memory_id == memory.id,
            models.Like.user_id == current_user.id
        ).first() is not None

        res = schemas.MemoryResponse.model_validate(memory)
        res.location = {"lat": lat, "lng": lng}
        res.likes_count = likes_count
        res.comments_count = comments_count
        res.is_liked = is_liked
        results.append(res)
        
    return results

@router.get("/me/location-stats", response_model=schemas.UserLocationStats)
def get_my_location_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Total Memories
    total_memories = db.query(func.count(models.Memory.id)).filter(models.Memory.user_id == current_user.id).scalar() or 0
    
    # Distinct Countries
    countries = db.query(models.Memory.country).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.country.isnot(None)
    ).distinct().all()
    country_list = [c[0] for c in countries]
    
    # Distinct Provinces (Admin1)
    provinces = db.query(models.Memory.admin1).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.admin1.isnot(None)
    ).distinct().all()
    province_list = [p[0] for p in provinces]
    
    # Distinct Districts (Admin2)
    districts_count = db.query(func.count(func.distinct(models.Memory.admin2))).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.admin2.isnot(None)
    ).scalar() or 0
    
    # Distinct Communes (Admin3)
    communes_count = db.query(func.count(func.distinct(models.Memory.admin3))).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.admin3.isnot(None)
    ).scalar() or 0

    # Distinct Specific Places (place_name)
    places_count = db.query(func.count(func.distinct(models.Memory.place_name))).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.place_name.isnot(None)
    ).scalar() or 0
    
    return schemas.UserLocationStats(
        total_memories=total_memories,
        total_countries=len(country_list),
        total_provinces=len(province_list),
        total_districts=districts_count,
        total_communes=communes_count,
        total_places=places_count,
        countries=country_list,
        provinces=province_list
    )
