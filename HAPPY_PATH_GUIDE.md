# Happy Path Guide for BPI Challenge 2017

## 1) Muc dich tai lieu
Tai lieu nay giai thich:
- Dataset BPI Challenge 2017 dang dung trong du an.
- Notebook happy_path dang lam gi theo tung module.
- Cach doc ket qua va cach phat trien tiep cho Data Mining va Process Mining.

## 2) Tong quan dataset BPI 2017 trong du an
File du lieu chinh:
- data/bpi-challenge-2017/bpi_2017_cleaned.csv

Dac diem nghiep vu quan trong:
- Moi case la mot ho so vay.
- Event gom 3 nhom y nghia:
  - A_: trang thai ho so vay.
  - W_: cong viec xu ly noi bo.
  - O_: vong doi offer.
- Mot case co the co nhieu offer, vi vay trace de bi phuc tap neu khong loc dung.
- Lifecycle co nhieu gia tri, notebook uu tien complete de giam nhieu do thi.

Thuoc tinh nghiep vu dung nhieu trong phan tich:
- case:ApplicationType
- case:LoanGoal
- concept:name
- lifecycle:transition
- time:timestamp

## 3) Tom tat cac module trong notebooks/happy_path.ipynb

### Module A: Data loading va chuan hoa
Muc tieu:
- Doc log, chuan hoa timestamp.
- Loc lifecycle complete de process discovery on dinh.
- Chuan hoa ten O_Sent ve 1 ten thong nhat.

Ket qua:
- log_df la event log da san sang cho khai pha.

### Module B: Xac dinh successful cases
Muc tieu:
- Tao trace theo case.
- Danh dau success neu co A_Accepted va khong co A_Denied/A_Cancelled.

Ket qua:
- trace_df: bang tong hop theo case.
- success_df: tap case thanh cong.

### Module C: Tim happy path theo business score
Muc tieu:
- Gom variants tu success_df.
- Cham diem variant theo 2 tieu chi:
  - coverage cao
  - duration thap
- Chon variant diem cao nhat lam happy path.

Ket qua:
- happy_trace
- variant_ranking.csv

### Module D: KPI theo tung canh trong happy path
Muc tieu:
- Tinh wait time giua cac buoc trong cac case phu hop happy path.
- Tim cac canh co p90 cao de phat hien bottleneck.

Ket qua:
- happy_path_edge_kpi.csv

### Module E: Visual va bang nghiep vu
Muc tieu:
- Ve bieu do coverage variant.
- Ve bieu do p90 wait theo edge.
- Map tung activity ve phase nghiep vu.

Ket qua:
- happy_path_steps.csv

### Module F: DFG tach rieng cho tung happy path
Muc tieu:
- Tao DFG cho top happy paths toan cuc.
- Tao DFG rieng theo ApplicationType.

Ket qua:
- Thu muc results/happy_path/dfg_per_happy_path
- File index happy_path_dfg_index.csv

### Module G: Conformance proxy va root-cause
Muc tieu:
- Do do lech trace so voi happy path bang edit distance.
- So sanh success vs non-success.
- Phan tich nguyen nhan theo ApplicationType va LoanGoal.

Ket qua:
- conformance_case_metrics.csv
- root_cause_by_application_type.csv
- root_cause_by_loan_goal.csv
- action_plan_by_segment.csv

### Module H: Early prediction (Machine Learning) da nang prefix, ho tro dataset lon
Muc tieu:
- Khong co dinh 8 su kien dau.
- Chay nhieu moc prefix (mac dinh 5, 8, 12).
- Dung sparse features + SGDClassifier de scale cho du lieu lon hon.
- Co bien MAX_CASES_FOR_ML de gioi han so case khi can.

Dau ra:
- early_prediction_metrics_by_prefix.csv
- early_prediction_test_results_by_prefix.csv
- early_prediction_feature_importance_by_prefix.csv

Luu y quan trong:
- Neu threshold toi uu qua nho, nen dat floor threshold theo nghiep vu de tranh danh dau qua nhieu case.
- Co the uu tien recall non-success neu muc tieu la canh bao som.

### Module I: PLG application module
Muc tieu:
- Xuat bo canh/chuyen tiep va thoi gian cho de dua vao mo phong PLG.
- Ho tro what-if scenarios.

Dau ra:
- plg_inputs/plg_happy_edges.csv
- plg_inputs/plg_activity_nodes.csv
- plg_inputs/plg_readme.txt

## 4) Cach doc ket qua nhanh
1. Xem variant_ranking.csv de biet happy path nao phu nhieu case nhat.
2. Xem happy_path_edge_kpi.csv de tim edge co p90 wait cao nhat.
3. Xem root_cause_by_application_type.csv va root_cause_by_loan_goal.csv de xac dinh phan khuc rui ro.
4. Xem early_prediction_metrics_by_prefix.csv de chon moc prefix phu hop cho canh bao som.
5. Dung plg_happy_edges.csv de tao kich ban what-if trong PLG.

## 5) Huong phat trien tiep
1. Chon threshold theo business cost:
- false negative cao thi giam threshold de tang recall non-success.

2. Mo rong model benchmark:
- So sanh SGDClassifier voi XGBoost/LightGBM neu moi truong cho phep.

3. Prefix theo ti le tien trinh thay vi so su kien co dinh:
- Vi du 30%, 40%, 50% trace progress.

4. Dong bo Process Mining va Data Mining:
- Sau moi kich ban PLG, chay lai cung bo KPI conformance, bottleneck, early prediction.

## 6) Thu muc ket qua quan trong
- results/happy_path/
- results/happy_path/dfg_per_happy_path/
- results/happy_path/plg_inputs/

Tai lieu nay duoc viet de giup doc nhanh va bao cao nhanh, co the cap nhat tiep khi notebook thay doi.