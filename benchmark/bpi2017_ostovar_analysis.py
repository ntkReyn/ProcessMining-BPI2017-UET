#!/usr/bin/env python3
"""Apply the Ostovar DFG/JSD drift logic to the BPI Challenge 2017 log.

Unlike the synthetic Ostovar benchmark, BPI 2017 has no authoritative drift
ground truth.  This script therefore emits *candidate* change points and their
local explanations; it deliberately does not assign TP/FP/FN labels.

The implementation uses only the Python standard library.  It imports the
tested scoring, robust-threshold, peak-selection, and localization functions
from ``ostovar_benchmark.py`` so the analytical core remains identical.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from ostovar_benchmark import (
    END,
    START,
    _compact,
    _rate_changes,
    detect_peaks,
    robust_threshold,
    score_windows,
)


@dataclass(frozen=True)
class TraceRecord:
    global_trace_index: int
    case_id: str
    application_type: str
    start_time: datetime
    end_time: datetime
    event_count: int
    activity_count: int
    edges: set[str]
    activities: set[str]


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_bpi_traces(
    path: Path, lifecycle: str | None = "complete"
) -> tuple[list[TraceRecord], dict[str, object]]:
    """Read BPI CSV events and return cases ordered by their start timestamp.

    Cases are collected in a dictionary because event rows are not assumed to
    be contiguous.  Activity names are interned to reduce memory pressure on
    the 1.2-million-row source file.
    """

    cases: dict[str, dict[str, object]] = {}
    all_case_ids: set[str] = set()
    lifecycle_counts: Counter[str] = Counter()
    total_rows = 0
    kept_rows = 0
    skipped_missing = 0

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "case:concept:name",
            "concept:name",
            "time:timestamp",
            "lifecycle:transition",
            "case:ApplicationType",
        }
        missing = sorted(required - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Missing required BPI columns: {', '.join(missing)}")

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            case_id = (row.get("case:concept:name") or "").strip()
            activity = (row.get("concept:name") or "").strip()
            timestamp = (row.get("time:timestamp") or "").strip()
            transition = (row.get("lifecycle:transition") or "").strip().lower()
            lifecycle_counts[transition or "(blank)"] += 1
            if case_id:
                all_case_ids.add(case_id)
            if lifecycle is not None and transition != lifecycle.lower():
                continue
            if not case_id or not activity or not timestamp:
                skipped_missing += 1
                continue

            payload = cases.setdefault(
                case_id,
                {
                    "application_type": "",
                    "events": [],
                },
            )
            application_type = (row.get("case:ApplicationType") or "").strip()
            if application_type and not payload["application_type"]:
                payload["application_type"] = application_type
            events = payload["events"]
            assert isinstance(events, list)
            events.append((timestamp, row_number, sys.intern(activity)))
            kept_rows += 1

    provisional: list[TraceRecord] = []
    while cases:
        case_id, payload = cases.popitem()
        events = payload["events"]
        assert isinstance(events, list)
        events.sort(key=lambda item: (item[0], item[1]))
        activities_in_order = [item[2] for item in events]
        if not activities_in_order:
            continue
        padded = [START, *activities_in_order, END]
        edge_set = {
            f"{left}->{right}" for left, right in zip(padded, padded[1:])
        }
        activity_set = set(activities_in_order)
        provisional.append(
            TraceRecord(
                global_trace_index=-1,
                case_id=case_id,
                application_type=str(payload["application_type"] or "Unknown"),
                start_time=_parse_timestamp(events[0][0]),
                end_time=_parse_timestamp(events[-1][0]),
                event_count=len(activities_in_order),
                activity_count=len(activity_set),
                edges=edge_set,
                activities=activity_set,
            )
        )

    provisional.sort(key=lambda trace: (trace.start_time, trace.case_id))
    traces = [
        TraceRecord(
            global_trace_index=index,
            case_id=trace.case_id,
            application_type=trace.application_type,
            start_time=trace.start_time,
            end_time=trace.end_time,
            event_count=trace.event_count,
            activity_count=trace.activity_count,
            edges=trace.edges,
            activities=trace.activities,
        )
        for index, trace in enumerate(provisional)
    ]
    diagnostics: dict[str, object] = {
        "input_rows": total_rows,
        "input_cases": len(all_case_ids),
        "retained_rows": kept_rows,
        "retained_cases": len(traces),
        "cases_without_retained_events": len(all_case_ids) - len(traces),
        "skipped_missing_required_values": skipped_missing,
        "lifecycle_filter": lifecycle if lifecycle is not None else "ALL",
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
    }
    return traces, diagnostics


def _iso(value: datetime) -> str:
    return value.isoformat()


def _year_week(value: datetime) -> str:
    iso = value.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _scope_key(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.upper())
    return "_".join(part for part in cleaned.split("_") if part)


def cluster_multiscale_peaks(
    peaks: Sequence[dict[str, object]], tolerance: int
) -> list[list[dict[str, object]]]:
    """Cluster nearby peaks while allowing at most one peak per window size."""

    remaining = list(peaks)
    clusters: list[list[dict[str, object]]] = []
    while remaining:
        seed = max(
            remaining,
            key=lambda item: (
                float(item["score_ratio"]),
                float(item["score"]),
            ),
        )
        remaining.remove(seed)
        cluster = [seed]
        seed_index = int(seed["trace_index"])
        used_windows = {int(seed["window_size"])}
        for window_size in sorted(
            {int(item["window_size"]) for item in remaining}
        ):
            if window_size in used_windows:
                continue
            options = [
                item
                for item in remaining
                if int(item["window_size"]) == window_size
                and abs(int(item["trace_index"]) - seed_index) <= tolerance
            ]
            if not options:
                continue
            chosen = min(
                options,
                key=lambda item: (
                    abs(int(item["trace_index"]) - seed_index),
                    -float(item["score_ratio"]),
                ),
            )
            cluster.append(chosen)
            remaining.remove(chosen)
            used_windows.add(window_size)
        clusters.append(cluster)
    return sorted(
        clusters,
        key=lambda cluster: statistics.median(
            int(item["trace_index"]) for item in cluster
        ),
    )


def write_csv(
    path: Path, rows: Iterable[dict[str, object]], fields: Sequence[str]
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_calendar_consensus(
    candidates: Sequence[dict[str, object]], tolerance_days: int
) -> list[dict[str, object]]:
    """Group candidate rows from different scopes into calendar episodes."""

    ordered = sorted(
        candidates, key=lambda row: _parse_timestamp(str(row["estimated_change_time"]))
    )
    groups: list[list[dict[str, object]]] = []
    for candidate in ordered:
        timestamp = _parse_timestamp(str(candidate["estimated_change_time"]))
        if not groups:
            groups.append([candidate])
            continue
        previous = _parse_timestamp(
            str(groups[-1][-1]["estimated_change_time"])
        )
        if (timestamp - previous).total_seconds() <= tolerance_days * 86400:
            groups[-1].append(candidate)
        else:
            groups.append([candidate])

    consensus_rows: list[dict[str, object]] = []
    for sequence, group in enumerate(groups, start=1):
        strongest = max(group, key=lambda row: float(row["max_score_ratio"]))
        timestamps = sorted(
            _parse_timestamp(str(row["estimated_change_time"])) for row in group
        )
        representative = timestamps[len(timestamps) // 2]
        scopes = sorted({str(row["scope"]) for row in group})
        multiscale = sum(int(row["support_count"]) >= 2 for row in group)
        if len(scopes) >= 2 and multiscale:
            consensus_strength = "cross-scope-multiscale"
        elif len(scopes) >= 2:
            consensus_strength = "cross-scope"
        elif multiscale:
            consensus_strength = "multiscale"
        else:
            consensus_strength = "exploratory"
        consensus_rows.append(
            {
                "dataset": "BPI Challenge 2017",
                "consensus_id": f"CONSENSUS-D{sequence:03d}",
                "representative_time": _iso(representative),
                "representative_year_week": _year_week(representative),
                "earliest_candidate_time": _iso(timestamps[0]),
                "latest_candidate_time": _iso(timestamps[-1]),
                "calendar_span_days": round(
                    (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0, 2
                ),
                "candidate_count": len(group),
                "scope_count": len(scopes),
                "scopes": ";".join(scopes),
                "candidate_ids": ";".join(str(row["candidate_id"]) for row in group),
                "multiscale_candidate_count": multiscale,
                "consensus_strength": consensus_strength,
                "max_score_ratio": max(float(row["max_score_ratio"]) for row in group),
                "strongest_candidate_id": strongest["candidate_id"],
                "representative_localized_edges": strongest["localized_edges"],
                "representative_localized_nodes": strongest["localized_nodes"],
                "ground_truth_available": False,
                "validation_status": "candidate_only",
            }
        )
    return consensus_rows


def analyze_scope(
    scope: str,
    traces: Sequence[TraceRecord],
    window_sizes: Sequence[int],
    step: int,
    threshold_z: float,
    cluster_tolerance: int,
    localization_width: int,
    localization_limit: int,
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    edge_sets = [trace.edges for trace in traces]
    activity_sets = [trace.activities for trace in traces]
    signals: list[dict[str, object]] = []
    peak_records: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []

    for window_size in window_sizes:
        scores = score_windows(edge_sets, window_size, step)
        threshold, score_median, score_mad = robust_threshold(scores, threshold_z)
        peaks = detect_peaks(scores, threshold, min_distance=2 * window_size)
        peak_indices = {peak.trace_index for peak in peaks}
        for point in scores:
            boundary = min(point.trace_index, len(traces) - 1)
            signals.append(
                {
                    "dataset": "BPI Challenge 2017",
                    "scope": scope,
                    "window_size": window_size,
                    "step": step,
                    "scope_trace_index": point.trace_index,
                    "global_trace_index": traces[boundary].global_trace_index,
                    "boundary_case_id": traces[boundary].case_id,
                    "boundary_time": _iso(traces[boundary].start_time),
                    "boundary_year_week": _year_week(traces[boundary].start_time),
                    "jsd_score": round(point.score, 10),
                    "threshold": round(threshold, 10),
                    "score_ratio": round(point.score / threshold, 6)
                    if math.isfinite(threshold) and threshold > 0
                    else "",
                    "is_selected_peak": point.trace_index in peak_indices,
                }
            )
        for peak in peaks:
            peak_records.append(
                {
                    "scope": scope,
                    "window_size": window_size,
                    "trace_index": peak.trace_index,
                    "score": peak.score,
                    "threshold": threshold,
                    "score_ratio": peak.score / threshold
                    if math.isfinite(threshold) and threshold > 0
                    else 0.0,
                }
            )
        summaries.append(
            {
                "dataset": "BPI Challenge 2017",
                "scope": scope,
                "n_traces": len(traces),
                "start_time": _iso(traces[0].start_time),
                "end_time": _iso(traces[-1].start_time),
                "window_size": window_size,
                "step": step,
                "threshold_z": threshold_z,
                "n_score_points": len(scores),
                "score_median": round(score_median, 10),
                "score_mad": round(score_mad, 10),
                "threshold": round(threshold, 10),
                "n_selected_peaks": len(peaks),
            }
        )

    clusters = cluster_multiscale_peaks(peak_records, cluster_tolerance)
    candidates: list[dict[str, object]] = []
    localization_rows: list[dict[str, object]] = []
    total_windows = len(window_sizes)
    scope_prefix = _scope_key(scope)
    for sequence, cluster in enumerate(clusters, start=1):
        indices = [int(item["trace_index"]) for item in cluster]
        representative_index = int(round(statistics.median(indices)))
        representative_index = min(max(representative_index, 0), len(traces) - 1)
        representative_trace = traces[representative_index]
        strongest = max(cluster, key=lambda item: float(item["score_ratio"]))
        strongest_window = int(strongest["window_size"])
        alarm_boundary = min(len(traces), representative_index + strongest_window)
        alarm_trace = traces[max(0, alarm_boundary - 1)]
        support_windows = sorted({int(item["window_size"]) for item in cluster})
        support_count = len(support_windows)
        support_ratio = support_count / total_windows if total_windows else 0.0
        stability = (
            "high"
            if support_ratio >= 0.999
            else "medium"
            if support_ratio >= 0.5
            else "single-scale"
        )
        candidate_id = f"{scope_prefix}-D{sequence:03d}"
        edge_changes = _rate_changes(
            edge_sets,
            representative_index,
            localization_width,
            localization_limit,
        )
        node_changes = _rate_changes(
            activity_sets,
            representative_index,
            localization_width,
            localization_limit,
        )
        candidates.append(
            {
                "dataset": "BPI Challenge 2017",
                "candidate_id": candidate_id,
                "scope": scope,
                "scope_trace_index": representative_index,
                "global_trace_index": representative_trace.global_trace_index,
                "boundary_case_id": representative_trace.case_id,
                "estimated_change_time": _iso(representative_trace.start_time),
                "estimated_change_year_week": _year_week(
                    representative_trace.start_time
                ),
                "alarm_scope_trace_index": alarm_boundary,
                "alarm_time": _iso(alarm_trace.start_time),
                "support_count": support_count,
                "total_window_sizes": total_windows,
                "support_ratio": round(support_ratio, 4),
                "support_windows": ";".join(map(str, support_windows)),
                "stability": stability,
                "strongest_window_size": strongest_window,
                "max_jsd_score": round(float(strongest["score"]), 10),
                "max_score_ratio": round(float(strongest["score_ratio"]), 6),
                "localized_edges": _compact(edge_changes),
                "localized_nodes": _compact(node_changes),
                "ground_truth_available": False,
                "validation_status": "candidate_only",
            }
        )
        for feature_kind, changes in (("edge", edge_changes), ("node", node_changes)):
            for rank, item in enumerate(changes, start=1):
                localization_rows.append(
                    {
                        "dataset": "BPI Challenge 2017",
                        "candidate_id": candidate_id,
                        "scope": scope,
                        "scope_trace_index": representative_index,
                        "estimated_change_time": _iso(
                            representative_trace.start_time
                        ),
                        "feature_kind": feature_kind,
                        "rank": rank,
                        "feature": item["feature"],
                        "before_rate": item["before_rate"],
                        "after_rate": item["after_rate"],
                        "delta": item["delta"],
                        "z_score": item["z_score"],
                        "localization_width": localization_width,
                    }
                )

    robust_count = sum(row["stability"] in {"high", "medium"} for row in candidates)
    for summary in summaries:
        summary["n_candidate_clusters"] = len(candidates)
        summary["n_multiscale_candidates"] = robust_count
    return candidates, signals, localization_rows, summaries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/bpi-challenge-2017/bpi_2017_cleaned.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("results/bpi2017_ostovar")
    )
    parser.add_argument(
        "--window-sizes",
        type=int,
        nargs="+",
        default=[150, 300, 500],
        help="Adjacent trace-window sizes used for multiscale stability checks",
    )
    parser.add_argument("--step", type=int, default=10)
    parser.add_argument("--threshold-z", type=float, default=6.0)
    parser.add_argument("--cluster-tolerance", type=int, default=500)
    parser.add_argument("--consensus-days", type=int, default=14)
    parser.add_argument("--localization-width", type=int, default=300)
    parser.add_argument("--localization-limit", type=int, default=12)
    parser.add_argument(
        "--lifecycle",
        default="complete",
        help="Lifecycle transition to retain; pass ALL to disable filtering",
    )
    parser.add_argument(
        "--global-only",
        action="store_true",
        help="Skip ApplicationType-specific scopes",
    )
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input CSV not found: {args.input}")
    if any(size <= 0 for size in args.window_sizes):
        parser.error("Window sizes must be positive")
    if args.step <= 0:
        parser.error("Step must be positive")
    lifecycle = None if args.lifecycle.upper() == "ALL" else args.lifecycle

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Reading {args.input} ...", flush=True)
    traces, input_diagnostics = read_bpi_traces(args.input, lifecycle=lifecycle)
    if len(traces) < 2 * min(args.window_sizes):
        parser.error("Not enough retained cases for the requested window sizes")
    print(
        f"Retained {len(traces):,} cases and "
        f"{int(input_diagnostics['retained_rows']):,} events",
        flush=True,
    )

    scopes: dict[str, list[TraceRecord]] = {"ALL": traces}
    if not args.global_only:
        application_types = sorted({trace.application_type for trace in traces})
        for application_type in application_types:
            scoped = [
                trace
                for trace in traces
                if trace.application_type == application_type
            ]
            if len(scoped) >= 2 * min(args.window_sizes):
                scopes[application_type] = scoped

    all_candidates: list[dict[str, object]] = []
    all_signals: list[dict[str, object]] = []
    all_localization: list[dict[str, object]] = []
    all_summaries: list[dict[str, object]] = []
    for scope, scoped_traces in scopes.items():
        print(f"Analyzing {scope}: {len(scoped_traces):,} cases", flush=True)
        candidates, signals, localization, summaries = analyze_scope(
            scope=scope,
            traces=scoped_traces,
            window_sizes=sorted(set(args.window_sizes)),
            step=args.step,
            threshold_z=args.threshold_z,
            cluster_tolerance=args.cluster_tolerance,
            localization_width=args.localization_width,
            localization_limit=args.localization_limit,
        )
        all_candidates.extend(candidates)
        all_signals.extend(signals)
        all_localization.extend(localization)
        all_summaries.extend(summaries)

    trace_rows = []
    for trace in traces:
        trace_rows.append(
            {
                "dataset": "BPI Challenge 2017",
                "global_trace_index": trace.global_trace_index,
                "case_id": trace.case_id,
                "application_type": trace.application_type,
                "case_start_time": _iso(trace.start_time),
                "case_start_year_week": _year_week(trace.start_time),
                "case_end_time": _iso(trace.end_time),
                "duration_hours": round(
                    (trace.end_time - trace.start_time).total_seconds() / 3600.0, 4
                ),
                "retained_event_count": trace.event_count,
                "distinct_activity_count": trace.activity_count,
            }
        )

    consensus_rows = build_calendar_consensus(
        all_candidates, tolerance_days=args.consensus_days
    )

    metadata_rows: list[dict[str, object]] = [
        {"key": "dataset", "value": "BPI Challenge 2017"},
        {"key": "input_file", "value": str(args.input)},
        {"key": "method", "value": "DFG occurrence sets + adjacent windows + JSD"},
        {"key": "window_sizes", "value": ";".join(map(str, sorted(set(args.window_sizes))))},
        {"key": "step", "value": args.step},
        {"key": "threshold", "value": "median + z * 1.4826 * MAD with safety floors"},
        {"key": "threshold_z", "value": args.threshold_z},
        {"key": "cluster_tolerance", "value": args.cluster_tolerance},
        {"key": "calendar_consensus_days", "value": args.consensus_days},
        {"key": "localization_width", "value": args.localization_width},
        {"key": "lifecycle_filter", "value": lifecycle or "ALL"},
        {"key": "ground_truth_available", "value": False},
        {
            "key": "interpretation",
            "value": "Rows are exploratory drift candidates, not validated TP/FP labels",
        },
    ]
    for key, value in input_diagnostics.items():
        if key == "lifecycle_counts":
            for transition, count in dict(value).items():
                metadata_rows.append(
                    {"key": f"lifecycle_count:{transition}", "value": count}
                )
        else:
            metadata_rows.append({"key": key, "value": value})

    candidate_fields = [
        "dataset",
        "candidate_id",
        "scope",
        "scope_trace_index",
        "global_trace_index",
        "boundary_case_id",
        "estimated_change_time",
        "estimated_change_year_week",
        "alarm_scope_trace_index",
        "alarm_time",
        "support_count",
        "total_window_sizes",
        "support_ratio",
        "support_windows",
        "stability",
        "strongest_window_size",
        "max_jsd_score",
        "max_score_ratio",
        "localized_edges",
        "localized_nodes",
        "ground_truth_available",
        "validation_status",
    ]
    signal_fields = [
        "dataset",
        "scope",
        "window_size",
        "step",
        "scope_trace_index",
        "global_trace_index",
        "boundary_case_id",
        "boundary_time",
        "boundary_year_week",
        "jsd_score",
        "threshold",
        "score_ratio",
        "is_selected_peak",
    ]
    localization_fields = [
        "dataset",
        "candidate_id",
        "scope",
        "scope_trace_index",
        "estimated_change_time",
        "feature_kind",
        "rank",
        "feature",
        "before_rate",
        "after_rate",
        "delta",
        "z_score",
        "localization_width",
    ]
    summary_fields = [
        "dataset",
        "scope",
        "n_traces",
        "start_time",
        "end_time",
        "window_size",
        "step",
        "threshold_z",
        "n_score_points",
        "score_median",
        "score_mad",
        "threshold",
        "n_selected_peaks",
        "n_candidate_clusters",
        "n_multiscale_candidates",
    ]
    trace_fields = [
        "dataset",
        "global_trace_index",
        "case_id",
        "application_type",
        "case_start_time",
        "case_start_year_week",
        "case_end_time",
        "duration_hours",
        "retained_event_count",
        "distinct_activity_count",
    ]
    consensus_fields = [
        "dataset",
        "consensus_id",
        "representative_time",
        "representative_year_week",
        "earliest_candidate_time",
        "latest_candidate_time",
        "calendar_span_days",
        "candidate_count",
        "scope_count",
        "scopes",
        "candidate_ids",
        "multiscale_candidate_count",
        "consensus_strength",
        "max_score_ratio",
        "strongest_candidate_id",
        "representative_localized_edges",
        "representative_localized_nodes",
        "ground_truth_available",
        "validation_status",
    ]

    write_csv(args.output_dir / "bpi2017_drift_candidates.csv", all_candidates, candidate_fields)
    write_csv(
        args.output_dir / "bpi2017_drift_consensus.csv",
        consensus_rows,
        consensus_fields,
    )
    write_csv(args.output_dir / "bpi2017_drift_signals.csv", all_signals, signal_fields)
    write_csv(
        args.output_dir / "bpi2017_drift_localization.csv",
        all_localization,
        localization_fields,
    )
    write_csv(args.output_dir / "bpi2017_scope_summary.csv", all_summaries, summary_fields)
    write_csv(args.output_dir / "bpi2017_trace_index.csv", trace_rows, trace_fields)
    write_csv(args.output_dir / "bpi2017_run_metadata.csv", metadata_rows, ["key", "value"])
    print(
        f"Wrote {len(all_candidates)} candidate rows in "
        f"{len(consensus_rows)} calendar consensus groups, "
        f"{len(all_signals)} signal rows, and {len(all_localization)} "
        f"localization rows to {args.output_dir}",
        flush=True,
    )


if __name__ == "__main__":
    main()
