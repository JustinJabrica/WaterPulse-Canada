"""
SQLAlchemy models for the Collections feature.

A Collection is a named, user-owned grouping of stations with optional
collaborators (view / edit), public-vs-private visibility, an optional
view-only share token, and tags. Replaces the legacy `favorite_stations`
single-row "star a station" concept.

See `C:\\Users\\Justi\\.claude\\plans\\nominatim-is-fine-ux-gentle-rainbow.md`
for the full design and permission matrix.
"""
from datetime import datetime

from sqlalchemy import (
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    is_valuable: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    share_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_collection_owner_name"),
    )

    owner: Mapped["User"] = relationship(back_populates="collections")
    stations: Mapped[list["CollectionStation"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )
    collaborators: Mapped[list["CollectionCollaborator"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )
    tag_links: Mapped[list["CollectionTag"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )
    favourited_by: Mapped[list["FavouriteCollection"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Collection {self.id} {self.name!r} owner={self.owner_user_id}>"


class CollectionStation(Base):
    __tablename__ = "collection_stations"

    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    station_number: Mapped[str] = mapped_column(
        String(20), ForeignKey("stations.station_number"), primary_key=True, index=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    collection: Mapped["Collection"] = relationship(back_populates="stations")
    station: Mapped["Station"] = relationship()


class CollectionCollaborator(Base):
    __tablename__ = "collection_collaborators"

    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(10))  # 'view' | 'edit'
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    collection: Mapped["Collection"] = relationship(back_populates="collaborators")
    user: Mapped["User"] = relationship(back_populates="collaborations")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(CITEXT, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    collection_links: Mapped[list["CollectionTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tag {self.name!r}>"


class CollectionTag(Base):
    __tablename__ = "collection_tags"

    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )

    collection: Mapped["Collection"] = relationship(back_populates="tag_links")
    tag: Mapped["Tag"] = relationship(back_populates="collection_links")


class FavouriteCollection(Base):
    __tablename__ = "favourite_collections"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    collection_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="favourite_collections")
    collection: Mapped["Collection"] = relationship(back_populates="favourited_by")
