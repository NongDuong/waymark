from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import uuid
from typing import List, Optional

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user
from ..worker import send_notification

router = APIRouter()

@router.post("/memories/{memory_id}/likes", status_code=status.HTTP_201_CREATED)
def like_memory(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
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
    current_user: models.User = Depends(get_current_user)
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
    
    results = []
    for comment, username, display_name, avatar_media_id in comments:
        avatar_url = None
        if avatar_media_id:
            avatar_media = db.query(models.Media).filter_by(id=avatar_media_id).first()
            if avatar_media:
                from .media import get_r2_url
                avatar_url = get_r2_url(avatar_media.file_url)
                
        comment_media_url = None
        if comment.media_id:
            comment_media = db.query(models.Media).filter_by(id=comment.media_id).first()
            if comment_media:
                from .media import get_r2_url
                comment_media_url = get_r2_url(comment_media.file_url)

        # Count comment likes and check if liked by current user
        likes_count = db.query(models.CommentLike).filter_by(comment_id=comment.id).count()
        is_liked = db.query(models.CommentLike).filter_by(comment_id=comment.id, user_id=current_user.id).first() is not None

        r = schemas.CommentResponse.model_validate(comment)
        r.username = username
        r.display_name = display_name or username
        r.avatar_url = avatar_url
        r.parent_comment_id = comment.parent_comment_id
        r.media_url = comment_media_url
        r.likes_count = likes_count
        r.is_liked = is_liked
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
        
    db.query(models.CommentLike).filter_by(comment_id=comment_id).delete()
    db.query(models.Report).filter(models.Report.target_id == comment_id, models.Report.target_type == 2).delete()
    db.delete(comment)
    db.commit()
    return


@router.post("/users/follow", status_code=status.HTTP_201_CREATED)
def follow_user(
    follow_in: schemas.FollowCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.id == follow_in.target_user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    notifications = db.query(models.Notification).filter_by(user_id=current_user.id).order_by(models.Notification.created_at.desc()).limit(50).all()
    
    results = []
    for n in notifications:
        res = schemas.NotificationResponse.model_validate(n)
        if n.sender_id:
            sender = db.query(models.User).filter_by(id=n.sender_id).first()
            profile = db.query(models.UserProfile).filter_by(user_id=n.sender_id).first()
            if sender:
                res.sender_username = sender.username
                res.sender_display_name = profile.display_name if profile else sender.username
                if profile and profile.avatar_media_id:
                    avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                    if avatar_media:
                        from .media import get_r2_url
                        res.sender_avatar_url = get_r2_url(avatar_media.file_url)
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

@router.get("/followers", response_model=List[schemas.SimpleUserResponse])
def get_my_followers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Find everyone who follows current_user (target_user_id = current_user.id, relation_type = 1)
    relations = db.query(models.UserRelationship).filter_by(
        target_user_id=current_user.id,
        relation_type=1 # follow
    ).all()
    
    results = []
    from .media import get_r2_url
    for rel in relations:
        user = db.query(models.User).filter_by(id=rel.source_user_id).first()
        if user:
            profile = db.query(models.UserProfile).filter_by(user_id=rel.source_user_id).first()
            avatar_url = None
            if profile and profile.avatar_media_id:
                avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                if avatar_media:
                    avatar_url = get_r2_url(avatar_media.file_url)
            
            results.append(schemas.SimpleUserResponse(
                user_id=user.id,
                username=user.username,
                display_name=profile.display_name if profile else user.username,
                avatar_url=avatar_url
            ))
    return results


@router.get("/following", response_model=List[schemas.SimpleUserResponse])
def get_my_following(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Find everyone current_user follows (source_user_id = current_user.id, relation_type = 1)
    relations = db.query(models.UserRelationship).filter_by(
        source_user_id=current_user.id,
        relation_type=1 # follow
    ).all()
    
    results = []
    from .media import get_r2_url
    for rel in relations:
        user = db.query(models.User).filter_by(id=rel.target_user_id).first()
        if user:
            profile = db.query(models.UserProfile).filter_by(user_id=rel.target_user_id).first()
            avatar_url = None
            if profile and profile.avatar_media_id:
                avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                if avatar_media:
                    avatar_url = get_r2_url(avatar_media.file_url)
            
            results.append(schemas.SimpleUserResponse(
                user_id=user.id,
                username=user.username,
                display_name=profile.display_name if profile else user.username,
                avatar_url=avatar_url
            ))
    return results


@router.get("/friends", response_model=List[schemas.SimpleUserResponse])
def get_my_friends(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Find mutual followers (friends)
    following_ids = db.query(models.UserRelationship.target_user_id).filter_by(
        source_user_id=current_user.id,
        relation_type=1
    ).subquery()
    
    mutual_relations = db.query(models.UserRelationship).filter(
        models.UserRelationship.target_user_id == current_user.id,
        models.UserRelationship.relation_type == 1,
        models.UserRelationship.source_user_id.in_(following_ids)
    ).all()
    
    results = []
    from .media import get_r2_url
    for rel in mutual_relations:
        user = db.query(models.User).filter_by(id=rel.source_user_id).first()
        if user:
            profile = db.query(models.UserProfile).filter_by(user_id=rel.source_user_id).first()
            avatar_url = None
            if profile and profile.avatar_media_id:
                avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                if avatar_media:
                    avatar_url = get_r2_url(avatar_media.file_url)
            
            results.append(schemas.SimpleUserResponse(
                user_id=user.id,
                username=user.username,
                display_name=profile.display_name if profile else user.username,
                avatar_url=avatar_url
            ))
    return results


@router.get("/memories/{memory_id}/likes", response_model=List[schemas.SimpleUserResponse])
def get_memory_likes(
    memory_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    likes = db.query(models.Like).filter_by(memory_id=memory_id).all()
    
    results = []
    from .media import get_r2_url
    for l in likes:
        user = db.query(models.User).filter_by(id=l.user_id).first()
        if user:
            profile = db.query(models.UserProfile).filter_by(user_id=l.user_id).first()
            avatar_url = None
            if profile and profile.avatar_media_id:
                avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                if avatar_media:
                    avatar_url = get_r2_url(avatar_media.file_url)
            
            results.append(schemas.SimpleUserResponse(
                user_id=user.id,
                username=user.username,
                display_name=profile.display_name if profile else user.username,
                avatar_url=avatar_url
            ))
    return results
