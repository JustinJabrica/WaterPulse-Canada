"""initial schema — create all tables from scratch

Revision ID: 0001
Revises: (none — this is the first migration)
Create Date: 2026-04-02

Creates all 6 tables for a fresh WaterPulse database:
  stations, current_readings, historical_daily_means,
  station_weather, users, favorite_stations.

This replaces the earlier incremental migrations that assumed tables
already existed from local development. Docker starts with an empty
database, so we need CREATE TABLE, not ALTER TABLE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── stations ────────────────────────────────────────────────────
    op.create_table(
        'stations',
        sa.Column('station_number', sa.String(20), nullable=False),
        sa.Column('station_name', sa.String(200), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('province', sa.String(2), nullable=True),
        sa.Column('station_type', sa.String(5), nullable=True),
        sa.Column('data_type', sa.String(5), nullable=True),
        sa.Column('data_source', sa.String(20), nullable=True),
        sa.Column('basin_number', sa.String(20), nullable=True),
        sa.Column('catchment_number', sa.String(10), nullable=True),
        sa.Column('drainage_basin_prefix', sa.String(5), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('real_time', sa.Boolean(), nullable=True),
        sa.Column('drainage_area_gross', sa.Float(), nullable=True),
        sa.Column('drainage_area_effect', sa.Float(), nullable=True),
        sa.Column('contributor', sa.String(200), nullable=True),
        sa.Column('vertical_datum', sa.String(50), nullable=True),
        sa.Column('rhbn', sa.Boolean(), nullable=True),
        sa.Column('has_capacity', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('parameter_data_status', sa.String(20), nullable=True),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('station_number'),
    )
    op.create_index('ix_stations_province', 'stations', ['province'])
    op.create_index('ix_stations_station_type', 'stations', ['station_type'])
    op.create_index('ix_stations_data_source', 'stations', ['data_source'])
    op.create_index('ix_stations_basin_number', 'stations', ['basin_number'])
    op.create_index('ix_stations_catchment_number', 'stations', ['catchment_number'])
    op.create_index('ix_stations_drainage_basin_prefix', 'stations', ['drainage_basin_prefix'])

    # ── current_readings ────────────────────────────────────────────
    op.create_table(
        'current_readings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('station_number', sa.String(20), nullable=False),
        sa.Column('datetime_utc', sa.DateTime(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('data_source', sa.String(20), nullable=True),
        sa.Column('water_level', sa.Float(), nullable=True),
        sa.Column('discharge', sa.Float(), nullable=True),
        sa.Column('level_symbol', sa.String(50), nullable=True),
        sa.Column('discharge_symbol', sa.String(50), nullable=True),
        sa.Column('outflow', sa.Float(), nullable=True),
        sa.Column('capacity', sa.Float(), nullable=True),
        sa.Column('pct_full', sa.Float(), nullable=True),
        sa.Column('flow_rating', sa.String(20), nullable=True),
        sa.Column('level_rating', sa.String(20), nullable=True),
        sa.Column('pct_full_rating', sa.String(20), nullable=True),
        sa.Column('flow_percentiles', sa.JSON(), nullable=True),
        sa.Column('level_percentiles', sa.JSON(), nullable=True),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['station_number'], ['stations.station_number']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_number', name='uq_current_readings_station_number'),
    )
    op.create_index('ix_current_readings_station_number', 'current_readings', ['station_number'], unique=True)

    # ── historical_daily_means ──────────────────────────────────────
    op.create_table(
        'historical_daily_means',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('station_number', sa.String(20), nullable=False),
        sa.Column('data_key', sa.String(10), nullable=False),
        sa.Column('month_day', sa.String(5), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('data_source', sa.String(20), nullable=True),
        sa.Column('year_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['station_number'], ['stations.station_number']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_number', 'data_key', 'month_day', 'year', name='uq_station_key_date_year'),
    )
    op.create_index('ix_historical_daily_means_station_number', 'historical_daily_means', ['station_number'])
    op.create_index('ix_historical_daily_means_data_key', 'historical_daily_means', ['data_key'])
    op.create_index('ix_historical_daily_means_month_day', 'historical_daily_means', ['month_day'])

    # ── station_weather ─────────────────────────────────────────────
    op.create_table(
        'station_weather',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('station_number', sa.String(20), nullable=False),
        sa.Column('weather_data', sa.JSON(), nullable=True),
        sa.Column('weather_fetched_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['station_number'], ['stations.station_number']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('station_number'),
    )
    op.create_index('ix_station_weather_station_number', 'station_weather', ['station_number'], unique=True)

    # ── users ───────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # ── favorite_stations ───────────────────────────────────────────
    op.create_table(
        'favorite_stations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('station_number', sa.String(20), nullable=False),
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['station_number'], ['stations.station_number']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'station_number', name='uq_user_station'),
    )
    op.create_index('ix_favorite_stations_user_id', 'favorite_stations', ['user_id'])
    op.create_index('ix_favorite_stations_station_number', 'favorite_stations', ['station_number'])


def downgrade() -> None:
    op.drop_table('favorite_stations')
    op.drop_table('users')
    op.drop_table('station_weather')
    op.drop_table('historical_daily_means')
    op.drop_table('current_readings')
    op.drop_table('stations')
