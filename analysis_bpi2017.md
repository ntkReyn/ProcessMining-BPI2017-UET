# Đánh Giá Toàn Diện Dự Án Process Mining — BPI Challenge 2017

---

## 1. Tổng Quan Dataset & Cấu Trúc Dự Án

**Dataset:** BPI Challenge 2017 — Nhật ký sự kiện quy trình xét duyệt khoản vay của một ngân hàng Hà Lan.

| Chỉ số | Giá trị |
|--------|---------|
| Số dòng sự kiện | 1.201.090 |
| Số case (đơn vay) | 31.509 |
| Số loại activity | 26 |
| Thời gian | 2016–2017 |
| Phân nhóm event | A\_ (trạng thái đơn) / O\_ (offer) / W\_ (workflow) |

**Cấu trúc project:**
```
notebooks/
  ├── data_cleaning.ipynb       — Tiền xử lý & chuẩn hóa
  ├── eda_pm4py.ipynb           — Khám phá dữ liệu với pm4py
  ├── process.ipynb             — Process discovery (Petri net, DFG)
  ├── happy_path.ipynb          — Happy path + ML dự đoán sớm
  ├── drift_detection.ipynb     — Bottleneck analysis + phát hiện drift
  ├── process_drift.ipynb       — Drift theo tuần
  └── build_models.ipynb        — Xây dựng mô hình phân loại
results/
  ├── happy_path/               — DFG, conformance, early prediction
  ├── bottleneck_analysis/      — Biểu đồ workload & waiting time
  ├── phase_drift_analysis_local/ — Drift theo tuần
  └── trace_analysis/           — Trace-level inspection
```

---

## 2. Những Gì Dự Án Đã Làm Được ✅

### 2.1 Tiền Xử Lý & Làm Sạch Dữ Liệu
- ✅ Load và parse timestamp với UTC
- ✅ Chuẩn hóa tên activity (gộp các biến thể O_Sent)
- ✅ Lọc `lifecycle:transition = complete` để giảm nhiễu trong DFG
- ✅ Phân loại event theo 3 nhóm: Application (A_), Offer (O_), Workflow (W_)
- ✅ Tính `gap_minutes` giữa các sự kiện trong cùng case

### 2.2 Process Discovery
- ✅ Petri net qua `pm4py.discover_petri_net_inductive` (Inductive Miner)
- ✅ Directly-Follows Graph (DFG) cho toàn bộ log
- ✅ DFG riêng theo ApplicationType (New credit / Limit raise)
- ✅ Social Network Analysis (SNA) giữa các resource — kết quả HTML: `jupyter_sna_vis.html`

### 2.3 Happy Path Analysis
- ✅ Xác định successful cases (A_Accepted, không có A_Denied/A_Cancelled)
- ✅ Xếp hạng variant theo business score (coverage × duration)
- ✅ **Happy path #1:** 971 cases — trình tự 12 bước từ A_Create Application → A_Pending
- ✅ Tính KPI theo từng cạnh (p90 waiting time)
- ✅ Conformance proxy bằng edit distance so với happy path
- ✅ Root cause phân tích theo ApplicationType và LoanGoal

### 2.4 Bottleneck Analysis
- ✅ Weekly workload vs. waiting time (biểu đồ `01_weekly_workload_vs_waiting.png`)
- ✅ Xác định 4 tuần milestone: W19, W24, W25, W49
- ✅ Phân tích bottleneck theo giai đoạn nghiệp vụ
- ✅ Top activities P90 waiting time
- ✅ Bottleneck class mix (A_/O_/W_ nhóm nào gây delay nhiều nhất)

### 2.5 Drift Detection
- ✅ Local window comparison giữa các tuần milestone
- ✅ Phát hiện shift về tần suất và delay tại từng edge
- ✅ `bottleneck_summary_interpretation.csv` với top drift edge theo ApplicationType

### 2.6 Early Prediction (Machine Learning)
- ✅ Multi-prefix approach (prefix 5, 8, 12)
- ✅ Sparse features + SGDClassifier
- ✅ Kết quả ROC-AUC: 0.61 (prefix 5), 0.48 (prefix 8), **0.85 (prefix 12)**
- ✅ Feature importance theo từng prefix length
- ✅ `early_prediction_test_results_by_prefix.csv` — 1.19 MB

### 2.7 PLG Module (Process-Level Generation)
- ✅ Export edges và activity nodes cho PLG simulation
- ✅ What-if scenario support

---

## 3. So Sánh Với Các Giải Pháp Winning BPI 2017 🏆

### Câu hỏi chính của challenge (4 câu hỏi gốc từ ngân hàng):

