# 📊 Báo Cáo Phân Tích Sơ Bộ & Hướng Phát Triển Dataset Ostovar

**Dự án:** Đánh giá & Benchmark Thuật toán Concept Drift Detection trong Process Mining
**Ngày tạo:** Tháng 08/2026

---

## 1. Tổng Quan Về Dataset Ostovar

Bộ dataset Ostovar là tập hợp gồm **75 event logs** dạng dữ liệu tổng hợp (synthetic data), được sinh ra từ công cụ PLG2. Mục đích chính của bộ dữ liệu này là để làm **Benchmark (thước đo chuẩn)** cho các thuật toán phát hiện Concept Drift (Concept Drift Detection) trong lĩnh vực Process Mining.

**Cấu trúc dữ liệu:**
Dữ liệu được thiết kế có chủ đích với các điểm drift đã biết trước (Ground Truth), được chia thành các đặc tính:
*   **Tổng số file:** 75 file định dạng `.xes.gz`
*   **3 Cấp độ Drift (Drift Levels):**
    *   **Atomic (13 loại):** Các thay đổi đơn lẻ, cơ bản ở mức độ từng hoạt động (thêm, xóa, đổi chỗ).
    *   **Composite (6 loại):** Sự kết hợp của nhiều thay đổi Atomic hoặc thay đổi một cụm luồng quy trình (ví dụ: IOR).
    *   **Nested (6 loại):** Thay đổi xảy ra ở các quy trình con (sub-processes) lồng ghép bên trong, luồng chính bên ngoài vẫn giữ nguyên.
*   **3 Mức độ Nhiễu (Noise Levels):**
    *   `_0` (Baseline): Dữ liệu sạch 100%, không nhiễu.
    *   `_2`: Chứa 2,5% nhiễu ngẫu nhiên (hậu tố tên file được rút gọn thành `_2`).
    *   `_5`: Chứa 5% nhiễu ngẫu nhiên để kiểm tra tính bền vững (robustness) của mô hình chống lại cảnh báo giả (False Positives).

---

## 2. Những Công Việc Đã Thực Hiện (Tiến Độ Hiện Tại)

Chúng ta đã hoàn thành giai đoạn **Khám phá Dữ liệu (EDA - Exploratory Data Analysis)** sơ bộ, xây dựng nền tảng vững chắc để chuyển sang bước chạy mô hình. Cụ thể:

1.  **Xây dựng File Jupyter Notebook (`eda_75logs.ipynb`):**
    *   Tự động parse và phân loại 75 file logs thành một Catalog có cấu trúc (`ostovar_catalog_full.csv`).
    *   Xây dựng hàm `extract_log_stats()` để đọc song song và trích xuất các KPI quan trọng (số lượng traces, events, activities, độ dài trung bình trace) mà không làm quá tải RAM.
2.  **Phân tích & Trực quan hóa Đặc tính:**
    *   So sánh trực quan (Heatmap, Boxplot) kích thước log và sự khác biệt giữa các cấp độ Atomic, Composite, Nested.
    *   Phân tích sự tác động của mức độ nhiễu (Noise 2%, 5%) làm thay đổi đặc tính độ dài trung bình của trace như thế nào.
3.  **Deep-dive Phân tích Cấu trúc (Trace Variants):**
    *   Bóc tách một log đại diện để tìm quy luật phân bố (Pareto Chart), xác định các Variants cốt lõi chiếm 80% luồng quy trình.
    *   Xử lý lỗi kỹ thuật liên quan đến cấu trúc tuple của thư viện `pm4py`.

---

## 3. Hướng Phát Triển & Roadmap Xây Dựng Bảng Đánh Giá (Benchmark)

Mục tiêu tiếp theo là xây dựng một **Bảng Đánh Giá Mô Hình (Benchmark Table)** bao gồm các tiêu chí: *Thời điểm xảy ra Drift, Vị trí thay đổi (Cạnh nào), Loại thay đổi, và Nguyên nhân*.

Để đạt được bảng này, đây là **Roadmap 4 Bước** triển khai kỹ thuật:

### Bước 1: Xây dựng & Trích xuất "Đáp Án Chuẩn" (Ground Truth)
Vì Ostovar là dữ liệu tổng hợp, thời điểm xảy ra Drift (Drift point) đã được tác giả cấu hình sẵn. Tài liệu mô tả bộ dữ liệu xác nhận mỗi log có **hai sudden drift tại trace index 900 và 1900**, không phải một drift ở giữa log.
*   **Hành động:** Tạo `ground_truth.csv` với hai dòng ground truth cho mỗi log, ghi rõ nguồn và quy ước trace index. Không suy diễn ground truth từ chính tín hiệu cần đánh giá.
*   **Mục đích:** Dùng làm mốc (Baseline) để tính toán độ chính xác của mô hình sau này.

### Bước 2: Thiết lập Thuật Toán Phát Hiện (Drift Detection)
Cần lựa chọn và cài đặt một thuật toán thống kê hoặc học máy để tìm ra **"Thời điểm xảy ra"**.
*   **Phương pháp đề xuất:** Sử dụng kỹ thuật Cửa sổ trượt (Sliding Window) trích xuất đặc trưng (Feature Extraction) dựa trên Directly-Follows Graph (DFG) hoặc Run Length Encoding.
*   **Thuật toán thống kê áp dụng:** Sử dụng các kiểm định thống kê như **ADWIN** (Adaptive Windowing) hoặc **CUSUM** để phát hiện sự thay đổi phân phối dữ liệu đột ngột giữa các cửa sổ.

