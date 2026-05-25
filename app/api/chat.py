from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import uuid
import json
from typing import List, Dict

from .. import schemas, models
from ..database import get_db, SessionLocal
from ..core.dependencies import get_current_user

router = APIRouter()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        # user_id -> list of active websockets (supports multiple devices)
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast_to_participants(self, message: dict, participant_ids: List[uuid.UUID]):
        for uid in participant_ids:
            await self.send_personal_message(message, str(uid))

manager = ConnectionManager()

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Manual token validation for WebSocket (since Depends(get_current_user) is tricky with WS)
    from ..core.dependencies import verify_token
    user_id = verify_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive, we don't expect messages from client via WS for now 
            # (we use REST POST for sending to keep business logic centralized)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


def enrich_conversation(c, current_user, db) -> schemas.ConversationResponse:
    from .media import get_r2_url
    res = schemas.ConversationResponse(
        id=c.id,
        conversation_type=c.conversation_type,
        created_by=c.created_by,
        title=c.title,
        last_message_id=c.last_message_id,
        created_at=c.created_at,
        updated_at=c.updated_at
    )
    
    res.is_pending = False
    
    if c.last_message_id:
        last_msg = db.query(models.Message).filter_by(id=c.last_message_id).first()
        if last_msg:
            res.last_message_text = last_msg.text_content or "[Hình ảnh]"
            res.last_message_sender_id = last_msg.sender_user_id

    if c.conversation_type == 1:
        other_p = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == c.id,
            models.ConversationParticipant.user_id != current_user.id
        ).first()
        
        if other_p:
            other_user = db.query(models.User).filter_by(id=other_p.user_id).first()
            if other_user:
                res.other_user_id = other_user.id
                res.other_user_username = other_user.username
                
                profile = db.query(models.UserProfile).filter_by(user_id=other_user.id).first()
                if profile:
                    res.other_user_display_name = profile.display_name or other_user.username
                    if profile.avatar_media_id:
                        avatar_media = db.query(models.Media).filter_by(id=profile.avatar_media_id).first()
                        if avatar_media:
                            res.other_user_avatar_url = get_r2_url(avatar_media.file_url)
                
                if not res.other_user_display_name:
                    res.other_user_display_name = other_user.username
                    
                i_follow = db.query(models.UserRelationship).filter_by(
                    source_user_id=current_user.id,
                    target_user_id=other_user.id,
                    relation_type=1
                ).first() is not None
                
                they_follow = db.query(models.UserRelationship).filter_by(
                    source_user_id=other_user.id,
                    target_user_id=current_user.id,
                    relation_type=1
                ).first() is not None
                
                if not (i_follow and they_follow):
                    res.is_pending = True
                else:
                    res.is_pending = False
                    
                res.title = res.other_user_display_name
                
    return res

@router.get("", response_model=List[schemas.ConversationResponse])
async def get_conversations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Get conversation IDs the user is part of
    participant_records = db.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.user_id == current_user.id
    ).all()
    
    conv_ids = [p.conversation_id for p in participant_records]
    
    conversations = db.query(models.Conversation).filter(
        models.Conversation.id.in_(conv_ids)
    ).order_by(models.Conversation.updated_at.desc()).all()
    
    results = []
    for c in conversations:
        # Check block relation first if direct
        if c.conversation_type == 1:
            other_p = db.query(models.ConversationParticipant).filter(
                models.ConversationParticipant.conversation_id == c.id,
                models.ConversationParticipant.user_id != current_user.id
            ).first()
            if other_p:
                block_check = db.query(models.UserRelationship).filter(
                    models.UserRelationship.relation_type == 4, # block
                    ((models.UserRelationship.source_user_id == current_user.id) & (models.UserRelationship.target_user_id == other_p.user_id)) |
                    ((models.UserRelationship.source_user_id == other_p.user_id) & (models.UserRelationship.target_user_id == current_user.id))
                ).first()
                if block_check:
                    continue # Skip blocked conversation completely
        
        results.append(enrich_conversation(c, current_user, db))
    return results

