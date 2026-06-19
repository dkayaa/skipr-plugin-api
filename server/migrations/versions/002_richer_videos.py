"""richer videos row with intervals_json

Revision ID: 002_richer_videos
Revises: 001_create_v2_tables
Create Date: 2026-06-05

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "002_richer_videos"
down_revision: Union[str, Sequence[str], None] = "001_create_v2_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    video_columns = _column_names(inspector, "videos")

    if "status" not in video_columns:
        op.add_column(
            "videos",
            sa.Column("status", sa.String(length=20),
                      server_default="pending", nullable=False),
        )
    if "model_version" not in video_columns:
        op.add_column("videos", sa.Column("model_version",
                      sa.String(length=255), nullable=True))
    if "pipeline_version" not in video_columns:
        op.add_column("videos", sa.Column("pipeline_version",
                      sa.String(length=50), nullable=True))
    if "transcript_hash" not in video_columns:
        op.add_column("videos", sa.Column("transcript_hash",
                      sa.String(length=64), nullable=True))
    if "intervals_json" not in video_columns:
        op.add_column("videos", sa.Column(
            "intervals_json", sa.JSON(), nullable=True))
    if "computed_at" not in video_columns:
        op.add_column("videos", sa.Column(
            "computed_at", sa.DateTime(), nullable=True))
    if "error_message" not in video_columns:
        op.add_column("videos", sa.Column(
            "error_message", sa.Text(), nullable=True))

    if "intervals" in inspector.get_table_names():
        rows = bind.execute(
            sa.text(
                """
                SELECT v.pk, i.start_time, i.end_time, i.orgs
                FROM intervals i
                JOIN videos v ON v.pk = i.video_fk
                ORDER BY v.pk, i.start_time
                """
            )
        ).fetchall()

        intervals_by_video: dict[int, list[dict]] = {}
        for pk, start_time, end_time, orgs in rows:
            intervals_by_video.setdefault(pk, []).append(
                {
                    "start_time": start_time,
                    "end_time": end_time,
                    "orgs": orgs.split("|") if orgs else [],
                }
            )

        for pk, intervals in intervals_by_video.items():
            bind.execute(
                sa.text(
                    """
                    UPDATE videos
                    SET intervals_json = :intervals_json,
                        status = 'ready',
                        model_version = 'migrated',
                        pipeline_version = '1',
                        computed_at = CURRENT_TIMESTAMP
                    WHERE pk = :pk
                    """
                ),
                {"intervals_json": json.dumps(intervals), "pk": pk},
            )

        foreign_keys = inspector.get_foreign_keys("intervals")
        for foreign_key in foreign_keys:
            op.drop_constraint(
                foreign_key["name"], "intervals", type_="foreignkey")
        op.drop_table("intervals")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "intervals" not in inspector.get_table_names():
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

        videos = bind.execute(
            sa.text(
                "SELECT pk, intervals_json FROM videos WHERE intervals_json IS NOT NULL")
        ).fetchall()
        for video_pk, intervals_json in videos:
            intervals = json.loads(intervals_json) if isinstance(
                intervals_json, str) else intervals_json
            for item in intervals:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO intervals (start_time, end_time, orgs, video_fk)
                        VALUES (:start_time, :end_time, :orgs, :video_fk)
                        """
                    ),
                    {
                        "start_time": item["start_time"],
                        "end_time": item["end_time"],
                        "orgs": "|".join(item.get("orgs", [])),
                        "video_fk": video_pk,
                    },
                )

    video_columns = _column_names(inspect(bind), "videos")
    for column in (
        "error_message",
        "computed_at",
        "intervals_json",
        "transcript_hash",
        "pipeline_version",
        "model_version",
        "status",
    ):
        if column in video_columns:
            op.drop_column("videos", column)
