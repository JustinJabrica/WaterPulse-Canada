"""collections feature — replace favorite_stations with collections, tags, and friends

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-28

Schema changes:
  - Adds users.is_admin (bool, default false) for the new require_superuser dependency.
  - Enables CITEXT extension (used by tags.name for case-insensitive uniqueness).
  - Creates collections, collection_stations, collection_collaborators, tags,
    collection_tags, favourite_collections.
  - Drops favorite_stations (the old per-station star concept; replaced by
    "add station to a collection" + "favourite a collection").
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── extension ───────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ── users.is_admin ──────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # ── collections ─────────────────────────────────────────────────
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_valuable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("share_token", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token", name="uq_collections_share_token"),
        sa.UniqueConstraint(
            "owner_user_id", "name", name="uq_collection_owner_name"
        ),
    )
    op.create_index(
        "ix_collections_owner_user_id", "collections", ["owner_user_id"]
    )

    # ── collection_stations ─────────────────────────────────────────
    op.create_table(
        "collection_stations",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("station_number", sa.String(20), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["station_number"], ["stations.station_number"]),
        sa.PrimaryKeyConstraint("collection_id", "station_number"),
    )
    op.create_index(
        "ix_collection_stations_station_number",
        "collection_stations",
        ["station_number"],
    )

    # ── collection_collaborators ────────────────────────────────────
    op.create_table(
        "collection_collaborators",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("permission", sa.String(10), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "user_id"),
    )

    # ── tags ────────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", postgresql.CITEXT(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )

    # ── collection_tags ─────────────────────────────────────────────
    op.create_table(
        "collection_tags",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "tag_id"),
    )

    # ── favourite_collections ───────────────────────────────────────
    op.create_table(
        "favourite_collections",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "collection_id"),
    )

    # ── drop legacy favorite_stations ───────────────────────────────
    op.drop_index("ix_favorite_stations_user_id", table_name="favorite_stations")
    op.drop_index(
        "ix_favorite_stations_station_number", table_name="favorite_stations"
    )
    op.drop_table("favorite_stations")


def downgrade() -> None:
    # Recreate favorite_stations first so any later steps can still reference users.
    op.create_table(
        "favorite_stations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("station_number", sa.String(20), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["station_number"], ["stations.station_number"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "station_number", name="uq_user_station"),
    )
    op.create_index(
        "ix_favorite_stations_user_id", "favorite_stations", ["user_id"]
    )
    op.create_index(
        "ix_favorite_stations_station_number",
        "favorite_stations",
        ["station_number"],
    )

    # Drop new tables in reverse-dependency order.
    op.drop_table("favourite_collections")
    op.drop_table("collection_tags")
    op.drop_table("tags")
    op.drop_table("collection_collaborators")
    op.drop_index(
        "ix_collection_stations_station_number", table_name="collection_stations"
    )
    op.drop_table("collection_stations")
    op.drop_index("ix_collections_owner_user_id", table_name="collections")
    op.drop_table("collections")

    op.drop_column("users", "is_admin")

    # Leave the citext extension installed — it has no per-database cost
    # once enabled, and dropping it would also remove any user-created
    # CITEXT columns outside this schema.
