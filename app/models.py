from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geography, Geometry
import uuid
from datetime import datetime, timedelta
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SmallInteger, default=1)
    is_admin = Column(Boolean, default=False)
    username = Column(String(30), unique=True, nullable=True)
    primary_email = Column(String(255), nullable=True) # citext in postgres
    hashed_password = Column(String(255), nullable=True)
    primary_phone = Column(String(20), nullable=True)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    phone_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    permissions = Column(JSONB, nullable=True, default=dict)
    is_vip = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    display_name = Column(String(80))
    avatar_media_id = Column(UUID(as_uuid=True), nullable=True)
    bio = Column(String(300))
    gender = Column(String(20), nullable=True)
    home_city = Column(String(120), nullable=True)
    country_code = Column(String(2), nullable=True)
    followers_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    total_likes_received = Column(Integer, default=0)
    memories_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Place(Base):
    __tablename__ = "places"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(30))
    provider_place_id = Column(String(128))
    name = Column(String(255))
    address_text = Column(String(500))
    country_code = Column(String(2))
    admin1 = Column(String(120))
    admin2 = Column(String(120))
    location = Column(Geometry(geometry_type='POINT', srid=4326))
    geohash = Column(String(16))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.id"), nullable=True)
    place_snapshot_id = Column(UUID(as_uuid=True), nullable=True) # ForeignKey placeholder
    privacy_level = Column(SmallInteger, default=3) # 1=private, 2=friends, 3=public
    visibility_status = Column(SmallInteger, default=1)
    caption = Column(Text)
    mood_code = Column(String(32), nullable=True)
    location = Column(Geometry(geometry_type='POINT', srid=4326))
    geohash = Column(String(16))
    taken_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    posted_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    comment_policy = Column(SmallInteger, default=1)
    language_code = Column(String(8), nullable=True)
    
    # Structured location data for statistics
    country = Column(String(100), nullable=True)
    admin1 = Column(String(120), nullable=True) # Province / State
    admin2 = Column(String(120), nullable=True) # District / City
    admin3 = Column(String(120), nullable=True) # Commune / Ward
    village = Column(String(120), nullable=True) # Village / Neighborhood
    address_text = Column(String(500), nullable=True)
    place_name = Column(String(255), nullable=True) # Name of specific location (e.g. Restaurant A)
    visibility_expires_at = Column(DateTime(timezone=True), default=lambda: datetime.utcnow() + timedelta(days=30))

class UserRelationship(Base):
    __tablename__ = "user_relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    relation_type = Column(SmallInteger, default=1) # 1=follow, 2=friend_request, 3=friend, 4=block, 5=mute
    status = Column(SmallInteger, default=1) # 1=pending, 2=accepted
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Like(Base):
    __tablename__ = "likes"
    
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memories.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class CommentLike(Base):
    __tablename__ = "comment_likes"
    
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memories.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    parent_comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)
    root_comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)
    content = Column(Text, nullable=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=True)
    status = Column(SmallInteger, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class Media(Base):
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memories.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    media_type = Column(SmallInteger, default=1) # 1=image, 2=video
    file_url = Column(String(500))
    thumbnail_url = Column(String(500), nullable=True)
    status = Column(SmallInteger, default=1) # 1=pending, 2=processed
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_type = Column(SmallInteger, default=1) # 1=direct, 2=group
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(255), nullable=True)
    last_message_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    last_read_message_id = Column(UUID(as_uuid=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    sender_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    message_type = Column(SmallInteger, default=1) # 1=text, 2=image
    text_content = Column(Text, nullable=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=True)
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String(100))
    description = Column(String(300), nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class CollectionItem(Base):
    __tablename__ = "collection_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"))
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memories.id"))
    added_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notification_type = Column(SmallInteger) # 1=like, 2=comment, 3=follow, 4=chat
    message = Column(Text)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_id = Column(UUID(as_uuid=True))  # ID of Memory or Comment
    target_type = Column(SmallInteger)      # 1 = Memory, 2 = Comment
    reason = Column(String(100))            # Reason for report
    details = Column(Text, nullable=True)   # Additional details
    status = Column(SmallInteger, default=1) # 1 = Pending, 2 = Resolved (action taken), 3 = Dismissed
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
