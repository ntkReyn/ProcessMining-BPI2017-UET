# BPI 2017 — Ostovar-style drift result dataset

Đây là bộ kết quả áp dụng lõi DFG + Jensen–Shannon divergence + robust median/MAD của benchmark Ostovar cho BPI Challenge 2017.

Các dòng drift đều là **ứng viên thăm dò** (`candidate_only`). BPI 2017 không có ground truth drift đầy đủ nên bộ này không gắn TP/FP/FN.

## Thứ tự đọc đề xuất

1. `bpi2017_drift_consensus.csv` — hai giai đoạn consensus theo lịch.
2. `bpi2017_drift_candidates.csv` — ứng viên chi tiết theo scope.
3. `bpi2017_drift_localization.csv` — cạnh/node thay đổi.
4. `bpi2017_scope_summary.csv` — threshold và số peak theo cấu hình.
5. `bpi2017_drift_signals.csv` — score curve đầy đủ.
6. `bpi2017_trace_index.csv` — ánh xạ trace index về case/time.
7. `bpi2017_run_metadata.csv` — tham số và kiểm kê input.

Pipeline mặc định chỉ giữ lifecycle `complete`, chạy riêng `ALL`, `New credit`, `Limit raise`, và kiểm tra ba cỡ cửa sổ 150/300/500 cases.

Xem báo cáo đầy đủ tại `BPI2017_OSTOVAR_EVALUATION_REPORT.md` ở thư mục gốc dự án.
