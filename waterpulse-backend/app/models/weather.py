from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class StationWeather(Base):
    __tablename__ = "station_weather"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("stations.station_number"),
        unique=True, index=True,
    )

    # Full weather payload: {current, daily_forecast, air_quality, elevation_m}
    weather_data: Mapped[dict | None] = mapped_column(JSON)

    # When this weather was last fetched from Open-Meteo (naive UTC)
    weather_fetched_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationship
    station: Mapped["Station"] = relationship(back_populates="station_weather")

    def __repr__(self) -> str:
        return f"<StationWeather {self.station_number} fetched={self.weather_fetched_at}>"
