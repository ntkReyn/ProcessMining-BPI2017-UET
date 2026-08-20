# Đánh giá Ostovar 75 logs và áp dụng cho BPI Challenge 2017

## 1. Kết luận

Logic Ostovar trong repository **áp dụng được cho BPI Challenge 2017 ở vai trò phát hiện thăm dò (exploratory drift detection)**:

- Biểu diễn mỗi case bằng tập cạnh Directly-Follows Graph (DFG).
- So sánh hai cửa sổ case liền kề bằng Jensen–Shannon divergence (JSD).
- Dùng ngưỡng robust theo median/MAD để chọn đỉnh bất thường.
- Định vị thay đổi bằng chênh lệch tỷ lệ xuất hiện của cạnh và activity trước/sau điểm phát hiện.

Tuy nhiên, BPI 2017 không có ground truth drift đầy đủ. Vì vậy kết quả BPI chỉ được ghi là `candidate_only`, không được gắn nhãn TP/FP/FN và không được dùng để tuyên bố precision/recall/F1.

## 2. Đánh giá kết quả Ostovar 75 logs

### Kết quả mặc định

| Phạm vi | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Toàn bộ 75 logs | 145 | 0 | 5 | 1,0000 | 0,9667 | 0,9831 |

- Median sai số định vị change point: **50 traces**.
- Median độ trễ báo động theo cửa sổ: **200 traces**.
- Composite và Nested đạt recall 1,0 ở cả ba mức noise.
- Năm FN đều thuộc nhóm Atomic: `Loop` (3 FN) và `Skip` (2 FN), chỉ xuất hiện ở noise 2,5% hoặc 5%.

### Kiểm tra độ nhạy

Kết quả từ score cache, với cùng cửa sổ 150 và non-maximum suppression 300 traces:

| z ngưỡng | Tolerance | TP | FP | FN | F1 |
|---:|---:|---:|---:|---:|---:|
| 4 | 100 | 150 | 0 | 0 | 1,0000 |
| 5 | 100 | 149 | 0 | 1 | 0,9967 |
| 6 (mặc định) | 100 | 145 | 0 | 5 | 0,9831 |
| 7 | 100 | 142 | 0 | 8 | 0,9726 |
| 8 | 100 | 137 | 0 | 13 | 0,9547 |

Ở cấu hình mặc định, tolerance 100, 150 và 200 cho kết quả giống nhau. Do đó F1 0,9831 không đến từ việc riêng tolerance 200 ghép thêm detection xa; nó chủ yếu phản ánh detector bảo thủ ở `z=6`. Tuy vậy, kết quả thay đổi theo ngưỡng nên chưa đủ để khẳng định khả năng tổng quát hóa ngoài Ostovar nếu chưa có tập validation độc lập.

### Giới hạn của benchmark

1. Ostovar là dữ liệu tổng hợp với đúng hai sudden drift đã biết ở trace 900 và 1900; BPI là dữ liệu thực với thay đổi có thể gradual, seasonal hoặc do thay đổi cơ cấu hồ sơ.
2. Ngưỡng median/MAD được tính trên toàn bộ score curve của từng log. Đây là detector offline; `alarm_trace` chỉ mô phỏng thời điểm đủ cửa sổ bên phải, chưa phải triển khai streaming thuần túy.
3. Localization chưa có nhãn cạnh/node chuẩn nên chỉ là lời giải thích, không phải localization accuracy.
4. Tham số mặc định đã phù hợp với cấu trúc Ostovar 2.999 traces/log; không nên chuyển nguyên xi sang BPI 31.509 cases mà thiếu kiểm tra đa tỉ lệ.

## 3. Điều chỉnh khi áp dụng cho BPI 2017

| Thành phần Ostovar | Áp dụng BPI 2017 | Điều chỉnh |
|---|---|---|
| DFG occurrence set/case | Có | Chỉ giữ lifecycle `complete` để tránh lặp schedule/start/suspend |
| JSD giữa hai cửa sổ | Có | Giữ nguyên công thức |
| Ngưỡng median/MAD | Có | Tính riêng theo scope và cỡ cửa sổ |
| Cửa sổ 150 | Không dùng đơn lẻ | Chạy 150, 300 và 500 cases |
| Ground-truth matching | Không | Thay bằng `candidate_only` |
| TP/FP/FN, F1 | Không | Không tính khi thiếu ground truth |
| Localization cạnh/node | Có | Cửa sổ 300 cases, điều kiện \|delta\| ≥ 0,05 và z ≥ 3 |
| Trace order | Có điều kiện | Sắp case theo thời điểm bắt đầu; thời gian drift là thời gian cohort bắt đầu |
| Segmentation | Bổ sung | Chạy `ALL`, `New credit`, `Limit raise` |

## 4. Dataset BPI 2017 đã xử lý

- Dòng sự kiện nguồn: **1.202.267**.
- Case: **31.509**.
- Event lifecycle `complete` giữ lại: **475.306**.
- Case không còn event sau lọc: **0**.
- Scope: `ALL` 31.509 cases, `New credit` 28.120 cases, `Limit raise` 3.389 cases.
- Tổng score point: **18.339**.
- Đỉnh được chọn trên từng cấu hình scope × window: **9**.
- Sau ghép đa tỉ lệ: **5 candidate rows**.
- Sau hợp nhất theo lịch giữa các scope: **2 consensus episodes**.

