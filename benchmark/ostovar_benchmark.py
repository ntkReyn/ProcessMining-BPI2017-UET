#!/usr/bin/env python3
"""Build an evaluation table for the 75 Ostovar concept-drift logs.

The implementation intentionally uses only the Python standard library so the
benchmark is reproducible in a clean environment.  Detection is unsupervised:
ground-truth points are used only after detection, during one-to-one matching.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import statistics
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


GROUND_TRUTH_POINTS = (900, 1900)
NOISE_BY_SUFFIX = {None: 0.0, "2": 2.5, "5": 5.0}

START = "__START__"
END = "__END__"


@dataclass(frozen=True)
class LogInfo:
    filename: str
    level: str
    change_pattern: str
    noise_pct: float


@dataclass(frozen=True)
class ScorePoint:
    trace_index: int
    score: float


def parse_filename(path: Path) -> LogInfo:
    match = re.fullmatch(
        r"(Atomic|Composite|Nested)_(.+?)_output_(.+?)(?:_([25]))?\.xes\.gz",
        path.name,
    )
    if not match:
        raise ValueError(f"Unexpected Ostovar filename: {path.name}")
    level, prefix_pattern, output_pattern, suffix = match.groups()
    if prefix_pattern != output_pattern:
        raise ValueError(f"Inconsistent change-pattern labels: {path.name}")
    return LogInfo(path.name, level, prefix_pattern, NOISE_BY_SUFFIX[suffix])


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_trace_features(path: Path) -> tuple[list[set[str]], list[set[str]]]:
    """Return per-trace DFG-edge and activity occurrence sets.

    Sets, instead of raw event counts, prevent loops in a single case from
    dominating a window.  Traces remain in XES document order, which is the
    ordering used by the published trace-index ground truth.
    """
    edge_sets: list[set[str]] = []
    activity_sets: list[set[str]] = []
    with gzip.open(path, "rb") as source:
        for _, elem in ET.iterparse(source, events=("end",)):
            if _local_name(elem.tag) != "trace":
                continue
            activities: list[str] = []
            for event in elem:
                if _local_name(event.tag) != "event":
                    continue
                for attr in event:
                    if (
                        _local_name(attr.tag) == "string"
                        and attr.attrib.get("key") == "concept:name"
                    ):
                        activities.append(attr.attrib.get("value", ""))
                        break
            if activities:
                padded = [START, *activities, END]
                edge_sets.append(
                    {f"{left}->{right}" for left, right in zip(padded, padded[1:])}
                )
                activity_sets.append(set(activities))
            else:
                edge_sets.append(set())
                activity_sets.append(set())
            elem.clear()
    return edge_sets, activity_sets


def _jensen_shannon(left: Counter[str], right: Counter[str]) -> float:
    left_total = sum(left.values())
    right_total = sum(right.values())
    if not left_total or not right_total:
        return 0.0
    score = 0.0
    for key in left.keys() | right.keys():
        p = left[key] / left_total
        q = right[key] / right_total
        midpoint = (p + q) / 2.0
        if p:
            score += 0.5 * p * math.log2(p / midpoint)
        if q:
            score += 0.5 * q * math.log2(q / midpoint)
    return score


def score_windows(
    feature_sets: Sequence[set[str]], window_size: int, step: int
) -> list[ScorePoint]:
    n_traces = len(feature_sets)
    if n_traces < 2 * window_size:
        return []
    left = Counter[str]()
    right = Counter[str]()
    for features in feature_sets[:window_size]:
        left.update(features)
    for features in feature_sets[window_size : 2 * window_size]:
        right.update(features)

    scores: list[ScorePoint] = []
    boundary = window_size
    while boundary <= n_traces - window_size:
        scores.append(ScorePoint(boundary, _jensen_shannon(left, right)))
        next_boundary = boundary + step
        if next_boundary > n_traces - window_size:
            break
        for index in range(boundary - window_size, next_boundary - window_size):
            left.subtract(feature_sets[index])
            left += Counter()
        for index in range(boundary, next_boundary):
            left.update(feature_sets[index])
            right.subtract(feature_sets[index])
            right += Counter()
        for index in range(boundary + window_size, next_boundary + window_size):
            right.update(feature_sets[index])
        boundary = next_boundary
    return scores


def robust_threshold(scores: Sequence[ScorePoint], z: float) -> tuple[float, float, float]:
    values = [point.score for point in scores]
    if not values:
        return math.inf, 0.0, 0.0
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
    robust_sigma = 1.4826 * mad
    # A tiny floor prevents numerical fluctuations in near-deterministic logs
    # from becoming detections when MAD is zero.
    threshold = max(median + z * robust_sigma, median * 1.5, 1e-6)
    return threshold, median, mad


def detect_peaks(
    scores: Sequence[ScorePoint], threshold: float, min_distance: int
) -> list[ScorePoint]:
    if not scores:
        return []
    local: list[ScorePoint] = []
    for index, point in enumerate(scores):
        previous = scores[index - 1].score if index else -math.inf
        following = scores[index + 1].score if index + 1 < len(scores) else -math.inf
        if point.score >= threshold and point.score >= previous and point.score > following:
            local.append(point)

    selected: list[ScorePoint] = []
    for candidate in sorted(local, key=lambda point: point.score, reverse=True):
        if all(
            abs(candidate.trace_index - accepted.trace_index) >= min_distance
            for accepted in selected
        ):
            selected.append(candidate)
    return sorted(selected, key=lambda point: point.trace_index)


def match_points(
    truth: Sequence[int], detected: Sequence[int], tolerance: int
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Maximum-cardinality, then minimum-distance, one-to-one matching.

    Dynamic programming is used instead of nearest-first greedy matching.  A
    greedy match can reduce cardinality when tolerance intervals overlap.
    """
    actual_points = sorted(truth)
    predicted_points = sorted(detected)
    # Each state contains (match_count, total_distance, matched_pairs).
    table: list[list[tuple[int, int, tuple[tuple[int, int], ...]]]] = [
        [(0, 0, ()) for _ in range(len(predicted_points) + 1)]
        for _ in range(len(actual_points) + 1)
    ]

    def better(
        first: tuple[int, int, tuple[tuple[int, int], ...]],
        second: tuple[int, int, tuple[tuple[int, int], ...]],
    ) -> tuple[int, int, tuple[tuple[int, int], ...]]:
        return first if (first[0], -first[1]) >= (second[0], -second[1]) else second

    for i in range(1, len(actual_points) + 1):
        for j in range(1, len(predicted_points) + 1):
            best = better(table[i - 1][j], table[i][j - 1])
            actual = actual_points[i - 1]
            predicted = predicted_points[j - 1]
            distance = abs(actual - predicted)
            if distance <= tolerance:
                previous = table[i - 1][j - 1]
                matched = (
                    previous[0] + 1,
                    previous[1] + distance,
                    (*previous[2], (actual, predicted)),
                )
                best = better(best, matched)
            table[i][j] = best

    matches = list(table[-1][-1][2])
    matched_truth = {actual for actual, _ in matches}
    matched_detected = {predicted for _, predicted in matches}
    return (
        matches,
        [point for point in truth if point not in matched_truth],
        [point for point in detected if point not in matched_detected],
    )


