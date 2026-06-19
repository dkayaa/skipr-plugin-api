"""create v2 tables

Revision ID: 001_create_v2_tables
Revises:
Create Date: 2026-06-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "001_create_v2_tables"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "videos" not in existing_tables:
        op.create_table(
            "videos",
            sa.Column("pk", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("video_id", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text(
                "CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("pk"),
            sa.UniqueConstraint("video_id"),
        )
        op.create_index("ix_videos_video_id", "videos",
                        ["video_id"], unique=False)
    else:
        existing_indexes = {index["name"]
                            for index in inspector.get_indexes("videos")}
        if "ix_videos_video_id" not in existing_indexes:
            op.create_index("ix_videos_video_id", "videos",
                            ["video_id"], unique=False)

        has_video_id_unique = any(
            constraint.get("column_names") == ["video_id"]
            for constraint in inspector.get_unique_constraints("videos")
        )
        if not has_video_id_unique:
            op.create_unique_constraint(
                "uq_videos_video_id", "videos", ["video_id"])

    if "intervals" not in existing_tables:
        op.create_table(
            "intervals",
            sa.Column("pk", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("start_time", sa.Float(), nullable=False),
            sa.Column("end_time", sa.Float(), nullable=False),
            sa.Column("orgs", sa.String(length=1000),
                      server_default="", nullable=True),
            sa.Column("video_fk", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text(
                "CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["video_fk"], ["videos.pk"]),
            sa.PrimaryKeyConstraint("pk"),
        )
        op.create_index("ix_intervals_video_fk", "intervals",
                        ["video_fk"], unique=False)
    else:
        existing_indexes = {index["name"]
                            for index in inspector.get_indexes("intervals")}
        if "ix_intervals_video_fk" not in existing_indexes:
            op.create_index("ix_intervals_video_fk", "intervals", [
                            "video_fk"], unique=False)

    if "labels" not in existing_tables:
        op.create_table(
            "labels",
            sa.Column("pk", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("start_time", sa.Float(), nullable=False),
            sa.Column("label", sa.Integer(), nullable=False),
            sa.Column("video_fk", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text(
                "CURRENT_TIMESTAMP"), nullable=True),
            sa.ForeignKeyConstraint(["video_fk"], ["videos.pk"]),
            sa.PrimaryKeyConstraint("pk"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "intervals" in inspector.get_table_names():
        existing_indexes = {index["name"]
                            for index in inspector.get_indexes("intervals")}
        if "ix_intervals_video_fk" in existing_indexes:
            op.drop_index("ix_intervals_video_fk", table_name="intervals")
        op.drop_table("intervals")