Không có đỉnh nào vượt ngưỡng ở cửa sổ 150. Các phát hiện chỉ xuất hiện ở cửa sổ 300/500, cho thấy tín hiệu trên BPI rộng hơn sudden drift cục bộ mà Ostovar mô phỏng.

## 5. Hai giai đoạn drift consensus

### CONSENSUS-D001 — 28–29/01/2016, ISO week 2016-W04

- Xuất hiện ở `ALL` và `New credit`.
- Một ứng viên được xác nhận ở hai cỡ cửa sổ 300/500.
- Tỷ số score/ngưỡng mạnh nhất: **1,404536**.
- Thay đổi nổi bật trong `New credit`:
  - `A_Complete -> O_Create Offer`: 0,3833 → 0,1067, delta -0,2767.
  - `A_Complete -> A_Validating`: 0,4000 → 0,6033, delta +0,2033.
  - `O_Sent (mail and online) -> A_Validating`: 0,2633 → 0,0700, delta -0,1933.
  - Tỷ lệ case chứa `O_Cancelled`: 0,6333 → 0,5033, delta -0,1300.

### CONSENSUS-D002 — 30/06–04/07/2016, ISO week 2016-W26/W27

- Xuất hiện ở cả `ALL`, `New credit` và `Limit raise`.
- Cả ba ứng viên scope đều được xác nhận ở hai cỡ cửa sổ 300/500.
- Tỷ số score/ngưỡng mạnh nhất: **1,774577**.
- Thay đổi nổi bật trên toàn log:
  - `O_Sent (mail and online) -> O_Sent (mail and online)`: 0,3767 → 0,0633, delta -0,3133.
  - `O_Created -> O_Create Offer`: 0,3933 → 0,0933, delta -0,3000.
  - `O_Cancelled -> O_Cancelled`: 0,2933 → 0,0767, delta -0,2167.
  - `A_Pending -> __END__`: 0,2100 → 0,3700, delta +0,1600.
  - Tỷ lệ case chứa `O_Cancelled`: 0,6933 → 0,4633, delta -0,2300.
- Riêng `Limit raise`, `W_Validate application -> __END__` giảm 0,4000 → 0,1100 và tỷ lệ case chứa `W_Validate application` giảm 0,5400 → 0,2767.

Hai episode trên là thay đổi cấu trúc/tần suất control-flow theo cohort case. Chúng không tự động chứng minh thay đổi chính sách, lỗi dữ liệu hay bottleneck hiệu năng; cần đối chiếu lịch vận hành và phân tích duration/waiting time độc lập.

## 6. Quan hệ với kết quả bottleneck W19/W24/W25/W49

Các kết quả cũ W19/W24/W25/W49 đo workload, waiting time và drift cục bộ theo tuần. Pipeline Ostovar đo phân phối cạnh DFG theo thứ tự case bắt đầu. Hai phương pháp trả lời hai câu hỏi khác nhau; việc pipeline mới không chọn W19/W24/W25/W49 không phải mâu thuẫn trực tiếp.

## 7. Các tệp kết quả

- `bpi2017_drift_consensus.csv`: hai episode đã hợp nhất giữa các scope.
- `bpi2017_drift_candidates.csv`: năm ứng viên theo scope và độ ổn định đa tỉ lệ.
- `bpi2017_drift_localization.csv`: cạnh/node thay đổi kèm before rate, after rate, delta, z-score.
- `bpi2017_drift_signals.csv`: toàn bộ score curve và threshold để audit/vẽ lại.
- `bpi2017_scope_summary.csv`: thống kê theo scope × window.
- `bpi2017_trace_index.csv`: ánh xạ trace index sang case, thời gian và KPI case.
- `bpi2017_run_metadata.csv`: tham số, số dòng và phân bố lifecycle.
- `benchmark/results/sensitivity_analysis.csv`: độ nhạy của benchmark Ostovar theo z và tolerance.

## 8. Chạy lại

```powershell
python -m unittest discover -s benchmark -p "test_*.py"
python benchmark/evaluate_ostovar_sensitivity.py
python benchmark/bpi2017_ostovar_analysis.py
```

## 9. Khuyến nghị xác nhận tiếp theo

1. Đối chiếu hai episode với lịch thay đổi policy, hệ thống, kênh gửi offer hoặc quy tắc kết thúc case của ngân hàng.
2. Chạy thêm detector theo cửa sổ thời gian cố định (tuần/tháng), tránh ảnh hưởng của biến động số case.
3. Xác nhận bằng một phương pháp độc lập như ADWIN/CUSUM/MMD và kiểm tra độ lặp qua bootstrap.
4. Tách structural drift khỏi performance drift: bổ sung duration/waiting-time features thay vì suy luận bottleneck từ DFG occurrence.
5. Nếu cần precision/recall trên BPI, phải tạo ground truth được chuyên gia xác nhận hoặc dùng các mốc vận hành có tài liệu.