def _rate_changes(
    feature_sets: Sequence[set[str]], point: int, width: int, limit: int
) -> list[dict[str, float | str]]:
    before = feature_sets[max(0, point - width) : point]
    after = feature_sets[point : min(len(feature_sets), point + width)]
    if not before or not after:
        return []
    left = Counter(item for trace in before for item in trace)
    right = Counter(item for trace in after for item in trace)
    changes: list[dict[str, float | str]] = []
    for feature in left.keys() | right.keys():
        before_rate = left[feature] / len(before)
        after_rate = right[feature] / len(after)
        delta = after_rate - before_rate
        pooled = (left[feature] + right[feature]) / (len(before) + len(after))
        standard_error = math.sqrt(
            pooled * (1.0 - pooled) * (1.0 / len(before) + 1.0 / len(after))
        )
        z_score = abs(delta) / standard_error if standard_error else 0.0
        if abs(delta) >= 0.05 and z_score >= 3.0:
            changes.append(
                {
                    "feature": feature,
                    "before_rate": round(before_rate, 4),
                    "after_rate": round(after_rate, 4),
                    "delta": round(delta, 4),
                    "z_score": round(z_score, 3),
                }
            )
    changes.sort(key=lambda item: (abs(float(item["delta"])), float(item["z_score"])), reverse=True)
    return changes[:limit]