| # | Câu hỏi gốc | Dự án có làm không? | Trạng thái |
|---|-------------|---------------------|------------|
| 1 | **Throughput time** — thời gian chờ của ngân hàng vs. của khách hàng | Phân tích bottleneck & waiting time | ✅ Có — nhưng chưa phân tách rõ "bank wait" vs "customer wait" |
| 2 | **Offer acceptance** — ảnh hưởng của số lần yêu cầu thông tin bổ sung đến tỷ lệ chấp nhận offer | Root cause theo LoanGoal | ⚠️ Có một phần — chưa phân tích số lần incompleteness request |
| 3 | **Single vs multi-offer customer** — so sánh hành vi | Chưa có module riêng | ❌ Chưa làm |
| 4 | **Trends & anomalies** — xu hướng khác thú vị | Drift detection (W19/W24/W25/W49) | ✅ Có |

### So sánh kỹ thuật với các winners:

| Kỹ thuật | Winners dùng | Dự án hiện tại | Gap |
|-----------|-------------|----------------|-----|
| Process discovery (DFG, Petri net) | Celonis, Disco, ProM + Heuristics Miner | pm4py Inductive Miner | ⚠️ Thiếu Heuristics Miner (ít nhiễu hơn cho log phức tạp) |
| Conformance checking | Proper alignments | Edit distance proxy | ⚠️ Edit distance là xấp xỉ, không phải conformance chuẩn |
| Concept drift detection | ProM (CD-MMD, MFES) | Custom window comparison | ⚠️ Chưa dùng thuật toán drift chuẩn (ADWIN, CUSUM) |
| Segmentation | Tách A_/O_/W_ riêng biệt | Lọc lifecycle=complete | ⚠️ Tốt nhưng chưa tách hoàn toàn 3 sub-process |
| Offer analysis | Phân tích số offer/khách | Chưa có | ❌ Thiếu hẳn |
| Resource/workload analysis | SNA + handover-of-work | SNA HTML + bottleneck | ✅ Khá tốt |
| Predictive analytics | Decision tree, Random Forest | SGDClassifier | ⚠️ SGD đơn giản, chưa dùng XGBoost/LightGBM |
| Business recommendations | Actionable insights | action_plan_by_segment.csv | ✅ Có nhưng ngắn |
| BPMN visualization | Có | Không (chỉ có DFG/Petri net) | ❌ Thiếu |

---

## 4. Tính Logic của Các File Notebook 🧪

### 4.1 `data_cleaning.ipynb` — **Logic tốt ✅**
- Đọc dữ liệu → kiểm tra schema → lọc lifecycle → chuẩn hóa tên → lưu CSV
- Luồng tuyến tính, không có lỗi logic rõ ràng

### 4.2 `process.ipynb` — **Logic tốt, nhưng thiếu context ⚠️**
- Dùng pm4py để format → discover Petri net → visualize
- **Vấn đề:** Inductive Miner với toàn bộ log (kể cả schedule/start/suspend) sẽ tạo model rất phức tạp. Nên lọc chỉ `complete` trước (đã làm trong `data_cleaning` nhưng không rõ có apply vào đây không)

### 4.3 `happy_path.ipynb` — **Logic chặt chẽ, nhiều module ✅✅**
- Module A → B → C → D → E → F → G → H → I
- Chuỗi phụ thuộc hợp lý: cleaning → case success → variant ranking → KPI → DFG → conformance → ML → PLG
- **Lưu ý:** Prefix 8 cho ROC-AUC = 0.48 (gần ngẫu nhiên) — có thể do đây là "vùng mù" giữa quá ít và đủ thông tin; prefix 12 đạt 0.85 là tốt

### 4.4 `drift_detection.ipynb` — **Logic đúng, đặt tên nhầm ⚠️**
- File được đặt tên `drift_detection.ipynb` nhưng tiêu đề bên trong là **"Bottleneck Analysis"**
- Nội dung thực là: tính gap_minutes → weekly aggregation → highlight tuần W19/W24/W25/W49 → phân tích class mix
- Đây là bottleneck analysis, không phải concept drift đúng nghĩa

### 4.5 `process_drift.ipynb` — **Khung còn nhỏ, cần phát triển thêm ⚠️**
- 51KB — có thể là phiên bản rút gọn
- Cần kiểm tra xem có test thống kê hay chỉ visualization

### 4.6 `build_models.ipynb` — **Logic ổn ✅**
- Load data → sort theo case + time → 31.509 cases
- Có thể là phiên bản độc lập của module ML

---

## 5. Các Kết Quả Output Đáng Chú Ý 📊

