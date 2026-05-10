from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from typing import List, Optional
from datetime import datetime

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_admin_user, get_super_admin_user
from ..core.security import pwd_context

router = APIRouter()

# --- REPORTS ENDPOINTS ---

@router.get("/reports", response_model=List[schemas.ReportResponse])
def get_reports(
    status: Optional[int] = Query(None, description="1=Pending, 2=Resolved, 3=Dismissed"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user)
):
    query = db.query(models.Report)
    if status is not None:
        query = query.filter(models.Report.status == status)
        
    reports = query.order_by(models.Report.created_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    for r in reports:
        res = schemas.ReportResponse.model_validate(r)
        
        # Populate reporter info
        reporter = db.query(models.User).filter_by(id=r.reporter_id).first()
        if reporter:
            res.reporter_username = reporter.username
            profile = db.query(models.UserProfile).filter_by(user_id=r.reporter_id).first()
            if profile:
                res.reporter_display_name = profile.display_name or reporter.username
        
        # Populate target content summary
        if r.target_type == 1:
            m = db.query(models.Memory).filter_by(id=r.target_id).first()
            res.target_content_summary = f"[Bài đăng] {m.caption[:100]}" if m and m.caption else "[Bài đăng hình ảnh]"
        elif r.target_type == 2:
            c = db.query(models.Comment).filter_by(id=r.target_id).first()
            res.target_content_summary = f"[Bình luận] {c.content[:100]}" if c and c.content else "[Bình luận hình ảnh]"
            
        results.append(res)
        
    return results

@router.patch("/reports/{report_id}", response_model=schemas.ReportResponse)
def resolve_report(
    report_id: uuid.UUID,
    resolve_in: schemas.ReportResolveRequest,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user)
):
    report = db.query(models.Report).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Báo cáo không tồn tại.")
        
    report.status = resolve_in.status
    report.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    
    # Return formatted response
    res = schemas.ReportResponse.model_validate(report)
    reporter = db.query(models.User).filter_by(id=report.reporter_id).first()
    if reporter:
        res.reporter_username = reporter.username
        profile = db.query(models.UserProfile).filter_by(user_id=report.reporter_id).first()
        if profile:
            res.reporter_display_name = profile.display_name
            
    return res


# --- USER MANAGEMENT ENDPOINTS ---

