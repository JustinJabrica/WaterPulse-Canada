"""add station_weather table

Revision ID: c4e7f2d93a10
Revises: b3f2c1a89d01
Create Date: 2026-04-01

Adds a station_weather table for caching per-station weather data
fetched on demand from Open-Meteo, replacing the bulk weather fetch
that previously ran during readings refresh.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4e7f2d93a10'
down_revision: Union[str, None] = 'b3f2c1a89d01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'station_weather',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('station_number', sa.String(length=20), nullable=False),
        sa.Column('weather_data', sa.JSON(), nullable=True),
        sa.Column('weather_fetched_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['station_number'], ['stations.station_number']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_number'),
    )
    op.create_index(
        op.f('ix_station_weather_station_number'),
        'station_weather',
        ['station_number'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_station_weather_station_number'),
        table_name='station_weather',
    )
    op.drop_table('station_weather')
