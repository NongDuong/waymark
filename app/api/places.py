from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from typing import List
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user

router = APIRouter()

@router.post("", response_model=schemas.PlaceResponse)
def create_place(
    place_in: schemas.PlaceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if place already exists based on provider_place_id
    existing_place = db.query(models.Place).filter_by(
        provider=place_in.provider, 
        provider_place_id=place_in.provider_place_id
    ).first()
    
    if existing_place:
        return existing_place

    wkt_point = f"SRID=4326;POINT({place_in.location.lng} {place_in.location.lat})"
    
    new_place = models.Place(
        id=uuid.uuid4(),
        provider=place_in.provider,
        provider_place_id=place_in.provider_place_id,
        name=place_in.name,
        address_text=place_in.address_text,
        country_code=place_in.country_code,
        admin1=place_in.admin1,
        admin2=place_in.admin2,
        location=wkt_point
    )
    db.add(new_place)
    db.commit()
    db.refresh(new_place)
    return new_place

@router.get("/{place_id}/memories", response_model=List[schemas.MemoryResponse])
def get_place_memories(
    place_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    from sqlalchemy import func
    
    # Find mutual followers (friends) to handle privacy_level == 2
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

    memories_data = db.query(
        models.Memory,
        func.ST_Y(models.Memory.location).label('lat'),
        func.ST_X(models.Memory.location).label('lng')
    ).filter(
        models.Memory.place_id == place_id,
        (models.Memory.user_id == current_user.id) |
        ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.utcnow())) |
        ((models.Memory.privacy_level == 2) & models.Memory.user_id.in_(friend_ids))
    ).order_by(models.Memory.posted_at.desc()).limit(50).all()
    
    results = []
    for m, lat, lng in memories_data:
        likes_c = db.query(func.count(models.Like.memory_id)).filter(models.Like.memory_id == m.id).scalar() or 0
        comments_c = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == m.id).scalar() or 0
        liked_by_me = db.query(models.Like).filter(
            models.Like.memory_id == m.id,
            models.Like.user_id == current_user.id
        ).first() is not None
        
        m_res = schemas.MemoryResponse.model_validate(m)
        m_res.location = {"lat": lat, "lng": lng}
        m_res.likes_count = likes_c
        m_res.comments_count = comments_c
        m_res.is_liked = liked_by_me
        results.append(m_res)
        
    return results
