from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_optional_user

from geoalchemy2 import Geography

router = APIRouter()

@router.get("/pins", response_model=List[schemas.MemoryResponse])
def get_map_pins(
    lat: float = Query(..., description="Center latitude"),
    lng: float = Query(..., description="Center longitude"),
    radius: float = Query(1000.0, description="Radius in meters"),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user)
):
    center_point = f"SRID=4326;POINT({lng} {lat})"

    if current_user is None:
        # Khách (chưa đăng nhập): chỉ trả về pin public còn hiệu lực
        query = db.query(
            models.Memory,
            func.ST_Y(models.Memory.location.cast(models.Geometry)).label('lat'),
            func.ST_X(models.Memory.location.cast(models.Geometry)).label('lng')
        ).filter(
            func.ST_DWithin(models.Memory.location.cast(Geography), center_point, radius),
            models.Memory.deleted_at.is_(None),
            models.Memory.privacy_level == 3,
            models.Memory.visibility_expires_at >= datetime.utcnow()
        ).limit(100)

        memories_data = query.all()

        results = []
        from .media import get_r2_url
        for m, m_lat, m_lng in memories_data:
            likes_c = db.query(func.count(models.Like.memory_id)).filter(models.Like.memory_id == m.id).scalar() or 0
            comments_c = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == m.id).scalar() or 0

            m_res = schemas.MemoryResponse.model_validate(m)
            m_res.likes_count = likes_c
            m_res.comments_count = comments_c
            m_res.is_liked = False
            m_res.location = {"lat": m_lat, "lng": m_lng}

            media_records = db.query(models.Media).filter(models.Media.memory_id == m.id).all()
            m_res.media = []
            for media in media_records:
                m_schema = schemas.MediaResponse.model_validate(media)
                m_schema.file_url = get_r2_url(media.file_url)
                m_res.media.append(m_schema)

            from .memories import populate_author_info
            populate_author_info(m_res, db)
            results.append(m_res)
        return results

    # Đã đăng nhập: áp dụng filter đầy đủ (public + bạn bè, loại trừ blocked)
    blocked_relations = db.query(models.UserRelationship).filter(
        models.UserRelationship.relation_type == 4,
        (models.UserRelationship.source_user_id == current_user.id) | (models.UserRelationship.target_user_id == current_user.id)
    ).all()

    blocked_ids = set()
    for rel in blocked_relations:
        blocked_ids.add(rel.source_user_id)
        blocked_ids.add(rel.target_user_id)

    following_subquery = db.query(models.UserRelationship.target_user_id).filter(
        models.UserRelationship.source_user_id == current_user.id,
        models.UserRelationship.relation_type == 1
    ).subquery()

    friends_subquery = db.query(models.UserRelationship.source_user_id).filter(
        models.UserRelationship.target_user_id == current_user.id,
        models.UserRelationship.relation_type == 1,
        models.UserRelationship.source_user_id.in_(following_subquery)
    ).all()

    friend_ids = [f[0] for f in friends_subquery]

    query = db.query(
        models.Memory,
        func.ST_Y(models.Memory.location.cast(models.Geometry)).label('lat'),
        func.ST_X(models.Memory.location.cast(models.Geometry)).label('lng')
    ).filter(
        func.ST_DWithin(models.Memory.location.cast(Geography), center_point, radius),
        models.Memory.deleted_at.is_(None),
        models.Memory.user_id != current_user.id
    ).filter(
        ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.utcnow())) |
        ((models.Memory.privacy_level == 2) & models.Memory.user_id.in_(friend_ids))
    )

    if blocked_ids:
        query = query.filter(~models.Memory.user_id.in_(list(blocked_ids)))

    query = query.limit(100)
    memories_data = query.all()

    results = []
    from .media import get_r2_url
    for m, m_lat, m_lng in memories_data:
        likes_c = db.query(func.count(models.Like.memory_id)).filter(models.Like.memory_id == m.id).scalar() or 0
        comments_c = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == m.id).scalar() or 0
        liked_by_me = db.query(models.Like).filter(
            models.Like.memory_id == m.id,
            models.Like.user_id == current_user.id
        ).first() is not None

        m_res = schemas.MemoryResponse.model_validate(m)
        m_res.likes_count = likes_c
        m_res.comments_count = comments_c
        m_res.is_liked = liked_by_me
        m_res.location = {"lat": m_lat, "lng": m_lng}

        media_records = db.query(models.Media).filter(models.Media.memory_id == m.id).all()
        m_res.media = []
        for media in media_records:
            m_schema = schemas.MediaResponse.model_validate(media)
            m_schema.file_url = get_r2_url(media.file_url)
            m_res.media.append(m_schema)

        from .memories import populate_author_info
        populate_author_info(m_res, db)
        results.append(m_res)
    return results
