from sqlalchemy import String, Float, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Station(Base):
    __tablename__ = "stations"

    # Primary key
    station_number: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Core identification
    station_name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    province: Mapped[str | None] = mapped_column(String(2), index=True)
    station_type: Mapped[str | None] = mapped_column(String(5), index=True)
    data_type: Mapped[str | None] = mapped_column(String(5))

    # Data source tracking
    data_source: Mapped[str | None] = mapped_column(String(20), index=True)

    # Grouping — used by provincial providers for regional organization
    basin_number: Mapped[str | None] = mapped_column(String(20), index=True)
    catchment_number: Mapped[str | None] = mapped_column(String(10), index=True)
    drainage_basin_prefix: Mapped[str | None] = mapped_column(String(5), index=True)

    # Federal fields (from ECCC)
    status: Mapped[str | None] = mapped_column(String(20))
    real_time: Mapped[bool | None] = mapped_column(Boolean)
    drainage_area_gross: Mapped[float | None] = mapped_column(Float)
    drainage_area_effect: Mapped[float | None] = mapped_column(Float)
    contributor: Mapped[str | None] = mapped_column(String(200))
    vertical_datum: Mapped[str | None] = mapped_column(String(50))
    rhbn: Mapped[bool | None] = mapped_column(Boolean)

    # Reservoir tracking
    has_capacity: Mapped[bool] = mapped_column(Boolean, default=False)

    # Data quality/staleness
    parameter_data_status: Mapped[str | None] = mapped_column(String(20))

    # Provider-specific metadata (TSIDs, dataset URLs, etc.)
    extra: Mapped[dict | None] = mapped_column(JSON)

    # Relationships
    current_readings: Mapped[list["CurrentReading"]] = relationship(
        back_populates="station", cascade="all, delete-orphan"
    )
    historical_daily_means: Mapped[list["HistoricalDailyMean"]] = relationship(
        back_populates="station", cascade="all, delete-orphan"
    )
    station_weather: Mapped["StationWeather"] = relationship(
        back_populates="station", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Station {self.station_number}: {self.station_name}>"
