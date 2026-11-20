import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def set_auth_cookies(response: Response, user_id: int) -> None:
    """Set HTTPOnly access_token cookie and plain csrf_token cookie."""
    access_token = create_access_token(user_id)
    csrf_token = secrets.token_hex(32)
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # Must be readable by JavaScript
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear both auth cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Returns the authenticated user if a valid access_token cookie is present,
    or None for guest access.
    """
    token = request.cookies.get("access_token")
    if token is None:
        return None

    try:
        # algorithms= is an explicit allow-list (never trust the token's own
        # "alg" header), and "require" rejects tokens missing exp/sub instead
        # of letting int(None) raise a TypeError that surfaced as a 500.
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    """Dependency that requires authentication (rejects guests)."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


async def require_superuser(
    user: User = Depends(require_user),
) -> User:
    """Dependency that requires the user to have is_admin=True."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return user


def _has_valid_admin_token(request: Request) -> bool:
    """True when the request carries `Authorization: Bearer <ADMIN_API_TOKEN>`.

    Always False when ADMIN_API_TOKEN is unset, so token auth is opt-in.
    Uses a constant-time comparison so the token can't be guessed by timing.
    """
    expected = settings.ADMIN_API_TOKEN
    if not expected:
        return False
    scheme, _, presented = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not presented:
        return False
    return secrets.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


async def require_admin(
    request: Request,
    user: User | None = Depends(get_current_user),
) -> User | None:
    """
    Dependency for operational endpoints (data syncs, full refreshes).

    Accepts either a logged-in superuser (cookie session; CSRFMiddleware
    still enforces the X-CSRF-Token header for it) or a script/cron caller
    presenting the ADMIN_API_TOKEN bearer token. Returns the User for
    cookie callers and None for token callers.
    """
    if _has_valid_admin_token(request):
        return None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return user


def is_admin_caller(request: Request, user: User | None) -> bool:
    """Non-raising variant of require_admin, for endpoints open to everyone
    that unlock extra scope (e.g. a full refresh) only for admins."""
    return _has_valid_admin_token(request) or bool(user and user.is_admin)
