from fastapi import APIRouter, Depends, HTTPException, Query, Form, File, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from typing import List, Optional

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user
from ..worker import process_media, reverse_geocode
from ..core.rate_limit import memory_limit

router = APIRouter()

@router.post("", response_model=schemas.MemoryDetailResponse)
def create_memory(
    caption: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    mood_code: Optional[str] = Form(None),
    privacy_level: int = Form(3),
    place_id: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _rl: None = Depends(memory_limit)
):
    # Validate and parse place_id
    parsed_place_id = None
    if place_id and place_id.strip() != "":
        try:
            parsed_place_id = uuid.UUID(place_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Mã địa điểm (place_id) không hợp lệ. Vui lòng nhập đúng định dạng UUID (ví dụ: 3fa85f64-5717-4562-b3fc-2c963f66afa6) hoặc để trống."
            )

    # Convert lat/lng to PostGIS geography POINT
    wkt_point = f"SRID=4326;POINT({lng} {lat})"
    
    new_memory = models.Memory(
        id=uuid.uuid4(),
        user_id=current_user.id,
        caption=caption,
        mood_code=mood_code,
        privacy_level=privacy_level,
        place_id=parsed_place_id,
        location=wkt_point
    )
    
    db.add(new_memory)
    
    # Increment memories_count in UserProfile
    db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).update(
        {models.UserProfile.memories_count: models.UserProfile.memories_count + 1}
    )
    
    db.commit()
    db.refresh(new_memory)
    
    media_records = []
    if images:
        from .media import s3_client, R2_BUCKET_NAME, get_r2_url
        for image in images:
            # Check if there is an actual file
            if not image.filename:
                continue
            media_id = uuid.uuid4()
            content_type = image.content_type
            
            if content_type and content_type.startswith("image/"):
                try:
                    from ..core.image_optimizer import optimize_image
                    import io
                    image_bytes = image.file.read()
                    optimized_bytes, content_type = optimize_image(image_bytes, max_width=1600, max_height=1600, quality=80)
                    upload_file_obj = io.BytesIO(optimized_bytes)
                    ext = "webp"
                except Exception:
                    image.file.seek(0)
                    upload_file_obj = image.file
                    ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
            else:
                upload_file_obj = image.file
                ext = image.filename.split('.')[-1] if '.' in image.filename else 'bin'

            object_key = f"memories/{new_memory.id}/{media_id}.{ext}"
            public_url = f"https://pub-xxxxxx.r2.dev/{object_key}"
            
            # Upload to R2 if client exists
            if s3_client:
                try:
                    s3_client.upload_fileobj(
                        upload_file_obj,
                        R2_BUCKET_NAME,
                        object_key,
                        ExtraArgs={"ContentType": content_type}
                    )
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to upload image {image.filename}: {str(e)}")
            
            new_media = models.Media(
                id=media_id,
                memory_id=new_memory.id,
                user_id=current_user.id,
                media_type=1, # 1=image
                file_url=public_url,
                status=2 # 2=processed
            )
            db.add(new_media)
            media_records.append(new_media)
        db.commit()
    
    # Trigger async tasks
    process_media.delay(str(new_memory.id))
    reverse_geocode.delay(str(new_memory.id))
    
    # Format and return MemoryDetailResponse
    from .media import get_r2_url
    result = schemas.MemoryDetailResponse.model_validate(new_memory)
    result.location = {"lat": lat, "lng": lng}
    
    # Convert file_urls to presigned R2 URLs
    result.media = []
    for m in media_records:
        m_schema = schemas.MediaResponse.model_validate(m)
        m_schema.file_url = get_r2_url(m.file_url)
        result.media.append(m_schema)
    return result

def populate_author_info(m_res: schemas.MemoryResponse, db: Session):
    author = db.query(models.User).filter_by(id=m_res.user_id).first()
    if author:
        m_res.username = author.username
        author_profile = db.query(models.UserProfile).filter_by(user_id=m_res.user_id).first()
        if author_profile:
            m_res.display_name = author_profile.display_name or author.username
            if author_profile.avatar_media_id:
                avatar_media = db.query(models.Media).filter_by(id=author_profile.avatar_media_id).first()
                if avatar_media:
                    from .media import get_r2_url
                    m_res.avatar_url = get_r2_url(avatar_media.file_url)
        else:
            m_res.display_name = author.username
    return m_res

