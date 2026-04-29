"""
Collections API routes.

A Collection is a named, user-owned grouping of stations with optional
view/edit collaborators, public/private visibility, an opaque view-only
share token, and tags. See the design plan for the full permission matrix.

Permission helpers (`is_owner`, `can_edit`, `can_administrate`, `can_delete`,
`can_view`, `compute_role`) are used by the routes below to enforce
access control. Routes that allow anonymous access use
`Depends(get_current_user)` (returns User | None); routes that require
auth use `Depends(require_user)`; superuser-only routes use
`Depends(require_superuser)`.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone


def _utcnow() -> datetime:
    """Naive UTC timestamp matching the rest of the project's convention
    (all DateTime columns store naive UTC — see CLAUDE.md)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, require_user, require_superuser
from app.database import get_db
from app.limiter import limiter
from app.models.collection import (
    Collection,
    CollectionStation,
    CollectionCollaborator,
    Tag,
    CollectionTag,
    FavouriteCollection,
)
from app.models.station import Station
from app.models.user import User
from app.schemas import (
    CollectionCreate,
    CollectionDetail,
    CollectionStationResponse,
    CollectionSummary,
    CollectionUpdate,
    CollaboratorCreate,
    CollaboratorResponse,
    CurrentReadingResponse,
    ShareTokenResponse,
    StationNumberList,
    TagSummary,
    ValuableUpdate,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


# Collection-loading helpers
# ─────────────────────────────────────────────────────────────────────


COLLECTION_EAGER_LOADS = (
    selectinload(Collection.owner),
    selectinload(Collection.stations)
    .selectinload(CollectionStation.station)
    .selectinload(Station.current_readings),
    selectinload(Collection.collaborators).selectinload(CollectionCollaborator.user),
    selectinload(Collection.tag_links).selectinload(CollectionTag.tag),
)


async def load_collection(db: AsyncSession, collection_id: int) -> Collection | None:
    """
    Load a collection with all relationships eager-loaded.

    Uses `populate_existing=True` so that re-loading after a write
    (e.g. add-stations followed by a fresh fetch for the response)
    overwrites the relationship lists on any cached instance instead of
    returning stale data.
    """
    result = await db.execute(
        select(Collection)
        .options(*COLLECTION_EAGER_LOADS)
        .where(Collection.id == collection_id)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def load_collection_or_404(db: AsyncSession, collection_id: int) -> Collection:
    collection = await load_collection(db, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


# Permission helpers
# ─────────────────────────────────────────────────────────────────────


def is_owner(collection: Collection, user: User | None) -> bool:
    return user is not None and collection.owner_user_id == user.id


def collaborator_record(
    collection: Collection, user: User | None
) -> CollectionCollaborator | None:
    if user is None:
        return None
    for c in collection.collaborators:
        if c.user_id == user.id:
            return c
    return None


def can_view(collection: Collection, user: User | None) -> bool:
    if collection.is_public:
        return True
    if user is None:
        return False
    if user.is_admin or is_owner(collection, user):
        return True
    return collaborator_record(collection, user) is not None


def can_edit(collection: Collection, user: User | None) -> bool:
    if user is None:
        return False
    if user.is_admin or is_owner(collection, user):
        return True
    record = collaborator_record(collection, user)
    return record is not None and record.permission == "edit"


def can_administrate(collection: Collection, user: User | None) -> bool:
    """Owner-only actions: invite collaborators, toggle is_public, rotate share token."""
    if user is None:
        return False
    return user.is_admin or is_owner(collection, user)


def can_delete(collection: Collection, user: User | None) -> bool:
    if user is None:
        return False
    if user.is_admin:
        return True
    if collection.is_valuable:
        return False
    return is_owner(collection, user)


def compute_role(collection: Collection, user: User | None) -> str | None:
    if user is None:
        return None
    if user.is_admin:
        return "superuser"
    if is_owner(collection, user):
        return "owner"
    record = collaborator_record(collection, user)
    if record is None:
        return None
    return "editor" if record.permission == "edit" else "viewer"


# Tag helpers
# ─────────────────────────────────────────────────────────────────────


def normalise_tag(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="Tag name cannot be empty")
    if len(cleaned) > 20:
        raise HTTPException(
            status_code=422,
            detail=f"Tag '{cleaned}' exceeds 20 characters",
        )
    return cleaned


async def upsert_tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    """Get-or-create tags by case-insensitive name (CITEXT)."""
    cleaned = [normalise_tag(n) for n in names]
    if not cleaned:
        return []
    if len(cleaned) > 10:
        raise HTTPException(status_code=422, detail="Maximum 10 tags per collection")

    # CITEXT uniqueness handles case-insensitive matching naturally.
    existing_result = await db.execute(select(Tag).where(Tag.name.in_(cleaned)))
    existing = {tag.name.lower(): tag for tag in existing_result.scalars().all()}
    tags: list[Tag] = []
    for name in cleaned:
        key = name.lower()
        if key in existing:
            tags.append(existing[key])
            continue
        new_tag = Tag(name=name)
        db.add(new_tag)
        await db.flush()
        existing[key] = new_tag
        tags.append(new_tag)
    return tags


# Serialisation helpers
# ─────────────────────────────────────────────────────────────────────


def to_collection_summary(
    collection: Collection,
    user: User | None,
    favourite_ids: set[int],
) -> CollectionSummary:
    return CollectionSummary(
        id=collection.id,
        owner_user_id=collection.owner_user_id,
        owner_username=collection.owner.username,
        name=collection.name,
        description=collection.description,
        is_public=collection.is_public,
        is_valuable=collection.is_valuable,
        station_count=len(collection.stations),
        tags=[TagSummary(id=link.tag.id, name=link.tag.name) for link in collection.tag_links],
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        role=compute_role(collection, user),
        is_favourited=collection.id in favourite_ids,
    )


def _serialize_collection_station(cs: CollectionStation) -> CollectionStationResponse:
    """Flatten a CollectionStation + its Station + its CurrentReading row."""
    station = cs.station
    reading = (
        station.current_readings[0]
        if station and station.current_readings
        else None
    )
    return CollectionStationResponse(
        station_number=cs.station_number,
        station_name=station.station_name if station else None,
        province=station.province if station else None,
        station_type=station.station_type if station else None,
        latitude=station.latitude if station else None,
        longitude=station.longitude if station else None,
        latest_reading=(
            CurrentReadingResponse.model_validate(reading) if reading else None
        ),
        added_at=cs.added_at,
    )


def to_collection_detail(
    collection: Collection,
    user: User | None,
    favourite_ids: set[int],
) -> CollectionDetail:
    summary = to_collection_summary(collection, user, favourite_ids)
    show_token = is_owner(collection, user) or (user is not None and user.is_admin)
    return CollectionDetail(
        **summary.model_dump(),
        stations=[
            _serialize_collection_station(cs) for cs in collection.stations
        ],
        collaborators=[
            CollaboratorResponse(
                user_id=c.user_id,
                username=c.user.username,
                permission=c.permission,
                added_at=c.added_at,
            )
            for c in collection.collaborators
        ],
        share_token=collection.share_token if show_token else None,
    )


async def fetch_favourite_ids(db: AsyncSession, user: User | None) -> set[int]:
    if user is None:
        return set()
    result = await db.execute(
        select(FavouriteCollection.collection_id).where(
            FavouriteCollection.user_id == user.id
        )
    )
    return {row[0] for row in result.all()}


# Routes
# ─────────────────────────────────────────────────────────────────────


@router.get("/", response_model=list[CollectionSummary])
async def list_my_collections(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Collections the current user owns, collaborates on, or has favourited."""
    owned_ids = select(Collection.id).where(Collection.owner_user_id == user.id)
    collaborated_ids = select(CollectionCollaborator.collection_id).where(
        CollectionCollaborator.user_id == user.id
    )
    favourited_ids = select(FavouriteCollection.collection_id).where(
        FavouriteCollection.user_id == user.id
    )
    visible = owned_ids.union(collaborated_ids, favourited_ids).subquery()

    result = await db.execute(
        select(Collection)
        .options(*COLLECTION_EAGER_LOADS)
        .where(Collection.id.in_(select(visible.c.id)))
        .order_by(Collection.updated_at.desc())
    )
    collections = result.scalars().unique().all()
    favourite_ids = await fetch_favourite_ids(db, user)
    return [to_collection_summary(c, user, favourite_ids) for c in collections]


@router.get("/discover", response_model=list[CollectionSummary])
async def discover_collections(
    province: str | None = Query(None, description="Filter to collections containing at least one station in this province"),
    tag: str | None = Query(None, description="Filter to collections carrying this tag (case-insensitive)"),
    q: str | None = Query(None, description="Substring match against collection name"),
    featured: bool = Query(False, description="Only return is_valuable=true collections"),
    limit: int = Query(50, ge=1, le=200),
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Public collection browse — anonymous-friendly."""
    stmt = (
        select(Collection)
        .options(*COLLECTION_EAGER_LOADS)
        .where(Collection.is_public.is_(True))
    )

    if province:
        province_subq = (
            select(CollectionStation.collection_id)
            .join(Station, Station.station_number == CollectionStation.station_number)
            .where(Station.province == province)
            .distinct()
        )
        stmt = stmt.where(Collection.id.in_(province_subq))

    if tag:
        tag_subq = (
            select(CollectionTag.collection_id)
            .join(Tag, Tag.id == CollectionTag.tag_id)
            .where(Tag.name == tag)
        )
        stmt = stmt.where(Collection.id.in_(tag_subq))

    if q:
        stmt = stmt.where(Collection.name.ilike(f"%{q}%"))

    if featured:
        stmt = stmt.where(Collection.is_valuable.is_(True))

    # Featured first when the caller didn't restrict to featured, then newest.
    stmt = stmt.order_by(
        Collection.is_valuable.desc(),
        Collection.updated_at.desc(),
    ).limit(limit)

    result = await db.execute(stmt)
    collections = result.scalars().unique().all()
    favourite_ids = await fetch_favourite_ids(db, user)
    return [to_collection_summary(c, user, favourite_ids) for c in collections]


@router.get("/share/{token}", response_model=CollectionDetail)
@limiter.limit("30/hour")
async def read_via_share_token(
    request: Request,
    token: str,
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read a collection via its share token. Anonymous-friendly; rate-limited."""
    result = await db.execute(
        select(Collection)
        .options(*COLLECTION_EAGER_LOADS)
        .where(Collection.share_token == token)
    )
    collection = result.scalar_one_or_none()
    if collection is None:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")
    favourite_ids = await fetch_favourite_ids(db, user)
    return to_collection_detail(collection, user, favourite_ids)


@router.post("/", response_model=CollectionDetail, status_code=201)
async def create_collection(
    data: CollectionCreate,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new collection."""
    # Per-user name uniqueness
    existing = await db.execute(
        select(Collection).where(
            Collection.owner_user_id == user.id, Collection.name == data.name
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a collection called {data.name!r}",
        )

    collection = Collection(
        owner_user_id=user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public,
    )
    db.add(collection)
    await db.flush()

    # Tags
    if data.tags:
        tags = await upsert_tags(db, data.tags)
        for tag in tags:
            db.add(CollectionTag(collection_id=collection.id, tag_id=tag.id))

    # Initial stations
    if data.station_numbers:
        await _add_stations(db, collection, data.station_numbers)

    await db.commit()
    fresh = await load_collection_or_404(db, collection.id)
    return to_collection_detail(fresh, user, set())


@router.get("/{collection_id}", response_model=CollectionDetail)
async def read_collection(
    collection_id: int,
    user: User | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Read a collection by id. Public collections allow anonymous access."""
    collection = await load_collection_or_404(db, collection_id)
    if not can_view(collection, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN
            if user is not None
            else status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this collection",
        )
    favourite_ids = await fetch_favourite_ids(db, user)
    return to_collection_detail(collection, user, favourite_ids)


@router.patch("/{collection_id}", response_model=CollectionDetail)
async def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit name, description, tags, or is_public (owner only for is_public)."""
    collection = await load_collection_or_404(db, collection_id)
    if not can_edit(collection, user):
        raise HTTPException(status_code=403, detail="Edit permission required")

    if data.name is not None and data.name != collection.name:
        # Uniqueness within owner
        clash = await db.execute(
            select(Collection).where(
                Collection.owner_user_id == collection.owner_user_id,
                Collection.name == data.name,
                Collection.id != collection.id,
            )
        )
        if clash.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Owner already has a collection called {data.name!r}",
            )
        collection.name = data.name

    if data.description is not None:
        collection.description = data.description

    if data.is_public is not None:
        if not can_administrate(collection, user):
            raise HTTPException(
                status_code=403, detail="Only the owner can change visibility"
            )
        collection.is_public = data.is_public

    if data.tags is not None:
        await db.execute(
            delete(CollectionTag).where(CollectionTag.collection_id == collection.id)
        )
        if data.tags:
            tags = await upsert_tags(db, data.tags)
            for tag in tags:
                db.add(CollectionTag(collection_id=collection.id, tag_id=tag.id))

    collection.updated_at = _utcnow()
    await db.commit()
    fresh = await load_collection_or_404(db, collection.id)
    favourite_ids = await fetch_favourite_ids(db, user)
    return to_collection_detail(fresh, user, favourite_ids)


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a collection. is_valuable collections are superuser-only."""
    collection = await load_collection_or_404(db, collection_id)
    if not can_delete(collection, user):
        raise HTTPException(status_code=403, detail="Cannot delete this collection")
    await db.delete(collection)
    await db.commit()


# Stations sub-resource
# ─────────────────────────────────────────────────────────────────────


async def _add_stations(
    db: AsyncSession, collection: Collection, station_numbers: list[str]
) -> None:
    if not station_numbers:
        return
    # Validate stations exist
    found = await db.execute(
        select(Station.station_number).where(Station.station_number.in_(station_numbers))
    )
    found_set = {row[0] for row in found.all()}
    missing = [n for n in station_numbers if n not in found_set]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown stations: {', '.join(sorted(missing))}",
        )
    existing = await db.execute(
        select(CollectionStation.station_number).where(
            CollectionStation.collection_id == collection.id,
            CollectionStation.station_number.in_(station_numbers),
        )
    )
    already = {row[0] for row in existing.all()}
    for number in station_numbers:
        if number in already:
            continue
        db.add(
            CollectionStation(
                collection_id=collection.id, station_number=number
            )
        )


@router.post("/{collection_id}/stations", response_model=CollectionDetail)
async def add_stations(
    collection_id: int,
    data: StationNumberList,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_edit(collection, user):
        raise HTTPException(status_code=403, detail="Edit permission required")
    await _add_stations(db, collection, data.station_numbers)
    collection.updated_at = _utcnow()
    await db.commit()
    fresh = await load_collection_or_404(db, collection.id)
    favourite_ids = await fetch_favourite_ids(db, user)
    return to_collection_detail(fresh, user, favourite_ids)


@router.delete("/{collection_id}/stations/{station_number}", status_code=204)
async def remove_station(
    collection_id: int,
    station_number: str,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_edit(collection, user):
        raise HTTPException(status_code=403, detail="Edit permission required")
    result = await db.execute(
        select(CollectionStation).where(
            CollectionStation.collection_id == collection.id,
            CollectionStation.station_number == station_number,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Station not in collection")
    await db.delete(link)
    collection.updated_at = _utcnow()
    await db.commit()


# Favouriting
# ─────────────────────────────────────────────────────────────────────


@router.post("/{collection_id}/favourite", status_code=201)
async def favourite_collection(
    collection_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_view(collection, user):
        raise HTTPException(
            status_code=403, detail="Cannot favourite a collection you cannot view"
        )
    existing = await db.execute(
        select(FavouriteCollection).where(
            FavouriteCollection.user_id == user.id,
            FavouriteCollection.collection_id == collection_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return {"status": "already_favourited"}
    db.add(
        FavouriteCollection(user_id=user.id, collection_id=collection_id)
    )
    await db.commit()
    return {"status": "favourited"}


@router.delete("/{collection_id}/favourite", status_code=204)
async def unfavourite_collection(
    collection_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FavouriteCollection).where(
            FavouriteCollection.user_id == user.id,
            FavouriteCollection.collection_id == collection_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="Not in your favourites")
    await db.delete(link)
    await db.commit()


# Collaborators
# ─────────────────────────────────────────────────────────────────────


@router.post(
    "/{collection_id}/collaborators",
    response_model=CollaboratorResponse,
    status_code=201,
)
async def invite_collaborator(
    collection_id: int,
    data: CollaboratorCreate,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_administrate(collection, user):
        raise HTTPException(
            status_code=403, detail="Only the owner can invite collaborators"
        )
    if data.permission not in ("view", "edit"):
        raise HTTPException(
            status_code=422, detail="permission must be 'view' or 'edit'"
        )

    invited_result = await db.execute(
        select(User).where(User.username == data.username)
    )
    invited = invited_result.scalar_one_or_none()
    if invited is None:
        raise HTTPException(status_code=404, detail="User not found")
    if invited.id == collection.owner_user_id:
        raise HTTPException(
            status_code=400, detail="Owner is already on the collection"
        )

    existing_result = await db.execute(
        select(CollectionCollaborator).where(
            CollectionCollaborator.collection_id == collection.id,
            CollectionCollaborator.user_id == invited.id,
        )
    )
    record = existing_result.scalar_one_or_none()
    if record is not None:
        record.permission = data.permission
    else:
        record = CollectionCollaborator(
            collection_id=collection.id,
            user_id=invited.id,
            permission=data.permission,
        )
        db.add(record)
    await db.commit()
    await db.refresh(record)
    return CollaboratorResponse(
        user_id=invited.id,
        username=invited.username,
        permission=record.permission,
        added_at=record.added_at,
    )


@router.delete(
    "/{collection_id}/collaborators/{user_id}", status_code=204
)
async def remove_collaborator(
    collection_id: int,
    user_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_administrate(collection, user):
        raise HTTPException(
            status_code=403, detail="Only the owner can remove collaborators"
        )
    result = await db.execute(
        select(CollectionCollaborator).where(
            CollectionCollaborator.collection_id == collection.id,
            CollectionCollaborator.user_id == user_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    await db.delete(record)
    await db.commit()


# Share token
# ─────────────────────────────────────────────────────────────────────


@router.post("/{collection_id}/share-token", response_model=ShareTokenResponse)
async def regenerate_share_token(
    collection_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_administrate(collection, user):
        raise HTTPException(
            status_code=403, detail="Only the owner can manage share tokens"
        )
    collection.share_token = secrets.token_urlsafe(32)
    await db.commit()
    return ShareTokenResponse(share_token=collection.share_token)


@router.delete("/{collection_id}/share-token", status_code=204)
async def clear_share_token(
    collection_id: int,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    if not can_administrate(collection, user):
        raise HTTPException(
            status_code=403, detail="Only the owner can manage share tokens"
        )
    collection.share_token = None
    await db.commit()


# Valuable toggle (superuser only)
# ─────────────────────────────────────────────────────────────────────


@router.patch("/{collection_id}/valuable", response_model=CollectionDetail)
async def toggle_valuable(
    collection_id: int,
    data: ValuableUpdate,
    user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db),
):
    collection = await load_collection_or_404(db, collection_id)
    collection.is_valuable = data.is_valuable
    collection.updated_at = _utcnow()
    await db.commit()
    fresh = await load_collection_or_404(db, collection.id)
    favourite_ids = await fetch_favourite_ids(db, user)
    return to_collection_detail(fresh, user, favourite_ids)
