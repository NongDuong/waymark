from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: Optional[UUID] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=6, max_length=128)
    display_name: Optional[str] = Field(None, max_length=50)

class GoogleLoginRequest(BaseModel):
    credential: str

class FacebookLoginRequest(BaseModel):
    access_token: str

class AppleLoginRequest(BaseModel):
    id_token: str
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str  # username hoặc email
    password: str

class UserResponse(BaseModel):
    id: UUID
    username: str
    primary_email: EmailStr
    is_admin: bool = False
    is_vip: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True

# Memory Schemas
class LocationInput(BaseModel):
    lat: float
    lng: float

class MemoryCreate(BaseModel):
    caption: str = Field(min_length=1, max_length=2000)
    location: LocationInput
    mood_code: Optional[str] = Field(None, max_length=50)
    privacy_level: int = 3
    place_id: Optional[UUID] = None

class MemoryUpdate(BaseModel):
    caption: Optional[str] = Field(None, min_length=1, max_length=2000)
    mood_code: Optional[str] = Field(None, max_length=50)
    privacy_level: Optional[int] = None

class MemoryResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    caption: str
    mood_code: Optional[str]
    privacy_level: int
    taken_at: datetime
    visibility_expires_at: Optional[datetime] = None
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    location: Optional[Any] = None
    media: Optional[List['MediaResponse']] = []
    
    # Location components
    country: Optional[str] = None
    admin1: Optional[str] = None
    admin2: Optional[str] = None
    admin3: Optional[str] = None
    village: Optional[str] = None
    address_text: Optional[str] = None
    place_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class MediaResponse(BaseModel):
    id: UUID
    media_type: int
    file_url: str
    thumbnail_url: Optional[str] = None
    status: int
    
    class Config:
        from_attributes = True

class MemoryDetailResponse(MemoryResponse):
    location: Any # we can format this better later
    media: Optional[List[MediaResponse]] = []
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[str] = None

class CommentResponse(BaseModel):
    id: UUID
    user_id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    parent_comment_id: Optional[UUID] = None
    content: Optional[str] = None
    media_url: Optional[str] = None
    created_at: datetime
    likes_count: int = 0
    is_liked: bool = False
    
    class Config:
        from_attributes = True

class FollowCreate(BaseModel):
    target_user_id: UUID

class PlaceCreate(BaseModel):
    provider: str
    provider_place_id: str
    name: str
    address_text: str
    country_code: str
    admin1: str
    admin2: str
    location: LocationInput

class PlaceResponse(BaseModel):
    id: UUID
    provider: str
    name: str
    address_text: str
    country_code: str
    
    class Config:
        from_attributes = True

class ClusterResponse(BaseModel):
    lat: float
    lng: float
    count: int

class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    home_city: Optional[str] = None
    country_code: Optional[str] = None
    avatar_media_id: Optional[UUID] = None

class UserProfileResponse(BaseModel):
    user_id: UUID
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    home_city: Optional[str] = None
    country_code: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    total_likes_received: int = 0
    memories_count: int = 0
    is_following: bool = False
    is_blocked: bool = False
    is_admin: bool = False
    is_super_admin: bool = False
    is_vip: bool = False
    
    class Config:
        from_attributes = True

class SimpleUserResponse(BaseModel):
    user_id: UUID
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserLocationStats(BaseModel):
    total_memories: int
    total_countries: int
    total_provinces: int # admin1
    total_districts: int # admin2
    total_communes: int # admin3
    total_places: int
    countries: List[str]
    provinces: List[str]

# Chat Schemas
class MessageCreate(BaseModel):
    text_content: Optional[str] = None
    media_id: Optional[UUID] = None
    reply_to_message_id: Optional[UUID] = None

class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_user_id: UUID
    message_type: int
    text_content: Optional[str] = None
    media_id: Optional[UUID] = None
    media_url: Optional[str] = None
    reply_to_message_id: Optional[UUID] = None
    sent_at: datetime
    
    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    participant_user_ids: List[UUID]
    title: Optional[str] = None
    conversation_type: int = 1 # 1=direct, 2=group

class ConversationResponse(BaseModel):
    id: UUID
    conversation_type: int
    created_by: UUID
    title: Optional[str] = None
    last_message_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    # Message Request / Follower relationship metadata
    is_pending: bool = False
    is_existing: bool = False
    other_user_id: Optional[UUID] = None
    other_user_username: Optional[str] = None
    other_user_display_name: Optional[str] = None
    other_user_avatar_url: Optional[str] = None
    last_message_text: Optional[str] = None
    last_message_sender_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True

# Collection Schemas
class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

class CollectionResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    is_public: bool
    created_at: datetime
    cover_image_url: Optional[str] = None
    items_count: int = 0
    
    class Config:
        from_attributes = True

class CollectionItemCreate(BaseModel):
    memory_id: UUID

class CollectionItemResponse(BaseModel):
    id: UUID
    collection_id: UUID
    memory_id: UUID
    added_at: datetime
    
    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    sender_id: Optional[UUID] = None
    sender_username: Optional[str] = None
    sender_display_name: Optional[str] = None
    sender_avatar_url: Optional[str] = None
    notification_type: int
    message: str
    reference_id: Optional[UUID] = None
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Reports Schemas
class ReportCreate(BaseModel):
    target_id: UUID
    target_type: int # 1 = Memory, 2 = Comment
    reason: str
    details: Optional[str] = None

class ReportResponse(BaseModel):
    id: UUID
    reporter_id: UUID
    target_id: UUID
    target_type: int
    reason: str
    details: Optional[str] = None
    status: int
    created_at: datetime
    updated_at: datetime
    reporter_username: Optional[str] = None
    reporter_display_name: Optional[str] = None
    target_content_summary: Optional[str] = None # Quick summary of what was reported

    class Config:
        from_attributes = True

class ReportResolveRequest(BaseModel):
    status: int # 2 = Resolved, 3 = Dismissed

# Admin Management Schemas
class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    is_admin: bool = False
    is_vip: bool = False
    permissions: Optional[dict] = None

class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[int] = None
    is_admin: Optional[bool] = None
    is_vip: Optional[bool] = None
    permissions: Optional[dict] = None

class AdminUserResponse(BaseModel):
    id: UUID
    username: str
    primary_email: EmailStr
    status: int
    is_admin: bool
    is_vip: bool = False
    permissions: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class DeviceTokenRequest(BaseModel):
    token: str
    platform: Optional[str] = None  # 'ios', 'android', 'web'

class LogoutRequest(BaseModel):
    device_token: Optional[str] = None

# Resolve forward references for MemoryResponse -> MediaResponse
MemoryResponse.model_rebuild()
MemoryDetailResponse.model_rebuild()
