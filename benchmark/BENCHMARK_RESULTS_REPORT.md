# 📊 Báo Cáo Giải Thích Kết Quả Benchmark — Phát Hiện Concept Drift Trên 75 Logs Ostovar

**Dự án:** Benchmark Concept Drift Detection — Bộ dữ liệu Ostovar
**Ngày chạy:** Tháng 08/2026
**Script:** `benchmark/ostovar_benchmark.py`

---

## 1. Tổng Quan Phương Pháp

### 1.1. Mục tiêu
Đánh giá khả năng **phát hiện tự động** các điểm thay đổi quy trình (Concept Drift) trong 75 event logs tổng hợp, sử dụng phương pháp cửa sổ trượt (Sliding Window) kết hợp khoảng cách Jensen–Shannon Divergence trên Directly-Follows Graph (DFG).

### 1.2. Tham số thuật toán

| Tham số | Giá trị mặc định | Ý nghĩa |
| :--- | ---: | :--- |
| `window_size` | 150 | Số lượng trace trong mỗi cửa sổ so sánh. Cửa sổ trái (trước) và cửa sổ phải (sau) mỗi cửa sổ 150 trace |
| `step` | 10 | Bước nhảy: cứ 10 trace thì tính lại một lần |
| `threshold_z` | 6.0 | Hệ số nhân MAD để xác định ngưỡng bất thường. Ngưỡng = median + 6 × 1.4826 × MAD |
| `tolerance` | 200 | Sai số cho phép (traces) khi khớp điểm phát hiện với ground truth. Nếu lệch ≤ 200 trace thì coi là khớp đúng |
| `localization_width` | 200 | Số trace trước/sau điểm phát hiện dùng để so sánh tần suất cạnh/node |
| `localization_limit` | 8 | Số lượng cạnh/node thay đổi lớn nhất được ghi lại cho mỗi điểm drift |

### 1.3. Quy trình xử lý

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Đọc file XES    │────▶│  Trích xuất DFG  │────▶│  Tính JSD giữa   │
│  (gzip)          │     │  edges per trace  │     │  2 cửa sổ trượt  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                          │
                         ┌──────────────────┐             ▼
                         │  Khớp 1-1 với    │◀────┌──────────────────┐
                         │  Ground Truth    │     │  Tìm đỉnh vượt  │
                         │  (DP matching)   │     │  ngưỡng robust   │
                         └──────────────────┘     └──────────────────┘
                                │
                                ▼
                         ┌──────────────────┐
                         │  Gán TP/FP/FN    │
                         │  + Localization  │
                         └──────────────────┘
