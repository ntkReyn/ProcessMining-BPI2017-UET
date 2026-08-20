import csv
import tempfile
import unittest
from pathlib import Path

from bpi2017_ostovar_analysis import (
    build_calendar_consensus,
    cluster_multiscale_peaks,
    read_bpi_traces,
)


class Bpi2017OstovarTests(unittest.TestCase):
    def test_cluster_uses_at_most_one_peak_per_window(self):
        peaks = [
            {"window_size": 150, "trace_index": 1000, "score_ratio": 2.0, "score": 0.2},
            {"window_size": 150, "trace_index": 1100, "score_ratio": 1.5, "score": 0.15},
            {"window_size": 300, "trace_index": 1020, "score_ratio": 1.8, "score": 0.18},
            {"window_size": 500, "trace_index": 980, "score_ratio": 1.4, "score": 0.14},
        ]
        clusters = cluster_multiscale_peaks(peaks, tolerance=150)
        self.assertEqual(2, len(clusters))
        for cluster in clusters:
            windows = [int(item["window_size"]) for item in cluster]
            self.assertEqual(len(windows), len(set(windows)))
        self.assertEqual(3, max(len(cluster) for cluster in clusters))

    def test_reader_filters_complete_and_orders_cases(self):
        headers = [
            "case:concept:name",
            "concept:name",
            "time:timestamp",
            "lifecycle:transition",
            "case:ApplicationType",
        ]
        rows = [
            ["C2", "B", "2017-01-02T00:01:00+00:00", "complete", "Limit raise"],
            ["C1", "A", "2017-01-01T00:00:00+00:00", "schedule", "New credit"],
            ["C2", "A", "2017-01-02T00:00:00+00:00", "complete", "Limit raise"],
            ["C1", "B", "2017-01-01T00:01:00+00:00", "complete", "New credit"],
            ["C1", "A", "2017-01-01T00:00:30+00:00", "complete", "New credit"],
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fixture.csv"
            with path.open("w", encoding="utf-8", newline="") as target:
                writer = csv.writer(target)
                writer.writerow(headers)
                writer.writerows(rows)
            traces, diagnostics = read_bpi_traces(path, lifecycle="complete")
        self.assertEqual(["C1", "C2"], [trace.case_id for trace in traces])
        self.assertEqual(4, diagnostics["retained_rows"])
        self.assertEqual(2, traces[0].event_count)
        self.assertIn("A->B", traces[0].edges)

    def test_calendar_consensus_groups_cross_scope_candidates(self):
        base = {
            "support_count": 2,
            "max_score_ratio": 1.2,
            "localized_edges": "A->B (+0.2)",
            "localized_nodes": "B (+0.2)",
        }
        candidates = [
            {
                **base,
                "candidate_id": "ALL-D001",
                "scope": "ALL",
                "estimated_change_time": "2016-01-01T00:00:00+00:00",
            },
            {
                **base,
                "candidate_id": "NEW-D001",
                "scope": "New credit",
                "estimated_change_time": "2016-01-05T00:00:00+00:00",
            },
            {
                **base,
                "candidate_id": "ALL-D002",
                "scope": "ALL",
                "estimated_change_time": "2016-03-01T00:00:00+00:00",
            },
        ]
        rows = build_calendar_consensus(candidates, tolerance_days=14)
        self.assertEqual(2, len(rows))
        self.assertEqual("cross-scope-multiscale", rows[0]["consensus_strength"])


if __name__ == "__main__":
    unittest.main()