@router.post("", response_model=schemas.ConversationResponse)
async def create_conversation(
    conv_in: schemas.ConversationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Determine type
    is_direct = len(conv_in.participant_user_ids) == 1
    c_type = 1 if is_direct else 2
    
    new_conv = models.Conversation(
        id=uuid.uuid4(),
        conversation_type=c_type,
        created_by=current_user.id,
        title=conv_in.title
    )
    db.add(new_conv)
    
    # Add participants
    participants = set(conv_in.participant_user_ids)
    participants.add(current_user.id)
    
    for uid in participants:
        p = models.ConversationParticipant(
            id=uuid.uuid4(),
            conversation_id=new_conv.id,
            user_id=uid
        )
        db.add(p)
        
    db.commit()
    db.refresh(new_conv)
    return enrich_conversation(new_conv, current_user, db)

@router.get("/{conversation_id}/messages", response_model=List[schemas.MessageResponse])
async def get_messages(
    conversation_id: uuid.UUID,
    limit: int = 50,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify participation
    participant = db.query(models.ConversationParticipant).filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant of this conversation")
        
    messages = db.query(models.Message).filter_by(
        conversation_id=conversation_id
    ).order_by(models.Message.sent_at.desc()).offset(skip).limit(limit).all()
    
    results = []
    from .media import get_r2_url
    for msg in messages:
        m_res = schemas.MessageResponse.model_validate(msg)
        if msg.media_id:
            media_record = db.query(models.Media).filter_by(id=msg.media_id).first()
            if media_record:
                m_res.media_url = get_r2_url(media_record.file_url)
        results.append(m_res)
        
    return results

@router.post("/{conversation_id}/messages", response_model=schemas.MessageResponse)
async def send_message(
    conversation_id: uuid.UUID,
    msg_in: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Verify participation
    participant = db.query(models.ConversationParticipant).filter_by(
        conversation_id=conversation_id,
        user_id=current_user.id
    ).first()
    
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant of this conversation")

    # Verify if blocked
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if conv and conv.conversation_type == 1:
        other_p = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conversation_id,
            models.ConversationParticipant.user_id != current_user.id
        ).first()
        if other_p:
            block_check = db.query(models.UserRelationship).filter(
                models.UserRelationship.relation_type == 4, # block
                ((models.UserRelationship.source_user_id == current_user.id) & (models.UserRelationship.target_user_id == other_p.user_id)) |
                ((models.UserRelationship.source_user_id == other_p.user_id) & (models.UserRelationship.target_user_id == current_user.id))
            ).first()
            if block_check:
                raise HTTPException(status_code=403, detail="Bạn không thể gửi tin nhắn cho người dùng này do có thiết lập chặn.")
        
    new_msg = models.Message(
        id=uuid.uuid4(),
        conversation_id=conversation_id,
        sender_user_id=current_user.id,
        message_type=1 if msg_in.text_content else 2,
        text_content=msg_in.text_content,
        media_id=msg_in.media_id,
        reply_to_message_id=msg_in.reply_to_message_id
    )
    db.add(new_msg)
    
    # Update conversation last_message_id and updated_at
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    conv.last_message_id = new_msg.id
    from datetime import datetime
    conv.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_msg)
    
    m_res = schemas.MessageResponse.model_validate(new_msg)
    if new_msg.media_id:
        media_record = db.query(models.Media).filter_by(id=new_msg.media_id).first()
        if media_record:
            from .media import get_r2_url
            m_res.media_url = get_r2_url(media_record.file_url)
            
    # Notify participants via WebSocket
    participants = db.query(models.ConversationParticipant).filter_by(conversation_id=conversation_id).all()
    participant_ids = [p.user_id for p in participants]
    
    # Prepare payload for WS
    from fastapi.encoders import jsonable_encoder
    ws_payload = {
        "type": "new_message",
        "conversation_id": str(conversation_id),
        "message": jsonable_encoder(m_res)
    }
    
    await manager.broadcast_to_participants(ws_payload, participant_ids)
            
    return m_res