```

> **Lưu ý quan trọng:** Thuật toán phát hiện KHÔNG được xem Ground Truth trong quá trình dò tìm. Ground Truth chỉ được dùng SAU KHI phát hiện xong, để đánh giá kết quả (tính TP, FP, FN).

---

## 2. Giải Thích Các File Output

### 2.1. `ground_truth.csv` — Đáp án chuẩn

File này chứa danh sách tất cả các điểm drift đã biết trước (do tác giả dataset thiết kế). Mỗi log có đúng **2 điểm drift** tại trace 900 và 1900.

| Trường | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- |
| `filename` | Tên file log gốc | `Atomic_ConditionalMove_output_ConditionalMove.xes.gz` |
| `level` | Cấp độ phức tạp của drift | `Atomic` / `Composite` / `Nested` |
| `change_pattern` | Loại thay đổi cụ thể trong quy trình | `ConditionalMove`, `Skip`, `IOR`, v.v. |
| `noise_pct` | Tỷ lệ nhiễu ngẫu nhiên (%) | `0.0` (sạch), `2.5`, `5.0` |
| `drift_sequence` | Thứ tự drift trong log (1 = drift đầu, 2 = drift sau) | `1` hoặc `2` |
| `ground_truth_trace` | Chỉ số trace mà drift thực sự xảy ra | `900` hoặc `1900` |
| `drift_nature` | Bản chất của drift | `Sudden` (đột ngột — luôn là Sudden trong bộ Ostovar) |

**Cách hiểu:** Mỗi log ~2999 traces được chia thành 3 giai đoạn:
- Trace 0–899: Chạy theo **Model A** (quy trình gốc)
- Trace 900–1899: Chạy theo **Model B** (quy trình đã thay đổi)
- Trace 1900–2998: Quay lại **Model A** (quy trình gốc)

---

### 2.2. `benchmark_table.csv` — Bảng kết quả chi tiết

Đây là bảng chính, mỗi dòng tương ứng với một **điểm drift thực tế (ground truth)** hoặc một **cảnh báo giả (false positive)** chưa khớp được.

| Trường | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- |
| `filename` | Tên file log | `Atomic_Loop_output_Loop_5.xes.gz` |
| `level` | Cấp độ drift: Atomic / Composite / Nested | `Atomic` |
| `change_pattern` | Loại thay đổi quy trình | `Loop` |
| `noise_pct` | Tỷ lệ nhiễu (%) | `5.0` |
| `n_traces` | Tổng số trace trong log | `2999` |
| `ground_truth_trace` | Trace thực sự xảy ra drift (đáp án) | `900` (trống nếu FP) |
| `detected_trace` | Trace mà thuật toán **ước lượng** là điểm thay đổi | `950` (trống nếu FN) |
| `estimation_error` | Sai số ước lượng = `detected_trace − ground_truth_trace` | `50` (thuật toán phát hiện trễ 50 trace) |
| `alarm_trace` | Trace mà hệ thống có đủ dữ liệu để **đưa ra cảnh báo** = `detected_trace + window_size` | `1100` |
| `detection_lag` | Độ trễ báo cáo = `alarm_trace − ground_truth_trace`. Đây là thời gian chờ từ khi drift xảy ra đến khi hệ thống có thể thông báo | `200` |
| `outcome` | Kết quả đánh giá | **TP** = Phát hiện đúng, **FN** = Bỏ sót, **FP** = Cảnh báo giả |
| `detection_score` | Điểm Jensen-Shannon tại đỉnh phát hiện. Giá trị càng cao = sự khác biệt giữa 2 cửa sổ càng lớn | `0.05398099` |
| `threshold` | Ngưỡng robust cho log này. Score phải vượt ngưỡng mới được coi là drift | `0.0151651` |
| `localized_edges` | Các **cạnh DFG** có tần suất thay đổi mạnh nhất trước/sau điểm drift. Dạng `cạnh (±delta)` | `o1->o2 (+0.945); o10->o11 (-0.445)` |
| `localized_nodes` | Các **activity (node)** có tần suất xuất hiện thay đổi mạnh nhất | `p7 (-0.500); p1 (-0.500)` |
| `drift_nature` | Bản chất drift | `Sudden` |
| `cause` | Nguyên nhân drift | `Synthetic process-model change` |

#### Cách đọc `localized_edges` và `localized_nodes`:

- **`o1->o2 (+0.945)`**: Cạnh từ activity `o1` đến activity `o2` tăng tần suất xuất hiện 94.5% (gần như không có trước drift, xuất hiện gần 100% sau drift).
- **`p7 (-0.500)`**: Activity `p7` giảm tần suất xuất hiện 50% (từ ~97% xuống ~47% hoặc biến mất hoàn toàn).
- **Delta dương (+)**: Cạnh/node này **MỚI XUẤT HIỆN** hoặc tần suất **TĂNG** sau drift.
- **Delta âm (−)**: Cạnh/node này **BIẾN MẤT** hoặc tần suất **GIẢM** sau drift.

#### Phân biệt `detected_trace`, `alarm_trace`, và `detection_lag`:

```
                    detected_trace          alarm_trace
                         │                      │
     ◄── cửa sổ trái ──►│◄── cửa sổ phải ──►  │
                         │                      │
  ─────────────────────────────────────────────────────── trace index
  0          ground_truth=900   950              1100
                    │           │                │
                    │           │◄─── detection_lag = 200 ───►│
                    │◄── estimation_error = 50 ──►│
