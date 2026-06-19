import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.analysis_runner import is_analysis_active, start_analysis_job
from backend.models import Video
from backend.pipeline import (
    PIPELINE_VERSION,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_READY,
    get_model_version,
)

logger = logging.getLogger(__name__)


class IntervalStore:
    def __init__(self, session: Session):
        self._session = session

    def request_intervals(
        self,
        video_id: str,
        compute_analysis: Callable[[], dict],
        *,
        retry: bool = False,
    ) -> dict:
        current_model = get_model_version()
        video = self._session.scalar(
            select(Video).where(Video.video_id == video_id))

        if video is not None and self._has_cached_intervals(video):
            if not self._needs_recompute(video, current_model):
                if video.model_version in (None, "migrated"):
                    logger.info(
                        "Backfilling metadata for cached video video_id=%s",
                        video_id,
                    )
                    self._backfill_metadata(video, current_model)
                    self._session.commit()
                logger.info(
                    "Cache hit video_id=%s interval_count=%d",
                    video_id,
                    len(video.intervals_json or []),
                )
                return self._status_ready(video)
            logger.info(
                "Recompute required video_id=%s pipeline_version=%s model_version=%s",
                video_id,
                video.pipeline_version,
                video.model_version,
            )

        if (
            video is not None
            and video.status == STATUS_FAILED
            and not retry
            and not self._needs_recompute(video, current_model)
        ):
            logger.warning(
                "Returning cached failure video_id=%s error=%s",
                video_id,
                video.error_message,
            )
            return self._status_failed(video)

        if video is not None and video.status == STATUS_PENDING:
            if is_analysis_active(video_id):
                logger.info(
                    "Analysis already in progress video_id=%s",
                    video_id,
                )
                return self._status_pending()
            logger.warning(
                "Pending row without active job; restarting analysis video_id=%s",
                video_id,
            )
            self._mark_pending(video, video_id)
            start_analysis_job(video_id, compute_analysis)
            return self._status_pending()

        if video is None:
            logger.info(
                "Starting analysis for new video video_id=%s", video_id)
        elif retry and video.status == STATUS_FAILED:
            logger.info("Retrying failed analysis video_id=%s", video_id)
        else:
            logger.info("Starting analysis video_id=%s status=%s",
                        video_id, video.status)

        self._mark_pending(video, video_id)
        start_analysis_job(video_id, compute_analysis)
        return self._status_pending()

    def _mark_pending(self, video: Video | None, video_id: str) -> None:
        if video is None:
            video = Video(video_id=video_id, status=STATUS_PENDING)
            self._session.add(video)
        else:
            video.status = STATUS_PENDING
            video.error_message = None
        self._session.commit()

    @staticmethod
    def _has_cached_intervals(video: Video) -> bool:
        return video.status == STATUS_READY and video.intervals_json is not None

    @staticmethod
    def _needs_recompute(video: Video, current_model: str) -> bool:
        if video.pipeline_version != PIPELINE_VERSION:
            return True
        if video.model_version in (None, "migrated"):
            return False
        return video.model_version != current_model

    def _backfill_metadata(self, video: Video, current_model: str) -> None:
        video.model_version = current_model
        video.pipeline_version = PIPELINE_VERSION
        if video.computed_at is None:
            video.computed_at = datetime.now(timezone.utc)

    @staticmethod
    def format_intervals(intervals_json: list[dict] | None) -> list[dict]:
        if not intervals_json:
            return []

        return [
            {
                "id": index + 1,
                "start_time": int(item["start_time"]),
                "end_time": int(item["end_time"]),
                "orgs": item["orgs"],
            }
            for index, item in enumerate(intervals_json)
        ]

    def _status_ready(self, video: Video) -> dict:
        return {
            "status": STATUS_READY,
            "intervals": self.format_intervals(video.intervals_json),
        }

    @staticmethod
    def _status_pending() -> dict:
        return {"status": STATUS_PENDING}

    @staticmethod
    def _status_failed(video: Video) -> dict:
        return {
            "status": STATUS_FAILED,
            "error": video.error_message or "Analysis failed",
        }
