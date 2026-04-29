"""
User-search route — backs the collaborator-invite autocomplete on the
collection edit page. Auth-required: usernames are not browseable to
anonymous visitors.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_user
from app.database import get_db
from app.models.user import User
from app.schemas import UserSearchResult

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/search", response_model=list[UserSearchResult])
async def search_users(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(8, ge=1, le=20),
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Username prefix-match for collaborator invite. Excludes the caller."""
    result = await db.execute(
        select(User)
        .where(User.username.ilike(f"{q}%"), User.id != user.id)
        .order_by(User.username)
        .limit(limit)
    )
    return list(result.scalars().all())
