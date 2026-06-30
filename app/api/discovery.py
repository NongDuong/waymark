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

    memories_data = db.query(
        models.Memory,
        func.ST_Y(models.Memory.location.cast(models.Geometry)).label('lat'),
        func.ST_X(models.Memory.location.cast(models.Geometry)).label('lng')
    ).filter(
        func.ST_DWithin(models.Memory.location.cast(Geography), center_point, radius),
        models.Memory.privacy_level == 3,
        models.Memory.visibility_expires_at >= datetime.utcnow(),
        models.Memory.deleted_at.is_(None)
    ).order_by(models.Memory.posted_at.desc()).limit(20).all()

    from .map import _batch_enrich_memories
    return _batch_enrich_memories(memories_data, db, current_user_id=current_user.id)

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
