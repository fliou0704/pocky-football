import unittest
from football_draft_analysis import positional_benchmark, rookie_status

class DraftV3(unittest.TestCase):
    def test_gain(self):
        self.assertEqual(positional_benchmark(100, 8, [10,20,30,40,45,50,55,60]), (40, 'available'))
        self.assertEqual(positional_benchmark(10, 2, [10,20]), (-10, 'available'))
    def test_no_invented_benchmarks(self):
        for rank, reason in [(None,'missing_rank'), (2.5,'fractional_tie'), (300,'beyond_drafted_position')]:
            self.assertEqual(positional_benchmark(100,rank,[10,20]), (None,reason))
    def test_zero_rank_does_not_become_benchmark(self):
        self.assertEqual(positional_benchmark(10,0,[10])[0], None)
    def test_rookie_requires_metadata(self):
        self.assertIsNone(rookie_status({},2025))
        self.assertTrue(rookie_status({'rookieSeason':2025},2025))
        self.assertFalse(rookie_status({'rookieSeason':2024},2025))
