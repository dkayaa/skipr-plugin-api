import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.support.path import setup_server_import_path

setup_server_import_path()

from backend.database import Base  # noqa: E402
from backend.interval_store import IntervalStore  # noqa: E402
from backend.models import Video  # noqa: E402
from backend.pipeline import PIPELINE_VERSION, STATUS_FAILED, STATUS_PENDING, STATUS_READY  # noqa: E402


TEST_MODEL = "kayaaaa/ad-classifier"


class TestIntervalStore(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.store = IntervalStore(self.session)
        # Isolate from server/.env so cached rows match the active model version.
        self._model_patcher = patch(
            "backend.interval_store.get_model_version",
            return_value=TEST_MODEL,
        )
        self._model_patcher.start()

    def tearDown(self):
        self._model_patcher.stop()
        self.session.close()

    def _ready_video(self, video_id: str = "dQw4w9WgXcQ") -> Video:
        video = Video(
            video_id=video_id,
            status=STATUS_READY,
            model_version=TEST_MODEL,
            pipeline_version=PIPELINE_VERSION,
            intervals_json=[{"start_time": 10, "end_time": 60, "orgs": ["Acme"]}],
        )
        self.session.add(video)
        self.session.commit()
        return video

    @patch("backend.interval_store.start_analysis_job")
    @patch("backend.interval_store.is_analysis_active", return_value=False)
    def test_request_intervals_returns_pending_for_new_video(self, _mock_active, mock_start):
        result = self.store.request_intervals("dQw4w9WgXcQ", lambda: {"intervals": []})

        self.assertEqual(result, {"status": STATUS_PENDING})
        mock_start.assert_called_once()
        video = self.session.query(Video).filter_by(video_id="dQw4w9WgXcQ").one()
        self.assertEqual(video.status, STATUS_PENDING)

    @patch("backend.interval_store.start_analysis_job")
    def test_request_intervals_returns_ready_for_cached_video(self, mock_start):
        self._ready_video()

        result = self.store.request_intervals("dQw4w9WgXcQ", lambda: {"intervals": []})

        self.assertEqual(result["status"], STATUS_READY)
        self.assertEqual(
            result["intervals"],
            [{"id": 1, "start_time": 10, "end_time": 60, "orgs": ["Acme"]}],
        )
        mock_start.assert_not_called()

    @patch("backend.interval_store.start_analysis_job")
    def test_request_intervals_returns_failed_without_retry(self, mock_start):
        video = Video(
            video_id="dQw4w9WgXcQ",
            status=STATUS_FAILED,
            model_version=TEST_MODEL,
            pipeline_version=PIPELINE_VERSION,
            error_message="transcript unavailable",
        )
        self.session.add(video)
        self.session.commit()

        result = self.store.request_intervals("dQw4w9WgXcQ", lambda: {"intervals": []})

        self.assertEqual(
            result,
            {"status": STATUS_FAILED, "error": "transcript unavailable"},
        )
        mock_start.assert_not_called()

    @patch("backend.interval_store.start_analysis_job")
    @patch("backend.interval_store.is_analysis_active", return_value=False)
    def test_request_intervals_retries_failed_when_requested(self, _mock_active, mock_start):
        video = Video(
            video_id="dQw4w9WgXcQ",
            status=STATUS_FAILED,
            model_version=TEST_MODEL,
            pipeline_version=PIPELINE_VERSION,
            error_message="transcript unavailable",
        )
        self.session.add(video)
        self.session.commit()

        result = self.store.request_intervals(
            "dQw4w9WgXcQ",
            lambda: {"intervals": []},
            retry=True,
        )

        self.assertEqual(result, {"status": STATUS_PENDING})
        mock_start.assert_called_once()

    @patch("backend.interval_store.start_analysis_job")
    @patch("backend.interval_store.is_analysis_active", return_value=True)
    def test_request_intervals_returns_pending_while_job_active(self, _mock_active, mock_start):
        video = Video(video_id="dQw4w9WgXcQ", status=STATUS_PENDING)
        self.session.add(video)
        self.session.commit()

        result = self.store.request_intervals("dQw4w9WgXcQ", lambda: {"intervals": []})

        self.assertEqual(result, {"status": STATUS_PENDING})
        mock_start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
