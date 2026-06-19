import os
import unittest
from unittest.mock import MagicMock, patch

from tests.support.path import setup_server_import_path

setup_server_import_path()

# WINDOW_SIZE=20, STRIDE=5 → need 31+ snippets for three windows (0, 5, 10).
_MIN_SNIPPETS = 31


class TestGetLabelledTscript(unittest.TestCase):
    def _snippets(self, count: int = _MIN_SNIPPETS):
        return [MagicMock(text=f"word{i}", start=float(i * 5)) for i in range(count)]

    @patch("transcript_labelling._orgs_for_ad_window", return_value=["Acme"])
    @patch("transcript_labelling._classify_windows", return_value=[0, 1, 0])
    @patch("transcript_labelling.ytt_api.fetch")
    def test_ner_runs_only_on_ad_windows(self, mock_fetch, _mock_classify, mock_orgs):
        mock_fetch.return_value = self._snippets()

        from transcript_labelling import get_labelled_tscript  # noqa: E402

        segments = get_labelled_tscript("dQw4w9WgXcQ")

        mock_orgs.assert_called_once()
        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[1]["orgs"], ["Acme"])
        self.assertEqual(segments[0]["orgs"], [])
        self.assertEqual(segments[2]["orgs"], [])

    @patch("transcript_labelling._classify_windows", return_value=[0, 1, 0])
    @patch("transcript_labelling.ytt_api.fetch")
    def test_ner_skipped_when_disabled(self, mock_fetch, _mock_classify):
        mock_fetch.return_value = self._snippets()

        from transcript_labelling import get_labelled_tscript  # noqa: E402

        with patch.dict(os.environ, {"NER_ENABLED": "false"}, clear=False):
            with patch("transcript_labelling._ner_enabled", return_value=False):
                segments = get_labelled_tscript("dQw4w9WgXcQ")

        self.assertEqual(len(segments), 3)
        self.assertEqual(segments[1]["orgs"], [])


if __name__ == "__main__":
    unittest.main()
