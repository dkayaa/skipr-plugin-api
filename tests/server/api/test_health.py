import unittest
from unittest.mock import patch

from tests.support.path import setup_server_import_path

setup_server_import_path()

from app import app  # noqa: E402


class TestHealth(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @patch("app.get_session")
    def test_health_ok(self, mock_get_session):
        mock_get_session.return_value.execute.return_value = None
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    @patch("app.get_session")
    def test_health_db_error(self, mock_get_session):
        mock_get_session.return_value.execute.side_effect = RuntimeError(
            "db down")
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIn("db down", body["error"])


if __name__ == "__main__":
    unittest.main()
