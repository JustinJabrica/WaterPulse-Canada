"""unique_station_number_on_readings

Revision ID: b3f2c1a89d01
Revises: 8a0a5bb54c54
Create Date: 2026-04-01

Adds a unique constraint on current_readings.station_number so the
readings table can use upserts instead of delete-all + re-insert.
Removes duplicate rows (keeping the latest) before adding the constraint.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f2c1a89d01'
down_revision: Union[str, None] = '8a0a5bb54c54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove duplicate station_number rows, keeping only the most recent
    op.execute("""
        DELETE FROM current_readings
        WHERE id NOT IN (
            SELECT DISTINCT ON (station_number) id
            FROM current_readings
            ORDER BY station_number, fetched_at DESC
        )
    """)

    # Add unique constraint
    op.create_unique_constraint(
        'uq_current_readings_station_number',
        'current_readings',
        ['station_number'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_current_readings_station_number',
        'current_readings',
        type_='unique',
    )
