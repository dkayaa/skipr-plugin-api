import unittest

from tests.support.path import setup_server_import_path

setup_server_import_path()

from transcript_labelling import compute_intervals  # noqa: E402


class TestTranscriptLabelling(unittest.TestCase):

    def test_no_merge_basic(self):
        input = [{
            'start': 10,
            'label': 1
        }, {
            'start': 20,
            'label': 0
        }, {
            'start': 30,
            'label': 1
        }]

        expected = [{
            'start_time': 10,
            'end_time': 20,
            'orgs': ['UNKNOWN']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_no_merge_basic_with_orgs(self):
        input = [{
            'start': 10,
            'label': 1,
            'orgs': ['org1']
        }, {
            'start': 20,
            'label': 0
        }, {
            'start': 30,
            'label': 1
        }]

        expected = [{
            'start_time': 10,
            'end_time': 20,
            'orgs': ['org1']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_all_merge_basic(self):
        input = [{
            'start': 10,
            'label': 1
        }, {
            'start': 20,
            'label': 1
        }, {
            'start': 30,
            'label': 1
        }, {
            'start': 40,
            'label': 0
        }]

        expected = [{
            'start_time': 10,
            'end_time': 40,
            'orgs': ['UNKNOWN']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_all_merge_basic_orgs_same(self):
        input = [{
            'start': 10,
            'label': 1,
            'orgs': ['org1']
        }, {
            'start': 20,
            'label': 1,
            'orgs': ['org1']
        }, {
            'start': 30,
            'label': 1,
            'orgs': []
        }, {
            'start': 40,
            'label': 0
        }]

        expected = [{
            'start_time': 10,
            'end_time': 40,
            'orgs': ['org1']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_all_merge_basic_orgs_dijoint(self):
        input = [{
            'start': 10,
            'label': 1,
            'orgs': ['org1']
        }, {
            'start': 20,
            'label': 1,
            'orgs': ['org2']
        }, {
            'start': 30,
            'label': 1,
            'orgs': []
        }, {
            'start': 40,
            'label': 0
        }]

        expected = [{
            'start_time': 10,
            'end_time': 40,
            'orgs': ['org1', 'org2']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_all_merge_basic_orgs_single(self):
        input = [{
            'start': 10,
            'label': 1,
            'orgs': ['org1', 'org2']
        }, {
            'start': 20,
            'label': 1,
            'orgs': []
        }, {
            'start': 30,
            'label': 1,
            'orgs': []
        }, {
            'start': 40,
            'label': 0
        }]

        expected = [{
            'start_time': 10,
            'end_time': 40,
            'orgs': ['org1', 'org2']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_no_overlap_hits_threshold_basic(self):
        input = [{
            'start': 10,
            'label': 1
        }, {
            'start': 15,
            'label': 0
        }, {
            'start': 20,
            'label': 1
        }, {
            'start': 25,
            'label': 0
        }]

        expected = [{
            'start_time': 10,
            'end_time': 25,
            'orgs': ['UNKNOWN']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_no_overlap_no_threshold_basic(self):
        input = [{
            'start': 10,
            'label': 1
        }, {
            'start': 15,
            'label': 0
        }, {
            'start': 21,
            'label': 1
        }, {
            'start': 25,
            'label': 0
        }]

        expected = [{
            'start_time': 10,
            'end_time': 15,
            'orgs': ['UNKNOWN']
        }, {
            'start_time': 21,
            'end_time': 25,
            'orgs': ['UNKNOWN']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)

    def test_trailing_ad_without_closing_zero_is_skipped(self):
        input = [{
            'start': 10,
            'label': 1
        }, {
            'start': 20,
            'label': 1
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), [])

    def test_contiguous_ones_collects_all_window_starts(self):
        input = [{
            'start': 100,
            'label': 1,
            'orgs': ['A']
        }, {
            'start': 115,
            'label': 1,
            'orgs': ['B']
        }, {
            'start': 130,
            'label': 0
        }]

        expected = [{
            'start_time': 100,
            'end_time': 130,
            'orgs': ['A', 'B']
        }]

        self.assertEqual(compute_intervals(input, min_duration=0), expected)


if __name__ == '__main__':
    unittest.main()
