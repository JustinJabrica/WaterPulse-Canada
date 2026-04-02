from sqlalchemy import String, Float, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class HistoricalDailyMean(Base):
    __tablename__ = "historical_daily_means"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("stations.station_number"), index=True
    )

    # "flow" or "level"
    data_key: Mapped[str] = mapped_column(String(10), index=True)

    # Calendar date as MM-DD (e.g., "03-19")
    month_day: Mapped[str] = mapped_column(String(5), index=True)

    # Which year this daily mean comes from
    year: Mapped[int] = mapped_column(Integer)

    # The computed daily mean value
    value: Mapped[float] = mapped_column(Float)

    # Data source tracking
    data_source: Mapped[str | None] = mapped_column(String(20))

    # How many years contributed to this mean (for confidence assessment)
    year_count: Mapped[int | None] = mapped_column(Integer)

    # Prevent duplicate entries for the same station/key/date/year
    __table_args__ = (
        UniqueConstraint(
            "station_number", "data_key", "month_day", "year",
            name="uq_station_key_date_year",
        ),
    )

    # Relationship
    station: Mapped["Station"] = relationship(back_populates="historical_daily_means")

    def __repr__(self) -> str:
        return (
            f"<HistoricalDailyMean {self.station_number} "
            f"{self.data_key} {self.month_day} ({self.year}): {self.value}>"
        )
