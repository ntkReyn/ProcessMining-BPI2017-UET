import unittest
from collections import Counter

from ostovar_benchmark import ScorePoint, _jensen_shannon, detect_peaks, match_points, parse_filename
from pathlib import Path


class BenchmarkTests(unittest.TestCase):
    def test_filename_metadata_and_noise(self):
        info = parse_filename(Path("Atomic_Swap_output_Swap_2.xes.gz"))
        self.assertEqual(info.level, "Atomic")
        self.assertEqual(info.change_pattern, "Swap")
        self.assertEqual(info.noise_pct, 2.5)

    def test_js_divergence(self):
        self.assertEqual(_jensen_shannon(Counter(a=2), Counter(a=3)), 0.0)
        self.assertAlmostEqual(_jensen_shannon(Counter(a=1), Counter(b=1)), 1.0)

    def test_peak_suppression(self):
        scores = [
            ScorePoint(100, 0.1),
            ScorePoint(110, 0.8),
            ScorePoint(120, 0.2),
            ScorePoint(500, 0.7),
            ScorePoint(510, 0.1),
        ]
        self.assertEqual(
            [point.trace_index for point in detect_peaks(scores, 0.5, 100)],
            [110, 500],
        )

    def test_one_to_one_matching(self):
        matches, missed, false_positives = match_points(
            [900, 1900], [890, 920, 1910, 2500], 200
        )
        self.assertEqual(matches, [(900, 890), (1900, 1910)])
        self.assertEqual(missed, [])
        self.assertEqual(false_positives, [920, 2500])

    def test_matching_prioritizes_cardinality_over_nearest_pair(self):
        matches, missed, false_positives = match_points([0, 10], [8, 18], 10)
        self.assertEqual(matches, [(0, 8), (10, 18)])
        self.assertEqual(missed, [])
        self.assertEqual(false_positives, [])


if __name__ == "__main__":
    unittest.main()
