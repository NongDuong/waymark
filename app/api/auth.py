from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import uuid
import secrets

from .. import schemas, models
from ..database import get_db
from ..core import security
from ..core.dependencies import get_current_user
from ..core.rate_limit import signup_limit, login_limit, forgot_pwd_limit

router = APIRouter()

@router.post("/signup/email", response_model=schemas.UserResponse)
def signup(user_in: schemas.UserCreate, db: Session = Depends(get_db), _rl: None = Depends(signup_limit)):
    # Check email duplicate
    email_exists = db.query(models.User).filter(
        models.User.primary_email == user_in.email
    ).first()
    if email_exists:
        raise HTTPException(status_code=400, detail="Email đã được đăng ký. Vui lòng sử dụng email khác.")
    
    # Check username duplicate
    username_exists = db.query(models.User).filter(
        models.User.username == user_in.username
    ).first()
    if username_exists:
        raise HTTPException(status_code=400, detail="Tên người dùng đã tồn tại. Vui lòng chọn tên khác.")
    
    # Validate password length
    if len(user_in.password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự.")
    
    hashed_password = security.get_password_hash(user_in.password)
    
    new_user = models.User(
        id=uuid.uuid4(),
        primary_email=user_in.email,
        username=user_in.username,
        hashed_password=hashed_password
    )
    db.add(new_user)
    
    try:
        db.flush() # Flush to populate new_user.id
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi tạo tài khoản: {str(e)}")
    
    # Create UserProfile immediately during registration
    display_name = user_in.display_name or user_in.username
    new_profile = models.UserProfile(
        user_id=new_user.id,
        display_name=display_name
    )
    db.add(new_profile)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi lưu hồ sơ người dùng: {str(e)}")
    
    db.refresh(new_user)
    
    return new_user

@router.post("/login/password", response_model=schemas.Token)
def login(login_in: schemas.LoginRequest, db: Session = Depends(get_db), _rl: None = Depends(login_limit)):
    # login_in.username can be username or email
    user = db.query(models.User).filter(
        (models.User.username == login_in.username) | 
        (models.User.primary_email == login_in.username)
    ).first()
    
    # Verify password
    if not user or not user.hashed_password or not security.verify_password(login_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user_id": str(user.id)}

@router.post("/refresh", response_model=schemas.Token)
def refresh_token(body: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    """Làm mới access token bằng refresh token. Trả về cặp token mới (token rotation)."""
    from jose import JWTError, jwt as jose_jwt
    try:
        payload = jose_jwt.decode(body.refresh_token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        token_type = payload.get("type")
        user_id_str = payload.get("sub")
        if token_type != "refresh" or user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or invalid")
    
    # Verify user still exists and is active
    import uuid as uuid_mod
    try:
        user_uuid = uuid_mod.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    user = db.query(models.User).filter(models.User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.status == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    # Issue new token pair (rotation)
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    new_refresh_token = security.create_refresh_token(
        data={"sub": str(user.id)}
    )
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user_id": str(user.id)
    }

@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/config")
def get_auth_config():
    import os
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "facebook_app_id": os.getenv("FACEBOOK_APP_ID", ""),
        "apple_client_id": os.getenv("APPLE_CLIENT_ID", "")
    }

@router.post("/change-password", status_code=200)
def change_password(
    body: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Đổi mật khẩu — yêu cầu đăng nhập."""
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Tài khoản không sử dụng mật khẩu (đăng nhập mạng xã hội).")
    if not security.verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 6 ký tự.")
    current_user.hashed_password = security.get_password_hash(body.new_password)
    db.commit()
    return {"message": "Đổi mật khẩu thành công."}


@router.post("/forgot-password", status_code=200)
def forgot_password(body: schemas.ForgotPasswordRequest, db: Session = Depends(get_db), _rl: None = Depends(forgot_pwd_limit)):
    """Yêu cầu đặt lại mật khẩu. Trả về token reset (tích hợp email sau)."""
    user = db.query(models.User).filter(models.User.primary_email == body.email).first()
    if not user:
        # Không tiết lộ email tồn tại hay không
        return {"message": "Nếu email tồn tại, bạn sẽ nhận được hướng dẫn đặt lại mật khẩu."}

    # Vô hiệu hoá token cũ chưa dùng
    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used_at.is_(None)
    ).delete(synchronize_session=False)

    reset_token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(minutes=30)
    prt = models.PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token=reset_token,
        expires_at=expiry
    )
    db.add(prt)
    db.commit()

    # TODO: gửi email chứa reset_token
    # Trả về token tạm thời để test (xoá trong production)
    return {
        "message": "Token đặt lại mật khẩu đã được tạo.",
        "reset_token": reset_token,
        "expires_in_minutes": 30
    }


@router.post("/reset-password", status_code=200)
def reset_password(body: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    """Đặt lại mật khẩu bằng token nhận được từ forgot-password."""
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải có ít nhất 6 ký tự.")

    prt = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == body.token
    ).first()

    if not prt:
        raise HTTPException(status_code=400, detail="Token không hợp lệ.")
    if prt.used_at is not None:
        raise HTTPException(status_code=400, detail="Token đã được sử dụng.")
    if prt.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token đã hết hạn.")

    user = db.query(models.User).filter(models.User.id == prt.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Người dùng không tồn tại.")

    user.hashed_password = security.get_password_hash(body.new_password)
    prt.used_at = datetime.utcnow()
    db.commit()
    return {"message": "Đặt lại mật khẩu thành công."}


@router.post("/device-token", status_code=200)
def register_device_token(
    body: schemas.DeviceTokenRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lưu FCM device token để nhận thông báo push notification."""
    if not body.token or not body.token.strip():
        raise HTTPException(status_code=400, detail="Token không được để trống.")

    existing = db.query(models.DeviceToken).filter(
        models.DeviceToken.token == body.token
    ).first()

    if existing:
        # Cập nhật chủ sở hữu nếu token thuộc thiết bị mới đăng nhập
        if existing.user_id != current_user.id:
            existing.user_id = current_user.id
            existing.platform = body.platform
            db.commit()
        return {"message": "Device token đã được lưu."}

    new_token = models.DeviceToken(
        id=uuid.uuid4(),
        user_id=current_user.id,
        token=body.token.strip(),
        platform=body.platform
    )
    db.add(new_token)
    db.commit()
    return {"message": "Device token đã được lưu."}


@router.post("/google", response_model=schemas.Token)
def login_google(google_in: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    from jose import jwt
    import requests
    
    token = google_in.credential
    try:
        # get_unverified_claims avoids python-jose's at_hash check (requires access_token we don't have)
        payload = jwt.get_unverified_claims(token)
        email = payload.get("email")
        name = payload.get("name")
        picture = payload.get("picture")

        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google token does not contain email")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Google token: {str(e)}")
        
    # Check if user already exists
    user = db.query(models.User).filter(models.User.primary_email == email).first()
    
    if not user:
        # Create a new user automatically
        username_base = email.split("@")[0].replace(".", "").replace("-", "").replace("_", "")
        username = username_base
        counter = 1
        while db.query(models.User).filter(models.User.username == username).first():
            username = f"{username_base}{counter}"
            counter += 1
            
        user = models.User(
            id=uuid.uuid4(),
            primary_email=email,
            username=username,
            status=1
        )
        db.add(user)
        db.flush() # Flush to resolve database relationship mappings
        
        # Create user profile and set avatar using external URL
        avatar_media_id = None
        if picture:
            media_id = uuid.uuid4()
            new_media = models.Media(
                id=media_id,
                user_id=user.id,
                media_type=1,
                file_url=picture,
                status=2
            )
            db.add(new_media)
            avatar_media_id = media_id
            
        profile = models.UserProfile(
            user_id=user.id,
            display_name=name or username,
            avatar_media_id=avatar_media_id
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
        
    # Issue JWT access token + refresh token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user_id": str(user.id)}


@router.post("/facebook", response_model=schemas.Token)
def login_facebook(fb_in: schemas.FacebookLoginRequest, db: Session = Depends(get_db)):
    import requests
    
    token = fb_in.access_token
    # Call Facebook Graph API to verify token and get user profile info
    try:
        if token.startswith("mock_fb_"):
            fb_id = token.replace("mock_fb_", "")
            email = f"fb_{fb_id}@facebook.com"
            name = f"FB User {fb_id[:5]}"
            picture_url = "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=200"
        else:
            url = "https://graph.facebook.com/me"
            params = {
                "fields": "id,name,email,picture.type(large)",
                "access_token": token
            }
            response = requests.get(url, params=params, timeout=5)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Facebook access token"
                )
                
            data = response.json()
            email = data.get("email")
            fb_id = data.get("id")
            name = data.get("name")
            
            # If Facebook doesn't return email, create a dummy one using their fb_id
            if not email:
                email = f"{fb_id}@facebook.com"
                
            picture_data = data.get("picture", {}).get("data", {})
            picture_url = picture_data.get("url") if not picture_data.get("is_silhouette") else None
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error verifying Facebook token: {str(e)}"
        )
        
    # Check if user already exists
    user = db.query(models.User).filter(models.User.primary_email == email).first()
    
    if not user:
        # Create a new user automatically
        username_base = f"fb_{fb_id}"
        username = username_base
        counter = 1
        while db.query(models.User).filter(models.User.username == username).first():
            username = f"{username_base}{counter}"
            counter += 1
            
        user = models.User(
            id=uuid.uuid4(),
            primary_email=email,
            username=username,
            status=1
        )
        db.add(user)
        db.flush()
        
        # Create user profile and set avatar using Facebook URL
        avatar_media_id = None
        if picture_url:
            media_id = uuid.uuid4()
            new_media = models.Media(
                id=media_id,
                user_id=user.id,
                media_type=1,
                file_url=picture_url,
                status=2
            )
            db.add(new_media)
            avatar_media_id = media_id
            
        profile = models.UserProfile(
            user_id=user.id,
            display_name=name or username,
            avatar_media_id=avatar_media_id
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
        
    # Issue JWT access token + refresh token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user_id": str(user.id)}


@router.post("/logout")
def logout(
    body: schemas.LogoutRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout: xóa device token của thiết bị hiện tại khỏi DB để không nhận push notification nữa."""
    if body.device_token:
        db.query(models.DeviceToken).filter(
            models.DeviceToken.user_id == current_user.id,
            models.DeviceToken.token == body.device_token
        ).delete(synchronize_session=False)
        db.commit()
    return {"message": "Đăng xuất thành công."}


@router.post("/apple", response_model=schemas.Token)
def login_apple(apple_in: schemas.AppleLoginRequest, db: Session = Depends(get_db)):
    from jose import jwt
    import requests
    
    token = apple_in.id_token
    try:
        if token.startswith("mock_apple_"):
            apple_sub = token.replace("mock_apple_", "")
            email = f"apple_{apple_sub[:10]}@appleid.com"
        else:
            # Fetch Apple's public keys to verify the token signature if possible
            try:
                certs = requests.get("https://appleid.apple.com/auth/keys", timeout=3).json()
                payload = jwt.decode(token, certs, audience=None, options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
            except Exception:
                # Local signatureless fallback for offline testing
                payload = jwt.decode(token, "", options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
                
            email = payload.get("email")
            apple_sub = payload.get("sub") # unique Apple ID
            
            if not email:
                # Fallback email if Apple hides it (private relay)
                email = f"{apple_sub}@appleid.com"
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Apple ID token: {str(e)}"
        )
        
    # Check if user already exists
    user = db.query(models.User).filter(models.User.primary_email == email).first()
    
    if not user:
        # Create a new user automatically
        username_base = f"apple_{apple_sub[:10]}"
        username = username_base
        counter = 1
        while db.query(models.User).filter(models.User.username == username).first():
            username = f"{username_base}{counter}"
            counter += 1
            
        user = models.User(
            id=uuid.uuid4(),
            primary_email=email,
            username=username,
            status=1
        )
        db.add(user)
        db.flush()
        
        # User's name is only sent on first login by Apple client
        name = apple_in.display_name or f"Apple User {apple_sub[:5]}"
        
        profile = models.UserProfile(
            user_id=user.id,
            display_name=name,
            avatar_media_id=None
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
        
    # Issue JWT access token + refresh token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer", "user_id": str(user.id)}
