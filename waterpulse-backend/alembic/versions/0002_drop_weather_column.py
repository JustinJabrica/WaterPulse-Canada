"""drop deprecated weather column from current_readings

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-03

Weather data is now stored in the separate station_weather table
(fetched on demand via Open-Meteo). The JSON weather column on
current_readings was never populated after the migration to the
new table and is safe to remove.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("current_readings", "weather")


def downgrade() -> None:
    op.add_column(
        "current_readings",
        sa.Column("weather", sa.JSON(), nullable=True),
    )