@router.get("/users", response_model=List[schemas.AdminUserResponse])
def get_users(
    search: Optional[str] = Query(None, description="Tìm kiếm theo username hoặc email"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    query = db.query(models.User)
    if search:
        query = query.filter(
            (models.User.username.ilike(f"%{search}%")) |
            (models.User.primary_email.ilike(f"%{search}%"))
        )
    users = query.order_by(models.User.created_at.desc()).offset(skip).limit(limit).all()
    return users

@router.post("/users", response_model=schemas.AdminUserResponse)
def create_user(
    user_in: schemas.AdminUserCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    # Check if exists
    existing = db.query(models.User).filter(
        (models.User.username == user_in.username) |
        (models.User.primary_email == user_in.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username hoặc Email đã được sử dụng.")
        
    user_id = uuid.uuid4()
    hashed_password = pwd_context.hash(user_in.password)
    
    new_user = models.User(
        id=user_id,
        username=user_in.username,
        primary_email=user_in.email,
        hashed_password=hashed_password,
        status=1, # active
        is_admin=user_in.is_admin,
        is_vip=user_in.is_vip,
        permissions=user_in.permissions or {},
        email_verified_at=datetime.utcnow()
    )
    db.add(new_user)
    
    # Create profile
    profile = models.UserProfile(
        user_id=user_id,
        display_name=user_in.username,
        bio=""
    )
    db.add(profile)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.patch("/users/{user_id}", response_model=schemas.AdminUserResponse)
def update_user(
    user_id: uuid.UUID,
    user_in: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
        
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "email":
            user.primary_email = value
        else:
            setattr(user, field, value)
            
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_super_admin_user)
):
    user = db.query(models.User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
        
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Bạn không thể tự xóa chính tài khoản Admin của mình.")
        
    # --- CASCADE DELETIONS FOR DATABASE INTEGRITY ---
    
    # Delete likes by this user
    db.query(models.Like).filter_by(user_id=user_id).delete()
    db.query(models.CommentLike).filter_by(user_id=user_id).delete()
    
    # Delete comments by this user
    comment_ids = [c.id for c in db.query(models.Comment).filter_by(user_id=user_id).all()]
    if comment_ids:
        db.query(models.CommentLike).filter(models.CommentLike.comment_id.in_(comment_ids)).delete()
        db.query(models.Comment).filter(models.Comment.id.in_(comment_ids)).delete()
        
    # Delete memories by this user (including cascade comments and likes of those memories)
    memories = db.query(models.Memory).filter_by(user_id=user_id).all()
    for m in memories:
        db.query(models.Like).filter_by(memory_id=m.id).delete()
        m_comment_ids = [c.id for c in db.query(models.Comment).filter_by(memory_id=m.id).all()]
        if m_comment_ids:
            db.query(models.CommentLike).filter(models.CommentLike.comment_id.in_(m_comment_ids)).delete()
            db.query(models.Comment).filter(models.Comment.id.in_(m_comment_ids)).delete()
        db.query(models.Media).filter_by(memory_id=m.id).delete()
        db.query(models.CollectionItem).filter_by(memory_id=m.id).delete()
        db.query(models.Report).filter(models.Report.target_id == m.id, models.Report.target_type == 1).delete()
        db.delete(m)
        
    # Delete social relations
    db.query(models.UserRelationship).filter(
        (models.UserRelationship.source_user_id == user_id) |
        (models.UserRelationship.target_user_id == user_id)
    ).delete()
    
    # Delete collections
    collection_ids = [c.id for c in db.query(models.Collection).filter_by(user_id=user_id).all()]
    if collection_ids:
        db.query(models.CollectionItem).filter(models.CollectionItem.collection_id.in_(collection_ids)).delete()
        db.query(models.Collection).filter(models.Collection.id.in_(collection_ids)).delete()
        
    # Delete media directly associated with user
    db.query(models.Media).filter_by(user_id=user_id).delete()
    
    # Delete reports filed by this user
    db.query(models.Report).filter_by(reporter_id=user_id).delete()
    
    # Delete reports filed against this user's comments
    # (Since comments of this user were already deleted above)
    
    # Delete profiles and user
    db.query(models.UserProfile).filter_by(user_id=user_id).delete()
    db.delete(user)
    
    db.commit()
    return


# --- MEMORY/COMMENT DIRECT MANAGEMENT ---

@router.get("/memories", response_model=List[schemas.MemoryDetailResponse])
def get_all_memories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user)
):
    memories = db.query(models.Memory).order_by(models.Memory.created_at.desc() if hasattr(models.Memory, "created_at") else models.Memory.taken_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    from .media import get_r2_url
    for m in memories:
        coords = db.query(
            func.ST_Y(models.Memory.location).label('lat'),
            func.ST_X(models.Memory.location).label('lng')
        ).filter(models.Memory.id == m.id).first()
        
        likes_count = db.query(func.count(models.Like.memory_id)).filter(models.Like.memory_id == m.id).scalar() or 0
        comments_count = db.query(func.count(models.Comment.id)).filter(models.Comment.memory_id == m.id).scalar() or 0
        
        res = schemas.MemoryDetailResponse.model_validate(m)
        res.likes_count = likes_count
        res.comments_count = comments_count
        res.is_liked = False
        
        if coords:
            res.location = {"lat": coords.lat, "lng": coords.lng}
            
        media_records = db.query(models.Media).filter_by(memory_id=m.id).all()
        res.media = []
        for mr in media_records:
            mr_schema = schemas.MediaResponse.model_validate(mr)
            mr_schema.file_url = get_r2_url(mr.file_url)
            res.media.append(mr_schema)
            
        # Author username / avatar
        author = db.query(models.User).filter_by(id=m.user_id).first()
        if author:
            res.username = author.username
            profile = db.query(models.UserProfile).filter_by(user_id=m.user_id).first()
            if profile:
                res.display_name = profile.display_name or author.username
                if profile.avatar_media_id:
                    avatar = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                    if avatar:
                        res.avatar_url = get_r2_url(avatar.file_url)
                        
        results.append(res)
        
    return results

@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_by_admin(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user)
):
    is_super_admin = getattr(admin, "is_admin", False)
    perms = getattr(admin, "permissions", None) or {}
    has_delete_perm = perms.get("can_delete_others_memories", False)
    
    if not is_super_admin and not has_delete_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản không có quyền xóa bài đăng kỷ niệm của người khác."
        )

    memory = db.query(models.Memory).filter_by(id=memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Bài đăng không tồn tại.")
        
    # Cascade deletions
    db.query(models.Like).filter_by(memory_id=memory_id).delete()
    comment_ids = [c.id for c in db.query(models.Comment).filter_by(memory_id=memory_id).all()]
    if comment_ids:
        db.query(models.CommentLike).filter(models.CommentLike.comment_id.in_(comment_ids)).delete()
        db.query(models.Comment).filter(models.Comment.id.in_(comment_ids)).delete()
        
    db.query(models.Media).filter_by(memory_id=memory_id).delete()
    db.query(models.CollectionItem).filter_by(memory_id=memory_id).delete()
    db.query(models.Report).filter(models.Report.target_id == memory_id, models.Report.target_type == 1).delete()
    
    # Decrement count
    db.query(models.UserProfile).filter(models.UserProfile.user_id == memory.user_id).update(
        {models.UserProfile.memories_count: func.greatest(0, models.UserProfile.memories_count - 1)}
    )
    
    db.delete(memory)
    db.commit()
    return

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment_by_admin(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin_user)
):
    is_super_admin = getattr(admin, "is_admin", False)
    perms = getattr(admin, "permissions", None) or {}
    has_delete_perm = perms.get("can_delete_others_comments", False)
    
    if not is_super_admin and not has_delete_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản không có quyền xóa bình luận của người khác."
        )

    comment = db.query(models.Comment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Bình luận không tồn tại.")
        
    db.query(models.CommentLike).filter_by(comment_id=comment_id).delete()
    db.query(models.Report).filter(models.Report.target_id == comment_id, models.Report.target_type == 2).delete()
    db.delete(comment)
    db.commit()
    return