```

- **`detected_trace = 950`**: Thuật toán ước tính rằng sự thay đổi xảy ra tại trace 950.
- **`estimation_error = 50`**: Sai lệch so với đáp án thực (900). Thuật toán đoán trễ 50 trace.
- **`alarm_trace = 1100`**: Nhưng vì cần đọc thêm 150 trace bên phải (window_size) để xác nhận, nên hệ thống chỉ có thể đưa ra cảnh báo sau khi đã xử lý tới trace 1100.
- **`detection_lag = 200`**: Từ lúc drift thực sự xảy ra (trace 900) đến lúc có cảnh báo (trace 1100) = 200 traces. Đây là "thời gian phản ứng" thực tế của hệ thống.

---

### 2.3. `summary.csv` — Bảng tổng hợp hiệu năng

Tổng hợp kết quả theo nhóm `(level × noise_pct)` và tổng thể (ALL).

| Trường | Ý nghĩa | Giải thích chi tiết |
| :--- | :--- | :--- |
| `level` | Nhóm đánh giá | `Atomic` / `Composite` / `Nested` / `ALL` |
| `noise_pct` | Mức nhiễu | `0.0` / `2.5` / `5.0` / `ALL` |
| `tp` | **True Positive** — Số điểm drift phát hiện đúng | Thuật toán báo có drift VÀ đúng khớp với ground truth (trong sai số ±200 trace) |
| `fp` | **False Positive** — Số cảnh báo giả | Thuật toán báo có drift NHƯNG không khớp với bất kỳ ground truth nào |
| `fn` | **False Negative** — Số điểm drift bị bỏ sót | Có drift thật (theo ground truth) NHƯNG thuật toán không phát hiện được |
| `precision` | **Độ chính xác** = TP / (TP + FP) | Trong tất cả các lần báo cáo drift, bao nhiêu % là đúng? |
| `recall` | **Độ bao phủ / Khả năng thu hồi** = TP / (TP + FN) | Trong tất cả các drift thật, thuật toán tìm được bao nhiêu %? |
| `f1` | **F1-Score** = 2 × Precision × Recall / (Precision + Recall) | Điểm cân bằng giữa Precision và Recall. Giá trị tối đa = 1.0 |
| `mean_absolute_estimation_error` | Sai số ước lượng trung bình (traces) | Trung bình thuật toán đoán lệch bao xa so với ground truth |
| `median_absolute_estimation_error` | Trung vị sai số ước lượng (traces) | Giá trị giữa, ít bị ảnh hưởng bởi outliers |
| `mean_detection_lag` | Độ trễ phát hiện trung bình (traces) | Trung bình bao lâu kể từ drift thật đến khi hệ thống đưa ra cảnh báo |
| `median_detection_lag` | Trung vị độ trễ phát hiện (traces) | Giá trị giữa của detection lag |

---

### 2.4. `localization_details.json` — Chi tiết định vị thay đổi

File JSON chứa dữ liệu chi tiết về từng cạnh/node bị thay đổi tại mỗi điểm drift được phát hiện.

**Cấu trúc mỗi phần tử trong mảng:**
```json
{
  "filename": "Tên file log",
  "level": "Atomic",
  "change_pattern": "ConditionalMove",
  "noise_pct": 0.0,
  "n_traces": 2999,
  "drift_nature": "Sudden",
  "cause": "Synthetic process-model change",
  "ground_truth_trace": 900,
  "detected_trace": 950,
  "edges": [
    {
      "feature": "o1->o2",
      "before_rate": 0.05,
      "after_rate": 0.995,
      "delta": 0.945,
      "z_score": 18.919
    }
  ],
  "nodes": [
    {
      "feature": "p7",
      "before_rate": 0.97,
      "after_rate": 0.47,
      "delta": -0.5,
      "z_score": 11.136
    }
  ]
}
```

| Trường con | Ý nghĩa |
| :--- | :--- |
| `feature` | Tên cạnh DFG (dạng `A->B`) hoặc tên activity (node) |
| `before_rate` | Tỷ lệ trace chứa feature này **TRƯỚC** điểm drift (0.0 → 1.0) |
| `after_rate` | Tỷ lệ trace chứa feature này **SAU** điểm drift (0.0 → 1.0) |
| `delta` | Mức thay đổi = `after_rate − before_rate`. Dương = tăng, Âm = giảm |
| `z_score` | Điểm Z thống kê. Giá trị ≥ 3.0 = thay đổi có ý nghĩa thống kê (p < 0.003) |

---

### 2.5. `detection_diagnostics.json` — Dữ liệu chuẩn đoán

File JSON chứa toàn bộ chuỗi điểm số JSD theo từng bước cho mỗi log. Dùng để vẽ biểu đồ tín hiệu (signal plot) nếu cần.

| Trường | Ý nghĩa |
| :--- | :--- |
| `score_median` | Trung vị điểm JSD trong toàn log. Thể hiện mức độ "dao động nền" bình thường |
| `score_mad` | Median Absolute Deviation. Thể hiện mức biến thiên của dao động nền |
| `threshold` | Ngưỡng phát hiện = `median + 6 × 1.4826 × MAD`. Chỉ các đỉnh vượt ngưỡng mới là drift |
| `detected_points` | Danh sách các trace index nơi thuật toán phát hiện drift |
| `scores` | Mảng toàn bộ điểm số `{trace_index, score}` dọc theo log — dùng để vẽ biểu đồ |

---

## 3. Kết Quả Tổng Hợp

### 3.1. Bảng tổng kết theo nhóm

| Phạm vi | Noise | TP | FP | FN | Precision | Recall | F1 | Median Sai Số (traces) | Median Lag (traces) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Atomic** | 0% | 26 | 0 | 0 | 1.0 | 1.0 | 1.0 | 50 | 200 |
| **Atomic** | 2.5% | 23 | 0 | 3 | 1.0 | 0.885 | 0.939 | 50 | 200 |
| **Atomic** | 5% | 24 | 0 | 2 | 1.0 | 0.923 | 0.960 | 50 | 200 |
| **Composite** | 0% | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 | 40 | 190 |
| **Composite** | 2.5% | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 | 40 | 190 |
| **Composite** | 5% | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 | 45 | 195 |
| **Nested** | 0% | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 | 40 | 190 |
| **Nested** | 2.5% | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 | 40 | 190 |
| **Nested** | 5% | 12 | 0 | 0 | 1.0 | 1.0 | 1.0 | 40 | 190 |
| **TỔNG THỂ** | ALL | **145** | **0** | **5** | **1.0** | **0.967** | **0.983** | **50** | **200** |

### 3.2. Giải thích kết quả

#### ✅ Điểm mạnh
- **Precision = 1.0 (hoàn hảo):** Thuật toán không bao giờ đưa ra cảnh báo giả (0 False Positive). Mọi lần nó nói "có drift" thì đều đúng. Đây là ưu điểm rất quan trọng trong thực tế — người dùng có thể tin tưởng hoàn toàn vào mỗi cảnh báo.
- **Composite & Nested đạt Recall 1.0:** Tất cả 72/72 điểm drift ở 2 nhóm này đều được phát hiện đúng, kể cả khi có nhiễu 5%. Composite tạo tín hiệu mạnh (thay đổi nhiều cạnh cùng lúc), Nested dù thay đổi sâu nhưng vẫn tạo đủ sự khác biệt trên DFG.

#### ⚠️ Điểm yếu — 5 False Negatives
Tất cả 5 trường hợp bỏ sót đều thuộc nhóm **Atomic** có nhiễu:

| File Log | Ground Truth | Lý do bỏ sót |
| :--- | :--- | :--- |
| `Atomic_Loop_2.xes.gz` | Trace 900 | Thay đổi kiểu Loop chỉ thêm một cạnh lặp. Nhiễu 2.5% làm mờ tín hiệu |
| `Atomic_Loop_5.xes.gz` | Trace 900 | Tương tự, nhiễu 5% làm cạnh lặp bị chìm hoàn toàn |
| `Atomic_Loop_5.xes.gz` | Trace 1900 | Cả 2 drift của Loop_5 đều bị bỏ sót |
| `Atomic_Skip_2.xes.gz` | Trace 900 | Skip chỉ bỏ qua 1 activity. Nhiễu 2.5% tạo tín hiệu tương đương |
| `Atomic_Skip_2.xes.gz` | Trace 1900 | Cả 2 drift của Skip_2 đều bị bỏ sót |

**Phân tích:** `Loop` và `Skip` là 2 loại thay đổi nhỏ nhất trong nhóm Atomic — chúng chỉ ảnh hưởng đến 1 cạnh duy nhất trong DFG. Khi nhiễu ngẫu nhiên tạo ra các cạnh giả với tần suất tương đương, tín hiệu drift bị chìm dưới ngưỡng phát hiện.

---

## 4. Ý Nghĩa Các Loại Change Pattern (Drift Type)

### Nhóm Atomic (13 loại — Thay đổi đơn lẻ)

| Change Pattern | Ý nghĩa tiếng Việt | Mô tả |
| :--- | :--- | :--- |
| `ConditionalMove` | Di chuyển nhánh điều kiện | Một nhánh `if-then` bị di chuyển sang vị trí khác trong quy trình |
| `ConditionalRemoval` | Xóa nhánh điều kiện | Một nhánh `if-then` bị loại bỏ hoàn toàn |
| `ConditionalToSequence` | Chuyển điều kiện thành tuần tự | Nhánh song song/điều kiện bị chuyển thành thực hiện tuần tự bắt buộc |
| `Frequency` | Thay đổi tần suất | Tần suất thực hiện một nhánh thay đổi (ví dụ: nhánh A từ 70% xuống 30%) |
| `Loop` | Thêm/bớt vòng lặp | Một vòng lặp (loop-back) được thêm vào hoặc loại bỏ |
| `ParallelMove` | Di chuyển nhánh song song | Một nhánh parallel bị di chuyển vị trí |
| `ParallelRemoval` | Xóa nhánh song song | Một nhánh trong cấu trúc song song (AND-split) bị loại bỏ |
| `ParallelToSequence` | Chuyển song song thành tuần tự | Các bước làm đồng thời bị bắt buộc làm lần lượt |
| `SerialMove` | Di chuyển bước tuần tự | Một bước trong chuỗi tuần tự bị di chuyển vị trí |
| `SerialRemoval` | Xóa bước tuần tự | Một bước trong chuỗi tuần tự bị loại bỏ |
| `Skip` | Bỏ qua bước | Một bước trở thành tùy chọn (có thể bỏ qua) |
| `Substitute` | Thay thế bước | Một hoặc nhiều activity bị thay thế bằng activity khác |
| `Swap` | Hoán đổi bước | Hai bước bị hoán đổi thứ tự thực hiện |

### Nhóm Composite (6 loại — Thay đổi phức hợp)

| Change Pattern | Ý nghĩa | Mô tả |
| :--- | :--- | :--- |
| `IOR` | Insert → Optional → Remove | Thêm nhánh mới, biến nhánh cũ thành tùy chọn, rồi xóa nhánh cũ |
| `IRO` | Insert → Remove → Optional | Thêm nhánh mới, xóa nhánh cũ, biến phần khác thành tùy chọn |
| `OIR` | Optional → Insert → Remove | Biến thành tùy chọn trước, rồi thêm mới, rồi xóa |
| `ORI` | Optional → Remove → Insert | Biến thành tùy chọn, xóa bỏ, rồi thêm mới |
| `RIO` | Remove → Insert → Optional | Xóa trước, thêm mới, rồi biến thành tùy chọn |
| `ROI` | Remove → Optional → Insert | Xóa trước, biến thành tùy chọn, rồi thêm mới |

### Nhóm Nested (6 loại — Thay đổi lồng ghép)
Cùng 6 pattern như Composite (IOR, IRO, OIR, ORI, RIO, ROI), nhưng thay đổi xảy ra **bên trong một sub-process** lồng ghép, luồng chính bên ngoài giữ nguyên.

---

## 5. Giới Hạn Của Phương Pháp

1. **Localization chỉ mang tính giải thích:** Các cột `localized_edges` và `localized_nodes` cho biết "cái gì thay đổi nhiều nhất", nhưng chưa có nhãn chuẩn (ground truth) về cạnh/node nào đúng là bị thay đổi theo thiết kế. Do đó không thể tính Localization Precision/Recall.

2. **Chỉ phát hiện Sudden Drift:** Thuật toán hiện tại được tối ưu cho Sudden Drift (thay đổi đột ngột). Với Gradual Drift (thay đổi từ từ) hoặc Recurring Drift (thay đổi lặp lại theo chu kỳ), cần điều chỉnh cách tính ngưỡng.

3. **Detection Lag phụ thuộc window_size:** Với window_size = 150, độ trễ tối thiểu lý thuyết là 150 traces. Giảm window_size sẽ giảm lag nhưng tăng nguy cơ False Positive.

4. **Dữ liệu tổng hợp:** Kết quả F1 = 0.983 là trên dữ liệu synthetic. Hiệu năng trên dữ liệu thực (BPI 2017, CDLG) có thể khác do nhiễu phức tạp hơn và drift có thể không phải Sudden.

---

## 6. Danh Sách File Output

| File | Đường dẫn | Mô tả |
| :--- | :--- | :--- |
| Ground Truth | `benchmark/results/ground_truth.csv` | Đáp án chuẩn: 150 dòng (75 logs × 2 drift points) |
| Benchmark Table | `benchmark/results/benchmark_table.csv` | Kết quả chi tiết: mỗi dòng là 1 TP, FN hoặc FP |
| Summary | `benchmark/results/summary.csv` | Tổng hợp Precision/Recall/F1 theo nhóm |
| Localization | `benchmark/results/localization_details.json` | Chi tiết tần suất before/after cho từng cạnh/node |
| Diagnostics | `benchmark/results/detection_diagnostics.json` | Toàn bộ chuỗi điểm JSD + ngưỡng cho mỗi log |
