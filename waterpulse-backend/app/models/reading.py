from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class CurrentReading(Base):
    __tablename__ = "current_readings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("stations.station_number"),
        unique=True, index=True,
    )

    # Timestamp of the reading in UTC (frontend converts to local)
    datetime_utc: Mapped[datetime | None] = mapped_column(DateTime)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Data source tracking
    data_source: Mapped[str | None] = mapped_column(String(20))

    # Core measurements (nullable since not all stations have all fields)
    water_level: Mapped[float | None] = mapped_column(Float)
    discharge: Mapped[float | None] = mapped_column(Float)

    # ECCC quality symbols
    level_symbol: Mapped[str | None] = mapped_column(String(50))
    discharge_symbol: Mapped[str | None] = mapped_column(String(50))

    # Reservoir measurements
    outflow: Mapped[float | None] = mapped_column(Float)
    capacity: Mapped[float | None] = mapped_column(Float)
    pct_full: Mapped[float | None] = mapped_column(Float)

    # Ratings
    flow_rating: Mapped[str | None] = mapped_column(String(20))
    level_rating: Mapped[str | None] = mapped_column(String(20))
    pct_full_rating: Mapped[str | None] = mapped_column(String(20))

    # Percentile data (stored as JSON)
    flow_percentiles: Mapped[dict | None] = mapped_column(JSON)
    level_percentiles: Mapped[dict | None] = mapped_column(JSON)

    # Provider-specific data (precipitation, units, etc.)
    extra: Mapped[dict | None] = mapped_column(JSON)

    # Relationship
    station: Mapped["Station"] = relationship(back_populates="current_readings")

    def __repr__(self) -> str:
        return (
            f"<CurrentReading {self.station_number} "
            f"at {self.datetime_utc}>"
        )
