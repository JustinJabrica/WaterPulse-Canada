"""
Tag autocomplete and popular-tag listing — backs the tag input on the
collection editor and the discovery page tag filter.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.collection import (
    Collection,
    CollectionTag,
    Tag,
)
from app.schemas import TagSummary, TagWithCount

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagSummary])
async def autocomplete_tags(
    q: str = Query(..., min_length=1, max_length=20),
    limit: int = Query(8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Prefix match against tag names (case-insensitive via CITEXT)."""
    result = await db.execute(
        select(Tag).where(Tag.name.ilike(f"{q}%")).order_by(Tag.name).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/popular", response_model=list[TagWithCount])
async def popular_tags(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Most-used tags across public collections — for the discovery surface."""
    count_col = func.count(CollectionTag.collection_id).label("collection_count")
    result = await db.execute(
        select(Tag.id, Tag.name, count_col)
        .join(CollectionTag, CollectionTag.tag_id == Tag.id)
        .join(Collection, Collection.id == CollectionTag.collection_id)
        .where(Collection.is_public.is_(True))
        .group_by(Tag.id, Tag.name)
        .order_by(count_col.desc())
        .limit(limit)
    )
    return [
        TagWithCount(id=row.id, name=row.name, collection_count=row.collection_count)
        for row in result.all()
    ]
