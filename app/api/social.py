from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from typing import List, Optional

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user
from ..worker import send_notification
from ..core.rate_limit import like_limit, comment_limit, follow_limit

router = APIRouter()

@router.post("/memories/{memory_id}/likes", status_code=status.HTTP_201_CREATED)
def like_memory(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _rl: None = Depends(like_limit)
):
    like = db.query(models.Like).filter_by(memory_id=memory_id, user_id=current_user.id).first()
    if like:
        return {"message": "Already liked"}
        
    new_like = models.Like(memory_id=memory_id, user_id=current_user.id)
    db.add(new_like)
    db.commit()
    
    # Notify memory owner
    memory = db.query(models.Memory).filter_by(id=memory_id).first()
    if memory and memory.user_id != current_user.id:
        sender_profile = db.query(models.UserProfile).filter_by(user_id=current_user.id).first()
        sender_name = (sender_profile.display_name if sender_profile else None) or current_user.username
        send_notification.delay(
            str(memory.user_id),
            f"{sender_name} đã thích kỷ niệm của bạn.",
            sender_id=str(current_user.id),
            notification_type=1,
            reference_id=str(memory_id)
        )
        
    return {"message": "Liked"}

@router.delete("/memories/{memory_id}/likes", status_code=status.HTTP_204_NO_CONTENT)
def unlike_memory(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    like = db.query(models.Like).filter_by(memory_id=memory_id, user_id=current_user.id).first()
    if like:
        db.delete(like)
        db.commit()
    return

@router.post("/memories/{memory_id}/comments", response_model=schemas.CommentResponse)
def add_comment(
    memory_id: uuid.UUID,
    content: Optional[str] = Form(None),
    parent_comment_id: Optional[str] = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _rl: None = Depends(comment_limit)
):
    if not content and not image:
        raise HTTPException(status_code=400, detail="Vui lòng nhập nội dung hoặc gửi ảnh.")

    # 1. Verify memory exists
    memory = db.query(models.Memory).filter_by(id=memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory không tồn tại.")
        
    # 2. Verify parent comment exists (if provided)
    parsed_parent_id = None
    if parent_comment_id and parent_comment_id.strip() != "":
        try:
            parsed_parent_id = uuid.UUID(parent_comment_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Mã bình luận cha (parent_comment_id) không đúng định dạng UUID. Vui lòng xóa bỏ hoặc nhập đúng chuẩn UUID."
            )
        parent_comment = db.query(models.Comment).filter_by(id=parsed_parent_id).first()
        if not parent_comment:
            raise HTTPException(
                status_code=400,
                detail="Bình luận cha (parent_comment_id) không tồn tại. Vui lòng để trống hoặc đặt thành null nếu đây là bình luận mới (gốc)."
            )

    media_id = None
    media_url = None
    if image and image.filename:
        from .media import s3_client, R2_BUCKET_NAME, get_r2_url
        media_id = uuid.uuid4()
        content_type = image.content_type
        
        if content_type and content_type.startswith("image/"):
            try:
                from ..core.image_optimizer import optimize_image
                import io
                image_bytes = image.file.read()
                optimized_bytes, content_type = optimize_image(image_bytes)
                upload_file_obj = io.BytesIO(optimized_bytes)
                ext = "webp"
            except Exception:
                image.file.seek(0)
                upload_file_obj = image.file
                ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
        else:
            upload_file_obj = image.file
            ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'

        object_key = f"comments/{current_user.id}/{media_id}.{ext}"
        public_url = f"https://pub-xxxxxx.r2.dev/{object_key}"
        
        if s3_client:
            try:
                s3_client.upload_fileobj(
                    upload_file_obj,
                    R2_BUCKET_NAME,
                    object_key,
                    ExtraArgs={"ContentType": content_type}
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to upload comment image: {str(e)}")
                
        new_media = models.Media(
            id=media_id,
            user_id=current_user.id,
            media_type=1,
            file_url=public_url,
            status=2
        )
        db.add(new_media)
        db.flush()  # Force database insert to avoid fk_comments_media_id violation
        media_url = get_r2_url(public_url)

    new_comment = models.Comment(
        id=uuid.uuid4(),
        memory_id=memory_id,
        user_id=current_user.id,
        content=content,
        media_id=media_id,
        parent_comment_id=parsed_parent_id
    )
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    # Notify memory owner
    if memory.user_id != current_user.id:
        sender_profile = db.query(models.UserProfile).filter_by(user_id=current_user.id).first()
        sender_name = (sender_profile.display_name if sender_profile else None) or current_user.username
        send_notification.delay(
            str(memory.user_id),
            f"{sender_name} đã bình luận về kỷ niệm của bạn.",
            sender_id=str(current_user.id),
            notification_type=2,
            reference_id=str(memory_id)
        )
        
    # Fetch profile and build response
    profile = db.query(models.UserProfile).filter_by(user_id=current_user.id).first()
    avatar_url = None
    if profile and profile.avatar_media_id:
        avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
        if avatar_media:
            from .media import get_r2_url
            avatar_url = get_r2_url(avatar_media.file_url)
            
    r = schemas.CommentResponse.model_validate(new_comment)
    r.username = current_user.username
    r.display_name = profile.display_name if profile else current_user.username
    r.avatar_url = avatar_url
    r.parent_comment_id = new_comment.parent_comment_id
    r.media_url = media_url
    return r

@router.get("/memories/{memory_id}/comments", response_model=List[schemas.CommentResponse])
def get_memory_comments(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify memory exists
    memory = db.query(models.Memory).filter_by(id=memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory không tồn tại.")
        
    # Fetch comments joined with User and UserProfile, excluding soft-deleted comments
    comments = db.query(
        models.Comment,
        models.User.username,
        models.UserProfile.display_name,
        models.UserProfile.avatar_media_id
    ).join(
        models.User, models.User.id == models.Comment.user_id
    ).outerjoin(
        models.UserProfile, models.UserProfile.user_id == models.Comment.user_id
    ).filter(
        models.Comment.memory_id == memory_id,
        models.Comment.deleted_at.is_(None)
    ).order_by(
        models.Comment.created_at.asc()
    ).all()
    
    # Batch-load all media needed (avatar + comment images) to avoid N+1
    from .media import get_r2_url
    all_media_ids = list({av for _, _, _, av in comments if av} |
                         {c.media_id for c, _, _, _ in comments if c.media_id})
    media_url_map = {}
    if all_media_ids:
        for m in db.query(models.Media).filter(models.Media.id.in_(all_media_ids)).all():
            media_url_map[m.id] = get_r2_url(m.file_url)

    # Batch-load comment likes counts and is_liked set
    comment_ids = [c.id for c, _, _, _ in comments]
    likes_count_map = {}
    liked_set = set()
    if comment_ids:
        likes_count_map = dict(
            db.query(models.CommentLike.comment_id, func.count())
            .filter(models.CommentLike.comment_id.in_(comment_ids))
            .group_by(models.CommentLike.comment_id).all()
        )
        liked_rows = db.query(models.CommentLike.comment_id).filter(
            models.CommentLike.comment_id.in_(comment_ids),
            models.CommentLike.user_id == current_user.id
        ).all()
        liked_set = {row[0] for row in liked_rows}

    results = []
    for comment, username, display_name, avatar_media_id in comments:
        r = schemas.CommentResponse.model_validate(comment)
        r.username = username
        r.display_name = display_name or username
        r.avatar_url = media_url_map.get(avatar_media_id) if avatar_media_id else None
        r.parent_comment_id = comment.parent_comment_id
        r.media_url = media_url_map.get(comment.media_id) if comment.media_id else None
        r.likes_count = likes_count_map.get(comment.id, 0)
        r.is_liked = comment.id in liked_set
        results.append(r)

    return results

@router.post("/comments/{comment_id}/likes", status_code=status.HTTP_201_CREATED)
def like_comment(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    comment = db.query(models.Comment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Bình luận không tồn tại.")
        
    existing_like = db.query(models.CommentLike).filter_by(comment_id=comment_id, user_id=current_user.id).first()
    if existing_like:
        return {"message": "Already liked"}
        
    new_like = models.CommentLike(comment_id=comment_id, user_id=current_user.id)
    db.add(new_like)
    db.commit()
    return {"message": "Liked"}

@router.delete("/comments/{comment_id}/likes", status_code=status.HTTP_204_NO_CONTENT)
def unlike_comment(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    existing_like = db.query(models.CommentLike).filter_by(comment_id=comment_id, user_id=current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        db.commit()
    return


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    comment = db.query(models.Comment).filter_by(id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
        
    memory = db.query(models.Memory).filter_by(id=comment.memory_id).first()
    
    is_comment_owner = (comment.user_id == current_user.id)
    is_memory_owner = (memory and memory.user_id == current_user.id)
    is_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_delete_perm = perms.get("can_delete_others_comments", False)
    
    if not is_comment_owner and not is_memory_owner and not is_admin and not has_delete_perm:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    from datetime import datetime as _dt
    comment.deleted_at = _dt.utcnow()
    db.commit()
    return


@router.post("/users/follow", status_code=status.HTTP_201_CREATED)
def follow_user(
    follow_in: schemas.FollowCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _rl: None = Depends(follow_limit)
):
    if current_user.id == follow_in.target_user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    target_user = db.query(models.User).filter_by(id=follow_in.target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
        
    rel = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id, 
        target_user_id=follow_in.target_user_id
    ).first()
    
    if rel:
        if rel.relation_type == 1:
            return {"message": "Already following"}
        else:
            rel.relation_type = 1
            rel.status = 2 # accepted by default for now
    else:
        rel = models.UserRelationship(
            id=uuid.uuid4(),
            source_user_id=current_user.id,
            target_user_id=follow_in.target_user_id,
            relation_type=1, # follow
            status=2 # accepted
        )
        db.add(rel)
        
    # Update counters in UserProfile
    # 1. Increment following_count for source user
    db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).update(
        {models.UserProfile.following_count: models.UserProfile.following_count + 1}
    )
    # 2. Increment followers_count for target user
    db.query(models.UserProfile).filter(models.UserProfile.user_id == follow_in.target_user_id).update(
        {models.UserProfile.followers_count: models.UserProfile.followers_count + 1}
    )
        
    db.commit()
    
    sender_profile = db.query(models.UserProfile).filter_by(user_id=current_user.id).first()
    sender_name = (sender_profile.display_name if sender_profile else None) or current_user.username
    send_notification.delay(
        str(follow_in.target_user_id),
        f"{sender_name} đã bắt đầu theo dõi bạn.",
        sender_id=str(current_user.id),
        notification_type=3,
        reference_id=str(current_user.id)
    )
    
    return {"message": "Followed successfully"}

@router.delete("/users/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    rel = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id, 
        target_user_id=user_id,
        relation_type=1 # follow
    ).first()
    
    if rel:
        db.delete(rel)
        
        # Update counters in UserProfile
        from sqlalchemy import func
        # 1. Decrement following_count for source user
        db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).update(
            {models.UserProfile.following_count: func.greatest(0, models.UserProfile.following_count - 1)}
        )
        # 2. Decrement followers_count for target user
        db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).update(
            {models.UserProfile.followers_count: func.greatest(0, models.UserProfile.followers_count - 1)}
        )
        
        db.commit()
    
    return

@router.get("/notifications", response_model=List[schemas.NotificationResponse])
def get_notifications(
    limit: int = 20,
    before_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.Notification).filter(models.Notification.user_id == current_user.id)
    if before_id:
        anchor = db.query(models.Notification).filter_by(id=before_id).first()
        if anchor:
            query = query.filter(models.Notification.created_at < anchor.created_at)
    notifications = query.order_by(models.Notification.created_at.desc()).limit(min(limit, 50)).all()

    # Batch-load senders to avoid N+1
    sender_ids = list({n.sender_id for n in notifications if n.sender_id})
    users_map = {}
    profiles_map = {}
    avatars_map = {}
    if sender_ids:
        from .media import get_r2_url
        users_map = {u.id: u for u in db.query(models.User).filter(models.User.id.in_(sender_ids)).all()}
        profiles_map = {p.user_id: p for p in db.query(models.UserProfile).filter(models.UserProfile.user_id.in_(sender_ids)).all()}
        avatar_ids = [p.avatar_media_id for p in profiles_map.values() if p and p.avatar_media_id]
        if avatar_ids:
            for av in db.query(models.Media).filter(models.Media.id.in_(avatar_ids)).all():
                avatars_map[av.id] = get_r2_url(av.file_url)

    results = []
    for n in notifications:
        res = schemas.NotificationResponse.model_validate(n)
        if n.sender_id:
            sender = users_map.get(n.sender_id)
            profile = profiles_map.get(n.sender_id)
            if sender:
                res.sender_username = sender.username
                res.sender_display_name = profile.display_name if profile else sender.username
                if profile and profile.avatar_media_id:
                    res.sender_avatar_url = avatars_map.get(profile.avatar_media_id)
        results.append(res)
    return results

@router.post("/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    notif = db.query(models.Notification).filter_by(id=notification_id, user_id=current_user.id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}

@router.post("/notifications/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db.query(models.Notification).filter_by(user_id=current_user.id, is_read=False).update({models.Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"message": "All notifications marked as read"}

@router.post("/users/{user_id}/block", status_code=status.HTTP_201_CREATED)
def block_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot block yourself")

    # Check if already blocked
    existing_block = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id,
        target_user_id=user_id,
        relation_type=4 # block
    ).first()

    if existing_block:
        return {"message": "User is already blocked"}

    # Determine if any follow relations exist and clear them
    # Direction 1: current_user follows user_id
    follow_1 = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id,
        target_user_id=user_id,
        relation_type=1 # follow
    ).first()
    if follow_1:
        db.delete(follow_1)
        from sqlalchemy import func
        db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).update(
            {models.UserProfile.following_count: func.greatest(0, models.UserProfile.following_count - 1)}
        )
        db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).update(
            {models.UserProfile.followers_count: func.greatest(0, models.UserProfile.followers_count - 1)}
        )

    # Direction 2: user_id follows current_user
    follow_2 = db.query(models.UserRelationship).filter_by(
        source_user_id=user_id,
        target_user_id=current_user.id,
        relation_type=1 # follow
    ).first()
    if follow_2:
        db.delete(follow_2)
        from sqlalchemy import func
        db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).update(
            {models.UserProfile.following_count: func.greatest(0, models.UserProfile.following_count - 1)}
        )
        db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).update(
            {models.UserProfile.followers_count: func.greatest(0, models.UserProfile.followers_count - 1)}
        )

    # Create block record
    new_block = models.UserRelationship(
        id=uuid.uuid4(),
        source_user_id=current_user.id,
        target_user_id=user_id,
        relation_type=4, # block
        status=2 # accepted
    )
    db.add(new_block)
    db.commit()

    return {"message": "User blocked successfully"}


@router.delete("/users/{user_id}/block", status_code=status.HTTP_204_NO_CONTENT)
def unblock_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    block = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id,
        target_user_id=user_id,
        relation_type=4 # block
    ).first()

    if block:
        db.delete(block)
        db.commit()

    return

def _build_simple_user_list(user_ids: list, db) -> list:
    """Batch-load user info to avoid N+1 queries."""
    from .media import get_r2_url
    if not user_ids:
        return []
    users = {u.id: u for u in db.query(models.User).filter(models.User.id.in_(user_ids)).all()}
    profiles = {p.user_id: p for p in db.query(models.UserProfile).filter(models.UserProfile.user_id.in_(user_ids)).all()}
    avatar_ids = [p.avatar_media_id for p in profiles.values() if p and p.avatar_media_id]
    avatars = {}
    if avatar_ids:
        for av in db.query(models.Media).filter(models.Media.id.in_(avatar_ids)).all():
            avatars[av.id] = get_r2_url(av.file_url)
    results = []
    for uid in user_ids:
        user = users.get(uid)
        if not user:
            continue
        profile = profiles.get(uid)
        results.append(schemas.SimpleUserResponse(
            user_id=user.id,
            username=user.username,
            display_name=profile.display_name if profile else user.username,
            avatar_url=avatars.get(profile.avatar_media_id) if profile and profile.avatar_media_id else None
        ))
    return results


@router.get("/followers", response_model=List[schemas.SimpleUserResponse])
def get_my_followers(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    relations = db.query(models.UserRelationship).filter_by(
        target_user_id=current_user.id, relation_type=1
    ).offset(offset).limit(min(limit, 100)).all()
    return _build_simple_user_list([r.source_user_id for r in relations], db)


@router.get("/following", response_model=List[schemas.SimpleUserResponse])
def get_my_following(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    relations = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id, relation_type=1
    ).offset(offset).limit(min(limit, 100)).all()
    return _build_simple_user_list([r.target_user_id for r in relations], db)


@router.get("/friends", response_model=List[schemas.SimpleUserResponse])
def get_my_friends(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    following_ids = db.query(models.UserRelationship.target_user_id).filter_by(
        source_user_id=current_user.id, relation_type=1
    ).subquery()
    mutual = db.query(models.UserRelationship.source_user_id).filter(
        models.UserRelationship.target_user_id == current_user.id,
        models.UserRelationship.relation_type == 1,
        models.UserRelationship.source_user_id.in_(following_ids)
    ).offset(offset).limit(min(limit, 100)).all()
    return _build_simple_user_list([r[0] for r in mutual], db)


@router.get("/memories/{memory_id}/likes", response_model=List[schemas.SimpleUserResponse])
def get_memory_likes(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    likes = db.query(models.Like).filter_by(memory_id=memory_id).all()
    return _build_simple_user_list([l.user_id for l in likes], db)
