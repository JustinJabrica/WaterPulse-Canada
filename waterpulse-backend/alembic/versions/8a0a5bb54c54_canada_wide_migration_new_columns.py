"""canada_wide_migration_new_columns

Revision ID: 8a0a5bb54c54
Revises:
Create Date: 2026-04-01 02:49:36.726888

Adds new columns for Canada-wide multi-provider architecture.
Migrates existing data from old column names to new ones before
dropping the old columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8a0a5bb54c54'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── STATIONS TABLE ──────────────────────────────────────────────

    # Add new columns
    op.add_column('stations', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('stations', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('stations', sa.Column('province', sa.String(length=2), nullable=True))
    op.add_column('stations', sa.Column('data_source', sa.String(length=20), nullable=True))
    op.add_column('stations', sa.Column('drainage_basin_prefix', sa.String(length=5), nullable=True))
    op.add_column('stations', sa.Column('status', sa.String(length=20), nullable=True))
    op.add_column('stations', sa.Column('real_time', sa.Boolean(), nullable=True))
    op.add_column('stations', sa.Column('drainage_area_gross', sa.Float(), nullable=True))
    op.add_column('stations', sa.Column('drainage_area_effect', sa.Float(), nullable=True))
    op.add_column('stations', sa.Column('contributor', sa.String(length=200), nullable=True))
    op.add_column('stations', sa.Column('vertical_datum', sa.String(length=50), nullable=True))
    op.add_column('stations', sa.Column('rhbn', sa.Boolean(), nullable=True))
    op.add_column('stations', sa.Column('extra', sa.JSON(), nullable=True))

    # Copy data from old columns to new columns
    op.execute("UPDATE stations SET latitude = station_latitude")
    op.execute("UPDATE stations SET longitude = station_longitude")
    op.execute("UPDATE stations SET province = 'AB'")
    op.execute("UPDATE stations SET data_source = 'alberta'")
    op.execute(
        "UPDATE stations SET drainage_basin_prefix = LEFT(station_number, 2) "
        "WHERE LENGTH(station_number) >= 2"
    )

    # Migrate Alberta-internal fields into the extra JSON column
    op.execute("""
        UPDATE stations SET extra = jsonb_build_object(
            'tsid', tsid,
            'pct25', pct25,
            'pct75', pct75,
            'secriver', secriver,
            'liveStorage', live_storage,
            'pctFull', pct_full,
            'ptValueLast6h', pt_value_last_6h,
            'ptValueLast12h', pt_value_last_12h,
            'ptValueLast24h', pt_value_last_24h,
            'ptValueLast48h', pt_value_last_48h,
            'wmo_reports', wmo_reports,
            'datasets', datasets
        )
    """)

    # Make station_type and data_type nullable (ECCC-only stations may lack these)
    op.alter_column('stations', 'station_type',
                    existing_type=sa.VARCHAR(length=5), nullable=True)
    op.alter_column('stations', 'data_type',
                    existing_type=sa.VARCHAR(length=5), nullable=True)

    # Create new indexes
    op.create_index(op.f('ix_stations_data_source'), 'stations', ['data_source'], unique=False)
    op.create_index(op.f('ix_stations_drainage_basin_prefix'), 'stations', ['drainage_basin_prefix'], unique=False)
    op.create_index(op.f('ix_stations_province'), 'stations', ['province'], unique=False)

    # Drop old columns
    op.drop_column('stations', 'station_latitude')
    op.drop_column('stations', 'station_longitude')
    op.drop_column('stations', 'tsid')
    op.drop_column('stations', 'pct25')
    op.drop_column('stations', 'pct75')
    op.drop_column('stations', 'secriver')
    op.drop_column('stations', 'live_storage')
    op.drop_column('stations', 'pct_full')
    op.drop_column('stations', 'pt_value_last_6h')
    op.drop_column('stations', 'pt_value_last_12h')
    op.drop_column('stations', 'pt_value_last_24h')
    op.drop_column('stations', 'pt_value_last_48h')
    op.drop_column('stations', 'wmo_reports')
    op.drop_column('stations', 'datasets')

    # ── CURRENT_READINGS TABLE ──────────────────────────────────────

    # Add new columns
    op.add_column('current_readings', sa.Column('datetime_utc', sa.DateTime(), nullable=True))
    op.add_column('current_readings', sa.Column('data_source', sa.String(length=20), nullable=True))
    op.add_column('current_readings', sa.Column('water_level', sa.Float(), nullable=True))
    op.add_column('current_readings', sa.Column('discharge', sa.Float(), nullable=True))
    op.add_column('current_readings', sa.Column('level_symbol', sa.String(length=50), nullable=True))
    op.add_column('current_readings', sa.Column('discharge_symbol', sa.String(length=50), nullable=True))
    op.add_column('current_readings', sa.Column('extra', sa.JSON(), nullable=True))

    # Copy data from old columns to new columns
    op.execute("UPDATE current_readings SET datetime_utc = reading_timestamp")
    op.execute("UPDATE current_readings SET water_level = level")
    op.execute("UPDATE current_readings SET discharge = flow")
    op.execute("UPDATE current_readings SET data_source = 'alberta'")

    # Migrate unit info into extra JSON
    op.execute("""
        UPDATE current_readings SET extra = jsonb_build_object(
            'level_unit', level_unit,
            'flow_unit', flow_unit,
            'outflow_unit', outflow_unit,
            'capacity_unit', capacity_unit,
            'pct_full_unit', pct_full_unit
        )
    """)

    # Drop old columns
    op.drop_column('current_readings', 'reading_timestamp')
    op.drop_column('current_readings', 'level')
    op.drop_column('current_readings', 'flow')
    op.drop_column('current_readings', 'level_unit')
    op.drop_column('current_readings', 'flow_unit')
    op.drop_column('current_readings', 'outflow_unit')
    op.drop_column('current_readings', 'capacity_unit')
    op.drop_column('current_readings', 'pct_full_unit')

    # ── HISTORICAL_DAILY_MEANS TABLE ────────────────────────────────

    op.add_column('historical_daily_means', sa.Column('data_source', sa.String(length=20), nullable=True))
    op.add_column('historical_daily_means', sa.Column('year_count', sa.Integer(), nullable=True))

    # Existing historical data is from Alberta
    op.execute("UPDATE historical_daily_means SET data_source = 'alberta'")


def downgrade() -> None:
    # ── HISTORICAL_DAILY_MEANS TABLE ────────────────────────────────
    op.drop_column('historical_daily_means', 'year_count')
    op.drop_column('historical_daily_means', 'data_source')

    # ── CURRENT_READINGS TABLE ──────────────────────────────────────
    op.add_column('current_readings', sa.Column('capacity_unit', sa.VARCHAR(length=10), nullable=True))
    op.add_column('current_readings', sa.Column('pct_full_unit', sa.VARCHAR(length=10), nullable=True))
    op.add_column('current_readings', sa.Column('flow_unit', sa.VARCHAR(length=10), nullable=True))
    op.add_column('current_readings', sa.Column('outflow_unit', sa.VARCHAR(length=10), nullable=True))
    op.add_column('current_readings', sa.Column('level', sa.DOUBLE_PRECISION(precision=53), nullable=True))
    op.add_column('current_readings', sa.Column('reading_timestamp', postgresql.TIMESTAMP(), nullable=True))
    op.add_column('current_readings', sa.Column('flow', sa.DOUBLE_PRECISION(precision=53), nullable=True))
    op.add_column('current_readings', sa.Column('level_unit', sa.VARCHAR(length=10), nullable=True))

    # Restore data from new columns
    op.execute("UPDATE current_readings SET reading_timestamp = datetime_utc")
    op.execute("UPDATE current_readings SET level = water_level")
    op.execute("UPDATE current_readings SET flow = discharge")

    op.drop_column('current_readings', 'extra')
    op.drop_column('current_readings', 'discharge_symbol')
    op.drop_column('current_readings', 'level_symbol')
    op.drop_column('current_readings', 'discharge')
    op.drop_column('current_readings', 'water_level')
    op.drop_column('current_readings', 'data_source')
    op.drop_column('current_readings', 'datetime_utc')

    # ── STATIONS TABLE ──────────────────────────────────────────────
    op.add_column('stations', sa.Column('station_latitude', sa.DOUBLE_PRECISION(precision=53), nullable=True))
    op.add_column('stations', sa.Column('station_longitude', sa.DOUBLE_PRECISION(precision=53), nullable=True))
    op.add_column('stations', sa.Column('tsid', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pct25', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pct75', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('secriver', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('live_storage', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pct_full', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pt_value_last_6h', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pt_value_last_12h', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pt_value_last_24h', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('pt_value_last_48h', sa.VARCHAR(length=20), nullable=True))
    op.add_column('stations', sa.Column('wmo_reports', sa.BOOLEAN(), nullable=False, server_default='false'))
    op.add_column('stations', sa.Column('datasets', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # Restore data from new columns
    op.execute("UPDATE stations SET station_latitude = latitude")
    op.execute("UPDATE stations SET station_longitude = longitude")

    op.drop_index(op.f('ix_stations_province'), table_name='stations')
    op.drop_index(op.f('ix_stations_drainage_basin_prefix'), table_name='stations')
    op.drop_index(op.f('ix_stations_data_source'), table_name='stations')
    op.alter_column('stations', 'data_type',
                    existing_type=sa.VARCHAR(length=5), nullable=False)
    op.alter_column('stations', 'station_type',
                    existing_type=sa.VARCHAR(length=5), nullable=False)
    op.drop_column('stations', 'extra')
    op.drop_column('stations', 'rhbn')
    op.drop_column('stations', 'vertical_datum')
    op.drop_column('stations', 'contributor')
    op.drop_column('stations', 'drainage_area_effect')
    op.drop_column('stations', 'drainage_area_gross')
    op.drop_column('stations', 'real_time')
    op.drop_column('stations', 'status')
    op.drop_column('stations', 'drainage_basin_prefix')
    op.drop_column('stations', 'data_source')
    op.drop_column('stations', 'province')
    op.drop_column('stations', 'longitude')
    op.drop_column('stations', 'latitude')
