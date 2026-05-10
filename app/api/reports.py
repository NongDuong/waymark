from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid

from .. import schemas, models
from ..database import get_db
from ..core.dependencies import get_current_user

router = APIRouter()

@router.post("", response_model=schemas.ReportResponse)
def create_report(
    report_in: schemas.ReportCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify target exists based on type
    target_summary = ""
    if report_in.target_type == 1:
        # Memory
        memory = db.query(models.Memory).filter(models.Memory.id == report_in.target_id).first()
        if not memory:
            raise HTTPException(status_code=404, detail="Bài viết không tồn tại.")
        target_summary = memory.caption[:100] if memory.caption else "[Hình ảnh]"
    elif report_in.target_type == 2:
        # Comment
        comment = db.query(models.Comment).filter(models.Comment.id == report_in.target_id).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Bình luận không tồn tại.")
        target_summary = comment.content[:100] if comment.content else "[Bình luận hình ảnh]"
    else:
        raise HTTPException(status_code=400, detail="Loại đối tượng báo cáo không hợp lệ (1 = Bài viết, 2 = Bình luận).")

    new_report = models.Report(
        id=uuid.uuid4(),
        reporter_id=current_user.id,
        target_id=report_in.target_id,
        target_type=report_in.target_type,
        reason=report_in.reason,
        details=report_in.details,
        status=1 # Pending
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    # Return response populated with reporter info
    response = schemas.ReportResponse.model_validate(new_report)
    response.reporter_username = current_user.username
    response.target_content_summary = target_summary
    
    profile = db.query(models.UserProfile).filter(models.UserProfile.user_id == current_user.id).first()
    if profile:
        response.reporter_display_name = profile.display_name
        
    return response