@router.get("/on-this-day", response_model=List[schemas.MemoryDetailResponse])
def get_on_this_day_memories(
    years_ago: Optional[int] = Query(None, ge=1, description="Số năm về trước (ví dụ: 1, 2 để tìm đúng năm cụ thể)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Lấy kỷ niệm vào ngày này của các năm về trước.
    - Nếu truyền years_ago (ví dụ = 1): Tìm đúng kỷ niệm ngày này, đúng 1 năm trước.
    - Nếu KHÔNG truyền years_ago: Tìm tất cả kỷ niệm ngày này trong các năm quá khứ (ví dụ 1 năm trước, 2 năm trước...).
    """
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import extract
    
    # Múi giờ Việt Nam UTC+7
    ICT = timezone(timedelta(hours=7))
    now_local = datetime.now(ICT)
    month = now_local.month
    day = now_local.day
    year = now_local.year
    
    # Query cơ bản: Chỉ lấy kỷ niệm của user hiện tại và chưa bị xóa mềm
    query = db.query(models.Memory).filter(
        models.Memory.user_id == current_user.id,
        models.Memory.deleted_at.is_(None)
    )
    
    if years_ago is not None:
        target_year = year - years_ago
        query = query.filter(
            extract('year', models.Memory.taken_at) == target_year,
            extract('month', models.Memory.taken_at) == month,
            extract('day', models.Memory.taken_at) == day
        )
    else:
        # Nếu không truyền, lấy tất cả các năm trước đó
        query = query.filter(
            extract('year', models.Memory.taken_at) < year,
            extract('month', models.Memory.taken_at) == month,
            extract('day', models.Memory.taken_at) == day
        )
        
    memories = query.order_by(models.Memory.taken_at.desc()).all()
    
    results = []
    from .media import get_r2_url
    
    for memory in memories:
        # Lấy tọa độ (lat/lng) bằng PostGIS ST_Y và ST_X
        coords = db.query(
            func.ST_Y(models.Memory.location).label('lat'),
            func.ST_X(models.Memory.location).label('lng')
        ).filter(models.Memory.id == memory.id).first()
        
        # Đếm lượt like, bình luận và trạng thái like của user hiện tại
        likes_count = db.query(func.count(models.Like.user_id)).filter(models.Like.memory_id == memory.id).scalar() or 0
        comments_count = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == memory.id).scalar() or 0
        is_liked = db.query(models.Like).filter(
            models.Like.memory_id == memory.id,
            models.Like.user_id == current_user.id
        ).first() is not None
        
        # Parse về Schema Response
        res = schemas.MemoryDetailResponse.model_validate(memory)
        res.likes_count = likes_count
        res.comments_count = comments_count
        res.is_liked = is_liked
        
        # Map thông tin chi tiết địa lý
        res.country = memory.country
        res.admin1 = memory.admin1
        res.admin2 = memory.admin2
        res.admin3 = memory.admin3
        res.village = memory.village
        res.address_text = memory.address_text
        res.place_name = memory.place_name
        
        if coords:
            res.location = {"lat": coords.lat, "lng": coords.lng}
            
        # Lấy các hình ảnh/video đi kèm
        media_records = db.query(models.Media).filter(models.Media.memory_id == memory.id).all()
        res.media = []
        for m in media_records:
            m_schema = schemas.MediaResponse.model_validate(m)
            m_schema.file_url = get_r2_url(m.file_url)
            res.media.append(m_schema)
            
        # Gán thông tin tác giả
        populate_author_info(res, db)
        results.append(res)
        
    return results

@router.get("/{memory_id}", response_model=schemas.MemoryDetailResponse)
def get_memory(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memory = db.query(models.Memory).filter(models.Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # Check if memory has been soft-deleted
    if memory.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    # Check blocking relationship
    block_exists = db.query(models.UserRelationship).filter(
        models.UserRelationship.relation_type == 4,
        (
            ((models.UserRelationship.source_user_id == current_user.id) & (models.UserRelationship.target_user_id == memory.user_id)) |
            ((models.UserRelationship.source_user_id == memory.user_id) & (models.UserRelationship.target_user_id == current_user.id))
        )
    ).first() is not None
    if block_exists:
        raise HTTPException(status_code=403, detail="Not authorized to view this memory (User block is active)")

    # Check privacy level (1=private, 2=friends, 3=public)
    from datetime import datetime, timezone
    if memory.privacy_level == 1 and memory.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this memory")
    
    # Check friends privacy constraint (level 2)
    if memory.privacy_level == 2 and memory.user_id != current_user.id:
        is_friend = db.query(models.UserRelationship).filter(
            models.UserRelationship.source_user_id == current_user.id,
            models.UserRelationship.target_user_id == memory.user_id,
            models.UserRelationship.relation_type == 1
        ).first() is not None and db.query(models.UserRelationship).filter(
            models.UserRelationship.source_user_id == memory.user_id,
            models.UserRelationship.target_user_id == current_user.id,
            models.UserRelationship.relation_type == 1
        ).first() is not None
        
        if not is_friend:
            raise HTTPException(status_code=403, detail="This memory is restricted to friends only")

    # Check public visibility expiration (level 3)
    if memory.privacy_level == 3 and memory.user_id != current_user.id:
        if memory.visibility_expires_at and memory.visibility_expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="This public memory has expired and is no longer visible to other users")
    
    # We return the memory. GeoAlchemy2 Geography fields aren't JSON serializable by default.
    # We will need to query ST_AsText or similar if we want actual coords in response.
    # For MVP, let's extract coords from the DB query.
    
    # query lat/lng using ST_Y and ST_X
    coords = db.query(
        func.ST_Y(models.Memory.location).label('lat'),
        func.ST_X(models.Memory.location).label('lng')
    ).filter(models.Memory.id == memory_id).first()
    
    # Count likes, comments, and check if liked by current user
    likes_count = db.query(func.count(models.Like.memory_id)).filter(models.Like.memory_id == memory_id).scalar() or 0
    comments_count = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == memory_id).scalar() or 0
    is_liked = db.query(models.Like).filter(
        models.Like.memory_id == memory_id,
        models.Like.user_id == current_user.id
    ).first() is not None

    result = schemas.MemoryDetailResponse.model_validate(memory)
    result.likes_count = likes_count
    result.comments_count = comments_count
    result.is_liked = is_liked
    
    # Map structured location components
    result.country = memory.country
    result.admin1 = memory.admin1
    result.admin2 = memory.admin2
    result.admin3 = memory.admin3
    result.village = memory.village
    result.address_text = memory.address_text
    result.place_name = memory.place_name
    
    if coords:
        result.location = {"lat": coords.lat, "lng": coords.lng}
    
    # Fetch associated media
    from .media import get_r2_url
    media_records = db.query(models.Media).filter(models.Media.memory_id == memory_id).all()
    result.media = []
    for m in media_records:
        m_schema = schemas.MediaResponse.model_validate(m)
        m_schema.file_url = get_r2_url(m.file_url)
        result.media.append(m_schema)
    populate_author_info(result, db)
    return result

@router.patch("/{memory_id}", response_model=schemas.MemoryDetailResponse)
def update_memory(
    memory_id: uuid.UUID,
    memory_in: schemas.MemoryUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memory = db.query(models.Memory).filter(models.Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    is_owner = (memory.user_id == current_user.id)
    is_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_edit_perm = perms.get("can_edit_others_memories", False)
    
    if not is_owner and not is_admin and not has_edit_perm:
        raise HTTPException(status_code=403, detail="Not authorized to edit this memory")
        
    update_data = memory_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(memory, field, value)
        
    db.commit()
    db.refresh(memory)
    
    return get_memory(memory_id=memory_id, db=db, current_user=current_user)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memory = db.query(models.Memory).filter(models.Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    is_owner = (memory.user_id == current_user.id)
    is_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_delete_perm = perms.get("can_delete_others_memories", False)
    
    if not is_owner and not is_admin and not has_delete_perm:
        raise HTTPException(status_code=403, detail="Not authorized to delete this memory")
        
    # Delete associated media and likes/comments (if cascade delete isn't set)
    db.query(models.Like).filter(models.Like.memory_id == memory_id).delete()
    db.query(models.Comment).filter(models.Comment.memory_id == memory_id).delete()
    db.query(models.Media).filter(models.Media.memory_id == memory_id).delete()
    
    db.delete(memory)
    
    # Decrement memories_count in UserProfile for the actual owner of the memory
    db.query(models.UserProfile).filter(models.UserProfile.user_id == memory.user_id).update(
        {models.UserProfile.memories_count: func.greatest(0, models.UserProfile.memories_count - 1)}
    )
    
    db.commit()
    return

@router.post("/{memory_id}/extend", response_model=schemas.MemoryDetailResponse)
def extend_memory_visibility(
    memory_id: uuid.UUID,
    days: int = Query(30, ge=1, description="Number of days to extend visibility"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memory = db.query(models.Memory).filter(models.Memory.id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    if memory.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to extend visibility for this memory")
    
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    current_expires = memory.visibility_expires_at or now
    if current_expires < now:
        current_expires = now
        
    memory.visibility_expires_at = current_expires + timedelta(days=days)
    db.commit()
    db.refresh(memory)
    
    return get_memory(memory_id=memory_id, db=db, current_user=current_user)