### Bước 3: Định Vị Sự Thay Đổi (Drift Localization)
Sau khi thuật toán báo có Drift tại vết thứ `N`. Chúng ta cần trả lời câu hỏi: **"Thay đổi ở cạnh nào / Perspective nào?"**
*   **Hành động:** 
    *   Chia Event Log thành 2 phần: Khúc trước Drift (`Log 1`) và Khúc sau Drift (`Log 2`).
    *   Chạy thuật toán Process Discovery (như *Inductive Miner*) để tạo ra mô hình cho `Log 1` và `Log 2`.
    *   So sánh sự khác biệt về topo đồ thị giữa 2 mô hình để tìm ra các cạnh (edges) hoặc node (activities) bị biến mất hoặc mới xuất hiện.

### Bước 4: Chạy Đánh Giá & Điền Bảng Kết Quả
Áp dụng toàn bộ quy trình trên cho 75 logs Ostovar và sau đó là các dataset khác (CDLG, BPI 2017).

**Khung Bảng Đánh Giá Dự Kiến:**

| Tên Log (Dataset) | Thời điểm Drift Thực Tế (Ground Truth) | Thời điểm Phát Hiện (Detected) | Độ Trễ (Detection Lag) | Thay đổi ở cạnh/node nào? (Localization) | Loại thay đổi (Type) | Nguyên nhân |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Atomic_ConditionalMove_0` | Trace 900 | Trace 950 (alarm tại 1100) | +200 traces | Xem các cạnh có chênh lệch tần suất lớn nhất | Sudden (Đột ngột) | Thay đổi mô hình tổng hợp |
| `Atomic_Loop_5` | Trace 900 | Không phát hiện (FN) | N/A | N/A | Sudden | Thay đổi mô hình tổng hợp |
| `BPI_2017_Log` | N/A (Dữ liệu thực) | Tuần 25 | N/A | Cạnh O_Returned -> O_Accepted | Gradual (Từ từ) | Nút thắt hiệu suất (Bottleneck) |

> [!TIP]
> **Khuyến nghị kỹ thuật:**
> Nên bắt đầu thử nghiệm (Prototyping) Bước 2 và Bước 3 trên một file `Atomic_0` (không nhiễu, đơn giản nhất) trước khi chạy pipeline hàng loạt (batch run) cho toàn bộ 75 files. Hướng tiếp cận này giúp dễ debug thuật toán hơn.

---

## 4. Đánh Giá Roadmap & Kết Quả Triển Khai

Roadmap hợp lý về thứ tự tổng quát (ground truth → detection → localization → evaluation), nhưng cần các điều chỉnh sau để kết quả có giá trị benchmark:

1. **Ground truth:** dùng hai mốc 900 và 1900 cho mỗi log; không giả định mốc giữa log.
2. **Noise:** chuẩn hóa ba mức thành 0%, 2,5% và 5%.
3. **Detection và evaluation phải tách biệt:** thuật toán phát hiện không được đọc ground truth. Ground truth chỉ được dùng sau đó để ghép one-to-one trong sai số cho phép (±200 trace).
4. **Cấu trúc bảng:** một dòng cho mỗi ground-truth drift hoặc false positive chưa ghép, với nhãn TP/FN/FP. Cách này cho phép tính Precision, Recall, F1 và lag đúng nghĩa.
5. **Localization:** so sánh tần suất xuất hiện cạnh DFG/node trong cửa sổ trước và sau điểm phát hiện. Không dùng Inductive Miner ở bản đầu vì discovery có thể tạo thêm sai số và làm mất các thay đổi tần suất. Các cột localization hiện là lời giải thích, chưa phải accuracy vì repo không có nhãn chuẩn về cạnh/node đã thay đổi.
6. **Dữ liệu thực:** không trộn BPI 2017 vào accuracy benchmark khi chưa có ground truth đầy đủ; chỉ nên báo cáo như exploratory case study.
7. **Độ trễ:** tách `detected_trace` (ước lượng vị trí change point) khỏi `alarm_trace` (thời điểm đã quan sát đủ cửa sổ sau). `detection_lag` được tính từ alarm, còn sai số định vị được lưu riêng trong `estimation_error`.

Pipeline đã được cài đặt tại `benchmark/ostovar_benchmark.py`, dùng hai cửa sổ DFG 150 trace, bước nhảy 10, Jensen–Shannon divergence, ngưỡng robust theo median/MAD và non-maximum suppression. Kết quả mặc định trên 75 log:

| Phạm vi | TP | FP | FN | Precision | Recall | F1 | Median estimation error | Median detection lag |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Toàn bộ | 145 | 0 | 5 | 1,0000 | 0,9667 | 0,9831 | 50 traces | 200 traces |

Năm false negative đều nằm ở `Atomic_Loop` hoặc `Atomic_Skip` có nhiễu 2,5%/5%; toàn bộ nhóm Composite và Nested đạt recall 1,0 ở cả ba mức noise. Kết quả chi tiết nằm trong `benchmark/results/benchmark_table.csv`; hướng dẫn và giới hạn phương pháp nằm trong `benchmark/README.md`.
