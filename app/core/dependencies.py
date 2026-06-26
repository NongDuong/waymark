from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from ..database import get_db
from ..models import User
from .security import SECRET_KEY, ALGORITHM

# Dùng HTTPBearer thay cho OAuth2PasswordBearer vì login endpoint giờ nhận JSON
bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        token_data = {"user_id": user_id_str}
    except JWTError:
        raise credentials_exception
        
    try:
        user_uuid = uuid.UUID(token_data["user_id"])
    except ValueError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise credentials_exception
    if user.status == 0: # 0 means inactive or blocked
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Returns the authenticated user or None if no/invalid token provided."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            return None
        user_uuid = uuid.UUID(user_id_str)
        user = db.query(User).filter(User.id == user_uuid).first()
        if user is None or user.status == 0:
            return None
        return user
    except (JWTError, ValueError):
        return None

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    is_super_admin = getattr(current_user, "is_admin", False)
    perms = getattr(current_user, "permissions", None) or {}
    has_any_permission = any(perms.values()) if isinstance(perms, dict) else False
    
    if not (is_super_admin or has_any_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản không có quyền truy cập quản trị."
        )
    return current_user

def get_super_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản không có quyền quản trị tối cao (Super Admin)."
        )
    return current_user


def check_permission(permission_name: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if getattr(current_user, "is_admin", False):
            return current_user  # Admin tối cao luôn có mọi quyền
            
        perms = getattr(current_user, "permissions", None) or {}
        if not perms.get(permission_name, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản không có quyền hạn: {permission_name}"
            )
        return current_user
    return dependency