### Bottleneck Analysis:
| File | Insight |
|------|---------|
| `01_weekly_workload_vs_waiting.png` | Phát hiện đỉnh bottleneck theo tuần |
| `02_stage_waiting_time_target_weeks.png` | So sánh giai đoạn nào chờ lâu nhất trong W19/24/25/49 |
| `03_bottleneck_class_mix.png` | A_/O_/W_ class nào chiếm tỷ lệ delay |
| `04_top_activities_p90_waiting.png` | Activity nào có P90 waiting cao nhất |

### Drift Summary (bottleneck_summary_interpretation.csv):
- **W19 - New credit:** Edge `O_Returned → W_Validate application` có delay 50.9 giờ; edge `W_Complete application → A_Complete` giảm 67 case
- **W24 - New credit:** Edge `A_Incomplete → A_Validating` delay 32.9 giờ
- **W25 - New credit:** Edge `O_Returned → O_Accepted` delay 70.6 giờ — **bottleneck nghiêm trọng nhất**

### Early Prediction:
| Prefix | ROC-AUC | Nhận xét |
|--------|---------|---------|
| 5 events | 0.61 | Chấp nhận được khi có rất ít thông tin |
| 8 events | 0.48 | Gần ngẫu nhiên — "dead zone" |
| 12 events | **0.85** | Tốt — đủ thông tin để dự đoán |

---

## 6. Những Gì Chưa Làm Được ❌

