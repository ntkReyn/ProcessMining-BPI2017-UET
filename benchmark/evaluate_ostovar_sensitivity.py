#!/usr/bin/env python3
"""Re-evaluate cached Ostovar scores across thresholds and match tolerances."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ostovar_benchmark import (
    GROUND_TRUTH_POINTS,
    ScorePoint,
    detect_peaks,
    match_points,
    robust_threshold,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diagnostics",
        type=Path,
        default=Path("benchmark/results/detection_diagnostics.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark/results/sensitivity_analysis.csv"),
    )
    parser.add_argument("--threshold-z", type=float, nargs="+", default=[4, 5, 6, 7, 8])
    parser.add_argument("--tolerance", type=int, nargs="+", default=[50, 100, 150, 200])
    parser.add_argument("--min-distance", type=int, default=300)
    args = parser.parse_args()

    with args.diagnostics.open("r", encoding="utf-8") as source:
        diagnostics = json.load(source)

    rows: list[dict[str, object]] = []
    for threshold_z in args.threshold_z:
        detections_by_log: list[list[int]] = []
        for log in diagnostics:
            scores = [ScorePoint(**point) for point in log["scores"]]
            threshold, _, _ = robust_threshold(scores, threshold_z)
            peaks = detect_peaks(scores, threshold, args.min_distance)
            detections_by_log.append([point.trace_index for point in peaks])

        for tolerance in args.tolerance:
            tp = fp = fn = 0
            absolute_errors: list[int] = []
            for detected in detections_by_log:
                matches, missed, false_positives = match_points(
                    GROUND_TRUTH_POINTS, detected, tolerance
                )
                tp += len(matches)
                fn += len(missed)
                fp += len(false_positives)
                absolute_errors.extend(abs(actual - predicted) for actual, predicted in matches)
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
            rows.append(
                {
                    "threshold_z": threshold_z,
                    "tolerance": tolerance,
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "mean_absolute_estimation_error_matched": round(
                        sum(absolute_errors) / len(absolute_errors), 2
                    )
                    if absolute_errors
                    else "",
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} sensitivity rows to {args.output}")


if __name__ == "__main__":
    main()
