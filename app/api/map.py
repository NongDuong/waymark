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


def _batch_enrich_memories(memories_data, db, current_user_id=None):
    """Batch-load likes, comments, media, author info to avoid N+1 queries."""
    from .media import get_r2_url
    from .memories import populate_author_info

    if not memories_data:
        return []

    memory_ids = [m.id for m, _, _ in memories_data]

    # Batch: likes count
    likes_map = dict(
        db.query(models.Like.memory_id, func.count())
        .filter(models.Like.memory_id.in_(memory_ids))
        .group_by(models.Like.memory_id).all()
    )
    # Batch: comments count
    comments_map = dict(
        db.query(models.Comment.memory_id, func.count())
        .filter(models.Comment.memory_id.in_(memory_ids), models.Comment.deleted_at.is_(None))
        .group_by(models.Comment.memory_id).all()
    )
    # Batch: is_liked
    liked_set = set()
    if current_user_id:
        liked_rows = db.query(models.Like.memory_id).filter(
            models.Like.memory_id.in_(memory_ids),
            models.Like.user_id == current_user_id
        ).all()
        liked_set = {row[0] for row in liked_rows}

    # Batch: media
    media_rows = db.query(models.Media).filter(models.Media.memory_id.in_(memory_ids)).all()
    media_map = {}
    for media in media_rows:
        media_map.setdefault(media.memory_id, []).append(media)

    # Batch: author info
    user_ids = list({m.user_id for m, _, _ in memories_data})
    users_map = {u.id: u for u in db.query(models.User).filter(models.User.id.in_(user_ids)).all()}
    profiles_map = {p.user_id: p for p in db.query(models.UserProfile).filter(models.UserProfile.user_id.in_(user_ids)).all()}
    avatar_media_ids = [p.avatar_media_id for p in profiles_map.values() if p and p.avatar_media_id]
    avatars_map = {}
    if avatar_media_ids:
        for av in db.query(models.Media).filter(models.Media.id.in_(avatar_media_ids)).all():
            avatars_map[av.id] = get_r2_url(av.file_url)

    results = []
    for m, m_lat, m_lng in memories_data:
        m_res = schemas.MemoryResponse.model_validate(m)
        m_res.likes_count = likes_map.get(m.id, 0)
        m_res.comments_count = comments_map.get(m.id, 0)
        m_res.is_liked = m.id in liked_set
        m_res.location = {"lat": m_lat, "lng": m_lng}

        m_res.media = []
        for media in media_map.get(m.id, []):
            m_schema = schemas.MediaResponse.model_validate(media)
            m_schema.file_url = get_r2_url(media.file_url)
            m_res.media.append(m_schema)

        author = users_map.get(m.user_id)
        if author:
            m_res.author_username = author.username
            profile = profiles_map.get(author.id)
            if profile:
                m_res.display_name = profile.display_name or author.username
                if profile.avatar_media_id:
                    m_res.avatar_url = avatars_map.get(profile.avatar_media_id)
            else:
                m_res.display_name = author.username

        results.append(m_res)
    return results


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
        memories_data = db.query(
            models.Memory,
            func.ST_Y(models.Memory.location.cast(models.Geometry)).label('lat'),
            func.ST_X(models.Memory.location.cast(models.Geometry)).label('lng')
        ).filter(
            func.ST_DWithin(models.Memory.location.cast(Geography), center_point, radius),
            models.Memory.deleted_at.is_(None),
            models.Memory.privacy_level == 3,
            models.Memory.visibility_expires_at >= datetime.utcnow()
        ).limit(100).all()

        return _batch_enrich_memories(memories_data, db)

    # Subquery: blocked user IDs (both directions)
    blocked_subq = db.query(models.UserRelationship.target_user_id).filter(
        models.UserRelationship.source_user_id == current_user.id,
        models.UserRelationship.relation_type == 4
    ).union(
        db.query(models.UserRelationship.source_user_id).filter(
            models.UserRelationship.target_user_id == current_user.id,
            models.UserRelationship.relation_type == 4
        )
    ).subquery()

    following_subquery = db.query(models.UserRelationship.target_user_id).filter(
        models.UserRelationship.source_user_id == current_user.id,
        models.UserRelationship.relation_type == 1
    ).subquery()

    friend_ids_rows = db.query(models.UserRelationship.source_user_id).filter(
        models.UserRelationship.target_user_id == current_user.id,
        models.UserRelationship.relation_type == 1,
        models.UserRelationship.source_user_id.in_(following_subquery)
    ).all()
    friend_ids = [f[0] for f in friend_ids_rows]

    query = db.query(
        models.Memory,
        func.ST_Y(models.Memory.location.cast(models.Geometry)).label('lat'),
        func.ST_X(models.Memory.location.cast(models.Geometry)).label('lng')
    ).filter(
        func.ST_DWithin(models.Memory.location.cast(Geography), center_point, radius),
        models.Memory.deleted_at.is_(None),
        models.Memory.user_id != current_user.id,
        ~models.Memory.user_id.in_(blocked_subq)
    ).filter(
        ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.utcnow())) |
        ((models.Memory.privacy_level == 2) & models.Memory.user_id.in_(friend_ids))
    ).limit(100)

    memories_data = query.all()
    return _batch_enrich_memories(memories_data, db, current_user_id=current_user.id)
