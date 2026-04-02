from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class FavoriteStation(Base):
    __tablename__ = "favorite_stations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True
    )
    station_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("stations.station_number"), index=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Prevent duplicate favorites
    __table_args__ = (
        UniqueConstraint("user_id", "station_number", name="uq_user_station"),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="favorites")
    station: Mapped["Station"] = relationship(back_populates="favorited_by")

    def __repr__(self) -> str:
        return f"<Favorite user={self.user_id} station={self.station_number}>"