def _compact(changes: Sequence[dict[str, float | str]]) -> str:
    return "; ".join(
        f"{item['feature']} ({float(item['delta']):+.3f})" for item in changes
    )


def evaluate_log(
    path: Path,
    window_size: int,
    step: int,
    threshold_z: float,
    tolerance: int,
    localization_width: int,
    localization_limit: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    info = parse_filename(path)
    edges, activities = read_trace_features(path)
    scores = score_windows(edges, window_size, step)
    threshold, score_median, score_mad = robust_threshold(scores, threshold_z)
    peaks = detect_peaks(scores, threshold, min_distance=2 * window_size)
    detected = [peak.trace_index for peak in peaks]
    score_by_point = {peak.trace_index: peak.score for peak in peaks}
    matches, missed, false_positives = match_points(
        GROUND_TRUTH_POINTS, detected, tolerance
    )

    base = {
        "filename": info.filename,
        "level": info.level,
        "change_pattern": info.change_pattern,
        "noise_pct": info.noise_pct,
        "n_traces": len(edges),
        "drift_nature": "Sudden",
        "cause": "Synthetic process-model change",
    }
    result_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []
    for actual, predicted in matches:
        alarm_trace = min(len(edges), predicted + window_size)
        edge_changes = _rate_changes(edges, predicted, localization_width, localization_limit)
        node_changes = _rate_changes(
            activities, predicted, localization_width, localization_limit
        )
        result_rows.append(
            {
                **base,
                "ground_truth_trace": actual,
                "detected_trace": predicted,
                "estimation_error": predicted - actual,
                "alarm_trace": alarm_trace,
                "detection_lag": alarm_trace - actual,
                "outcome": "TP",
                "detection_score": round(score_by_point[predicted], 8),
                "threshold": round(threshold, 8),
                "localized_edges": _compact(edge_changes),
                "localized_nodes": _compact(node_changes),
            }
        )
        detail_rows.append(
            {
                **base,
                "ground_truth_trace": actual,
                "detected_trace": predicted,
                "edges": edge_changes,
                "nodes": node_changes,
            }
        )
    for actual in missed:
        result_rows.append(
            {
                **base,
                "ground_truth_trace": actual,
                "detected_trace": "",
                "estimation_error": "",
                "alarm_trace": "",
                "detection_lag": "",
                "outcome": "FN",
                "detection_score": "",
                "threshold": round(threshold, 8),
                "localized_edges": "",
                "localized_nodes": "",
            }
        )
    for predicted in false_positives:
        edge_changes = _rate_changes(edges, predicted, localization_width, localization_limit)
        node_changes = _rate_changes(
            activities, predicted, localization_width, localization_limit
        )
        result_rows.append(
            {
                **base,
                "ground_truth_trace": "",
                "detected_trace": predicted,
                "estimation_error": "",
                "alarm_trace": min(len(edges), predicted + window_size),
                "detection_lag": "",
                "outcome": "FP",
                "detection_score": round(score_by_point[predicted], 8),
                "threshold": round(threshold, 8),
                "localized_edges": _compact(edge_changes),
                "localized_nodes": _compact(node_changes),
            }
        )
        detail_rows.append(
            {
                **base,
                "ground_truth_trace": None,
                "detected_trace": predicted,
                "edges": edge_changes,
                "nodes": node_changes,
            }
        )
    diagnostics = {
        **base,
        "score_median": round(score_median, 8),
        "score_mad": round(score_mad, 8),
        "threshold": round(threshold, 8),
        "detected_points": detected,
        "scores": [asdict(point) for point in scores],
    }
    return result_rows, detail_rows, diagnostics


def write_csv(path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_ground_truth(log_paths: Sequence[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in log_paths:
        info = parse_filename(path)
        for sequence, point in enumerate(GROUND_TRUTH_POINTS, start=1):
            rows.append(
                {
                    **asdict(info),
                    "drift_sequence": sequence,
                    "ground_truth_trace": point,
                    "drift_nature": "Sudden",
                }
            )
    return rows


def summarize(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, object], list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault((str(row["level"]), row["noise_pct"]), []).append(row)
    groups[("ALL", "ALL")] = list(rows)
    summaries: list[dict[str, object]] = []
    for (level, noise), group in sorted(groups.items(), key=lambda item: str(item[0])):
        tp = sum(row["outcome"] == "TP" for row in group)
        fp = sum(row["outcome"] == "FP" for row in group)
        fn = sum(row["outcome"] == "FN" for row in group)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        errors = [abs(int(row["estimation_error"])) for row in group if row["outcome"] == "TP"]
        lags = [int(row["detection_lag"]) for row in group if row["outcome"] == "TP"]
        summaries.append(
            {
                "level": level,
                "noise_pct": noise,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "mean_absolute_estimation_error": round(statistics.mean(errors), 2) if errors else "",
                "median_absolute_estimation_error": round(statistics.median(errors), 2) if errors else "",
                "mean_detection_lag": round(statistics.mean(lags), 2) if lags else "",
                "median_detection_lag": round(statistics.median(lags), 2) if lags else "",
            }
        )
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("EvaluationLogs/Ostovar"))
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/results"))
    parser.add_argument("--limit", type=int, help="Process only the first N logs (smoke tests)")
    parser.add_argument("--window-size", type=int, default=150)
    parser.add_argument("--step", type=int, default=10)
    parser.add_argument("--threshold-z", type=float, default=6.0)
    parser.add_argument("--tolerance", type=int, default=200)
    parser.add_argument("--localization-width", type=int, default=200)
    parser.add_argument("--localization-limit", type=int, default=8)
    args = parser.parse_args()

    log_paths = sorted(args.input_dir.glob("*.xes.gz"))
    if args.limit is not None:
        log_paths = log_paths[: args.limit]
    if not log_paths:
        parser.error(f"No .xes.gz logs found in {args.input_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    truth_rows = build_ground_truth(log_paths)
    write_csv(
        args.output_dir / "ground_truth.csv",
        truth_rows,
        [
            "filename",
            "level",
            "change_pattern",
            "noise_pct",
            "drift_sequence",
            "ground_truth_trace",
            "drift_nature",
        ],
    )

    all_results: list[dict[str, object]] = []
    all_details: list[dict[str, object]] = []
    all_diagnostics: list[dict[str, object]] = []
    for index, path in enumerate(log_paths, start=1):
        print(f"[{index:02d}/{len(log_paths):02d}] {path.name}", flush=True)
        result, details, diagnostics = evaluate_log(
            path,
            args.window_size,
            args.step,
            args.threshold_z,
            args.tolerance,
            args.localization_width,
            args.localization_limit,
        )
        all_results.extend(result)
        all_details.extend(details)
        all_diagnostics.append(diagnostics)

    result_fields = [
        "filename",
        "level",
        "change_pattern",
        "noise_pct",
        "n_traces",
        "ground_truth_trace",
        "detected_trace",
        "estimation_error",
        "alarm_trace",
        "detection_lag",
        "outcome",
        "detection_score",
        "threshold",
        "localized_edges",
        "localized_nodes",
        "drift_nature",
        "cause",
    ]
    write_csv(args.output_dir / "benchmark_table.csv", all_results, result_fields)
    summary_rows = summarize(all_results)
    write_csv(
        args.output_dir / "summary.csv",
        summary_rows,
        [
            "level",
            "noise_pct",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
            "mean_absolute_estimation_error",
            "median_absolute_estimation_error",
            "mean_detection_lag",
            "median_detection_lag",
        ],
    )
    with (args.output_dir / "localization_details.json").open("w", encoding="utf-8") as target:
        json.dump(all_details, target, ensure_ascii=False, indent=2)
    with (args.output_dir / "detection_diagnostics.json").open("w", encoding="utf-8") as target:
        json.dump(all_diagnostics, target, ensure_ascii=False)
    print(f"Wrote benchmark artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
