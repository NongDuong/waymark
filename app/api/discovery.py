from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user

from geoalchemy2 import Geography

router = APIRouter()

@router.get("/trending/nearby", response_model=List[schemas.MemoryResponse])
def get_trending_nearby(
    lat: float = Query(..., description="Center latitude"),
    lng: float = Query(..., description="Center longitude"),
    radius: float = Query(5000.0, description="Radius in meters"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # This is a simplified ranking function.
    # In reality, you'd calculate a score based on freshness + distance + engagement.
    # Here, we fetch recent public memories within the radius, ordering by how many likes they have (approximated or joined)
    # For MVP, just getting recent ones within radius.
    
    center_point = f"SRID=4326;POINT({lng} {lat})"
    
    query = db.query(models.Memory).filter(
        func.ST_DWithin(models.Memory.location.cast(Geography), center_point, radius),
        models.Memory.privacy_level == 3, # Public
        models.Memory.visibility_expires_at >= datetime.utcnow()
    ).order_by(models.Memory.posted_at.desc()).limit(20)
    
    trending_memories = query.all()
    results = []
    for m in trending_memories:
        coords = db.query(
            func.ST_Y(models.Memory.location).label('lat'),
            func.ST_X(models.Memory.location).label('lng')
        ).filter(models.Memory.id == m.id).first()
        
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
        if coords:
            m_res.location = {"lat": coords.lat, "lng": coords.lng}
            
        from .memories import populate_author_info
        populate_author_info(m_res, db)
        results.append(m_res)
    return results

@router.get("/clusters", response_model=List[schemas.ClusterResponse])
def get_map_clusters(
    bbox: str = Query(..., description="Bounding box 'minLng,minLat,maxLng,maxLat'"),
    zoom: int = Query(..., description="Map zoom level"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Dummy clustering API.
    Real implementation would use PostGIS ST_ClusterDBSCAN or Redis tile caching.
    """
    try:
        minLng, minLat, maxLng, maxLat = map(float, bbox.split(","))
    except ValueError:
        return []
        
    polygon = f"SRID=4326;POLYGON(({minLng} {minLat}, {minLng} {maxLat}, {maxLng} {maxLat}, {maxLng} {minLat}, {minLng} {minLat}))"
    
    # Just return simple count within bbox as a single cluster for MVP
    count = db.query(func.count(models.Memory.id)).filter(
        func.ST_Intersects(models.Memory.location, polygon),
        (models.Memory.user_id == current_user.id) |
        ((models.Memory.privacy_level == 3) & (models.Memory.visibility_expires_at >= datetime.utcnow()))
    ).scalar()
    
    if count > 0:
        center_lat = (minLat + maxLat) / 2
        center_lng = (minLng + maxLng) / 2
        return [{"lat": center_lat, "lng": center_lng, "count": count}]
    
    return []
