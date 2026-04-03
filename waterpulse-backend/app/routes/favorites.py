from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.station import Station
from app.models.favorite import FavoriteStation
from app.auth import require_user
from app.schemas import FavoriteCreate, FavoriteResponse

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@router.get("/", response_model=list[FavoriteResponse])
async def list_favorites(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's favorite stations."""
    result = await db.execute(
        select(FavoriteStation, Station.station_name)
        .join(Station, FavoriteStation.station_number == Station.station_number)
        .where(FavoriteStation.user_id == user.id)
        .order_by(FavoriteStation.added_at.desc())
    )
    rows = result.all()
    return [
        FavoriteResponse(
            id=fav.id,
            station_number=fav.station_number,
            station_name=station_name,
            added_at=fav.added_at,
        )
        for fav, station_name in rows
    ]


@router.post("/", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    data: FavoriteCreate,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a station to the user's favorites."""
    # Verify station exists
    result = await db.execute(
        select(Station).where(Station.station_number == data.station_number)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    # Check for duplicate
    result = await db.execute(
        select(FavoriteStation).where(
            FavoriteStation.user_id == user.id,
            FavoriteStation.station_number == data.station_number,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Station already in favorites",
        )

    favorite = FavoriteStation(
        user_id=user.id,
        station_number=data.station_number,
    )
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    return FavoriteResponse(
        id=favorite.id,
        station_number=favorite.station_number,
        station_name=station.station_name,
        added_at=favorite.added_at,
    )


@router.delete("/{station_number}", status_code=204)
async def remove_favorite(
    station_number: str,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a station from the user's favorites."""
    result = await db.execute(
        select(FavoriteStation).where(
            FavoriteStation.user_id == user.id,
            FavoriteStation.station_number == station_number,
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    await db.delete(favorite)
    await db.commit()