### Phân tích còn thiếu:
1. **Single vs. multi-offer analysis** — So sánh khách hàng nhận 1 offer vs. nhiều offer (câu hỏi gốc #3)
2. **Phân tách rõ "bank wait time" vs "customer wait time"** — Waiting time hiện tại tính chung
3. **Số lần incomplete request → tác động đến acceptance rate** (câu hỏi gốc #2)
4. **Offer-level analysis** — Phân tích riêng sub-process O_Create Offer → O_Accepted/O_Cancelled
5. **Proper conformance checking** — Dùng token-based replay hoặc alignment thay vì edit distance
6. **Thuật toán drift chuẩn** — ADWIN, CUSUM, hoặc ProM's concept drift plugins
7. **BPMN model** — Tạo BPMN diagram từ discovered model (winners hay dùng)
8. **Comparison between application types** — Throughput time phân theo ApplicationType chi tiết hơn

### Về output chất lượng:
- `trace_analysis/` chỉ có 2 trace sample — cần mở rộng
- `happy_path/action_plan_by_segment.csv` chỉ có 405 bytes — rất ngắn gọn
- `plg_inputs/` chưa thấy kết quả simulation

---

## 7. Có Thể Khai Thác Thêm Gì? 🚀

### 7.1 Phân tích nghiệp vụ sâu hơn
- **Offer conversion funnel:** O_Created → O_Sent → O_Returned → O_Accepted/O_Cancelled
- **Credit score segmentation:** Phân tích CreditScore, OfferedAmount, MonthlyCost tác động đến outcome
- **Resource workload balancing:** Ai xử lý nhiều case nhất? Bottleneck do người hay quy trình?
- **Multi-offer impact:** Khách hàng nhận >1 offer có conversion rate cao hơn không?

### 7.2 Process Mining nâng cao
- **Inductive Miner Infrequent (IMf):** Loại bỏ noise từ các trace hiếm
- **Decision Mining:** Học điều kiện phân nhánh (khi nào → A_Incomplete vs A_Accepted)
- **Social Network Analysis đầy đủ:** Handover-of-work matrix, working-together matrix
- **Temporal clustering:** Nhóm case theo thời điểm trong năm (seasonal patterns)

### 7.3 Predictive Analytics mở rộng
- **Random Forest / XGBoost** thay SGDClassifier
- **Remaining time prediction** (LSTM, Transformer)
- **Next activity prediction** theo từng trạng thái
- **Risk scoring** cho từng đơn vay dựa trên trace prefix

---

## 8. Có Thể Ứng Dụng Agent/LLMs Không? 🤖

### 8.1 Tại Sao Dataset Này Phù Hợp (Dù "Nhỏ" Theo Chuẩn LLM)?

**31.509 cases với 1.2 triệu events** là đủ lớn cho LLM-augmented analysis vì:
- LLM không cần toàn bộ raw data — chỉ cần **aggregated features + text description**
- Mỗi case có thể được mô tả bằng ngôn ngữ tự nhiên ngắn gọn

### 8.2 Các Ứng Dụng Agent/LLM Khả Thi

#### 🔴 Ứng dụng 1: Natural Language Process Mining Query
```
User: "Tuần nào có bottleneck nặng nhất trong 2017?"
Agent: → truy vấn bottleneck_summary_interpretation.csv
      → trả lời: "Tuần 25 - New credit, edge O_Returned→O_Accepted delay 70.6h"
```
**Feasibility:** ✅ Cao — dùng RAG + tool calling

#### 🟡 Ứng dụng 2: Trace Anomaly Explanation
```
Agent: Đọc trace của case X → so sánh với happy path → giải thích bằng tiếng Việt
       "Case này bị delay 3 ngày do loop A_Incomplete → A_Validating 2 lần"
```
**Feasibility:** ✅ Cao — trace đủ ngắn để fit vào context window

#### 🟡 Ứng dụng 3: Root Cause Report Generation
```
Agent: Đọc root_cause_by_loan_goal.csv + action_plan_by_segment.csv
      → Tạo báo cáo nghiệp vụ tự động bằng ngôn ngữ tự nhiên
```
**Feasibility:** ✅ Cao — đây là strong suit của LLM

#### 🔵 Ứng dụng 4: What-If Simulation Agent
```
User: "Nếu giảm thời gian xử lý W_Validate application xuống 50%, throughput tăng bao nhiêu?"
Agent: → Dùng PLG inputs → simulate → estimate outcome
```
**Feasibility:** ⚠️ Trung bình — cần PLG backend + LLM làm orchestrator

#### 🔴 Ứng dụng 5: Early Warning System
```
Khi một case mới đạt prefix=5 events:
Agent: → gọi SGDClassifier → dự đoán xác suất thất bại
       → nếu > threshold → gửi alert bằng ngôn ngữ tự nhiên
       → giải thích: "Case này có 70% khả năng bị từ chối vì CreditScore thấp"
```
**Feasibility:** ✅ Cao — ML model đã có, LLM chỉ cần interpret

### 8.3 Giới Hạn & Lưu Ý

| Hạn chế | Giải pháp |
|---------|-----------|
| Dữ liệu chứa thông tin ngân hàng nhạy cảm | Dùng LLM local (Ollama) hoặc data anonymization |
| 1.2M events không fit vào context window | Aggregation + feature extraction trước khi gửi LLM |
| LLM không hiểu process mining notation sẵn có | Fine-tune hoặc prompt engineering với ví dụ domain |
| ROC-AUC prefix=8 chỉ 0.48 | Cần feature engineering tốt hơn trước khi integrate LLM |

### 8.4 Kiến Trúc Agent Đề Xuất

```
┌─────────────────────────────────────────────┐
│              LLM Agent (Orchestrator)        │
│  (GPT-4o / Claude / Gemini / Llama local)   │
└──────────────────┬──────────────────────────┘
                   │ Tool calling
        ┌──────────┼──────────┐
        ▼          ▼          ▼
  [Query CSV]  [Run ML]  [Explain Trace]
  bottleneck   predict   compare to
  summary      outcome   happy path
        │          │          │
        └──────────┴──────────┘
                   │
              [RAG Layer]
         (variant_ranking.csv,
          conformance metrics,
          bottleneck summaries)
```

---

## 9. Tóm Tắt & Ưu Tiên Phát Triển

### Priority 1 — Hoàn thiện phân tích cơ bản:
1. Thêm **single vs. multi-offer analysis** (câu hỏi #3 của challenge)
2. Phân tách **bank wait vs. customer wait time**
3. Sửa tên file `drift_detection.ipynb` → `bottleneck_analysis.ipynb`

### Priority 2 — Nâng cao kỹ thuật:
1. Thay SGDClassifier bằng **XGBoost/LightGBM**
2. Thêm **proper conformance checking** (pm4py token replay)
3. Thêm **Offer-level sub-process analysis**

### Priority 3 — AI/LLM Integration:
1. Build **NL Query Agent** cho bottleneck summary
2. Build **Early Warning System** với LLM explanation
3. Thử nghiệm **trace anomaly explainer** cho từng case

> [!NOTE]
> Dataset BPI 2017 hoàn toàn phù hợp để tích hợp LLM/Agent. Điểm mạnh nhất là: dữ liệu có cấu trúc rõ ràng (A_/O_/W_), có output CSV sạch, và các câu hỏi nghiệp vụ rõ ràng — đây là điều kiện lý tưởng để LLM làm interpreter/explainer.

> [!TIP]
> Bắt đầu với ứng dụng đơn giản nhất: **Trace Anomaly Explainer** — chọn 10 case lệch nhiều nhất so với happy path, để LLM giải thích tại sao chúng thất bại. Không cần nhiều engineering, kết quả rất ấn tượng cho demo.
