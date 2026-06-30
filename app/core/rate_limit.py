from fastapi import Request, Response, HTTPException, status
from fastapi_limiter.depends import RateLimiter


async def ip_identifier(request: Request):
    """Rate limit by IP address (for unauthenticated endpoints like login, signup)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    return ip + ":" + request.scope["path"]


async def user_identifier(request: Request):
    """Rate limit by user_id extracted from JWT (for authenticated endpoints)."""
    from jose import jwt as jose_jwt
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = jose_jwt.get_unverified_claims(token)
            user_id = payload.get("sub")
            if user_id:
                return user_id + ":" + request.scope["path"]
        except Exception:
            pass
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.client.host
    return ip + ":" + request.scope["path"]


async def _rate_limit_callback(request: Request, response: Response, pexpire: int):
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Quá nhiều yêu cầu. Vui lòng thử lại sau {pexpire // 1000} giây."
    )


# Auth — IP based
signup_limit     = RateLimiter(times=5,   hours=1,   identifier=ip_identifier, callback=_rate_limit_callback)
login_limit      = RateLimiter(times=10,  minutes=1, identifier=ip_identifier, callback=_rate_limit_callback)
forgot_pwd_limit = RateLimiter(times=3,   hours=1,   identifier=ip_identifier, callback=_rate_limit_callback)

# Social — user based
like_limit       = RateLimiter(times=200, hours=1,   identifier=user_identifier, callback=_rate_limit_callback)
comment_limit    = RateLimiter(times=30,  hours=1,   identifier=user_identifier, callback=_rate_limit_callback)
follow_limit     = RateLimiter(times=50,  hours=1,   identifier=user_identifier, callback=_rate_limit_callback)

# Chat — user based
message_limit    = RateLimiter(times=30,  minutes=1, identifier=user_identifier, callback=_rate_limit_callback)

# Memory — user based
memory_limit     = RateLimiter(times=20,  hours=24,  identifier=user_identifier, callback=_rate_limit_callback)
