# Ostovar benchmark table

This folder implements the corrected evaluation roadmap for the 75 included
Ostovar logs.  The published dataset description specifies **two sudden drift
points at trace indices 900 and 1900** and noise levels of **0%, 2.5%, and 5%**.

## Method

1. Parse traces in XES document order and represent each trace by the set of
   directly-follows edges it contains (including synthetic start/end edges).
2. At every 10 traces, compare the edge distributions of two adjacent windows
   of 150 traces using Jensen-Shannon divergence.
3. Select local maxima above a robust, per-log threshold
   `median + 6 * 1.4826 * MAD`, with non-maximum suppression over 300 traces.
   Ground truth is not consulted during detection.
4. Match detected and actual points one-to-one within ±200 traces.  Unmatched
   actual points are FN; unmatched detections are FP.
5. For every detection, localize change using statistically large differences
   in edge/activity occurrence rates across 200 traces before and after it.

The CSV is deliberately normalized to one row per actual drift or unmatched
detection.  This supports correct precision, recall, F1, and lag calculations;
putting several drift points into one cell makes those metrics ambiguous.

`detected_trace` is the estimated change-point location. `estimation_error`
compares that estimate with ground truth. Because the method needs the complete
right-hand window, `alarm_trace = detected_trace + window_size`; only the
separate `detection_lag` column represents online-style reporting latency.

## Run

```powershell
python benchmark/ostovar_benchmark.py
python -m unittest discover -s benchmark -p "test_*.py"
```

Outputs are written to `benchmark/results/`:

- `ground_truth.csv`: auditable ground-truth mapping (150 rows for 75 logs).
- `benchmark_table.csv`: TP/FN/FP rows, lag, score, and compact localization.
- `summary.csv`: metrics by process-change level and noise level, plus overall.
- `localization_details.json`: full before/after rates for localized edges/nodes.
- `detection_diagnostics.json`: threshold and complete score curve per log.

The localization columns are model explanations, not localization-accuracy
scores: the included files do not contain authoritative changed-edge labels.
Such labels would need the original before/after process models or generator
configuration before localization precision/recall can be reported.
