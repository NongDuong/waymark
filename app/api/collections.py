from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import List

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user

router = APIRouter()

@router.get("", response_model=List[schemas.CollectionResponse])
def get_collections(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    collections = db.query(models.Collection).filter(
        models.Collection.user_id == current_user.id
    ).order_by(models.Collection.created_at.desc()).all()
    
    return collections

@router.post("", response_model=schemas.CollectionResponse)
def create_collection(
    col_in: schemas.CollectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_col = models.Collection(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=col_in.name,
        description=col_in.description,
        is_public=col_in.is_public
    )
    db.add(new_col)
    db.commit()
    db.refresh(new_col)
    return new_col

@router.get("/{collection_id}/items", response_model=List[schemas.MemoryResponse])
def get_collection_items(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check collection exists and is public or owned by user
    collection = db.query(models.Collection).filter_by(id=collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
        
    if collection.user_id != current_user.id and not collection.is_public:
        raise HTTPException(status_code=403, detail="Collection is private")
        
    items = db.query(models.CollectionItem).filter_by(collection_id=collection_id).all()
    memory_ids = [item.memory_id for item in items]
    
    if not memory_ids:
        return []
        
    from sqlalchemy import func
    memories_data = db.query(
        models.Memory,
        func.ST_Y(models.Memory.location).label('lat'),
        func.ST_X(models.Memory.location).label('lng')
    ).filter(models.Memory.id.in_(memory_ids)).all()
    
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

@router.post("/{collection_id}/items", response_model=schemas.CollectionItemResponse)
def add_collection_item(
    collection_id: uuid.UUID,
    item_in: schemas.CollectionItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    collection = db.query(models.Collection).filter_by(id=collection_id).first()
    if not collection or collection.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this collection")
        
    memory = db.query(models.Memory).filter_by(id=item_in.memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
        
    # Check if already added
    existing = db.query(models.CollectionItem).filter_by(
        collection_id=collection_id,
        memory_id=item_in.memory_id
    ).first()
    
    if existing:
        return existing
        
    new_item = models.CollectionItem(
        id=uuid.uuid4(),
        collection_id=collection_id,
        memory_id=item_in.memory_id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item
