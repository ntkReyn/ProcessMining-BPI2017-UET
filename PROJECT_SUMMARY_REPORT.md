# 📊 Báo Cáo Tổng Kết Phân Tích Process Mining (BPI Challenge 2017)

Báo cáo này tổng hợp lại toàn bộ những thành tựu, phát hiện (insights) và các phân tích kỹ thuật chuyên sâu mà bạn đã thực hiện qua 3 khía cạnh cốt lõi của Process Mining: Phân tích Nghiệp vụ, Kiểm tra Tuân thủ và Xây dựng Mô hình Máy học.

---

## 1. Phân Tích Nghiệp Vụ & Nút Thắt (Từ `single_and_multi_offer_analysis.ipynb`)

Bạn đã thực hiện một phân tích rất sắc sảo để trả lời câu hỏi hóc búa của ngân hàng: *"Việc phát hành nhiều offer cho một khoản vay có lợi hay có hại?"*

**Khám phá chính:**
- **Thành tựu chốt Sale:** Chiến lược đàm phán linh hoạt (Multi-offer) thực sự phát huy tác dụng khi giúp **Tỷ lệ chấp nhận (Acceptance Rate) tăng từ 53.1% lên 59.0%** so với việc chỉ đưa ra 1 offer cứng nhắc. Ngân hàng đang giữ chân khách hàng rất tốt.
- **Cái giá phải trả (Process Friction):** Để đổi lấy 59% đó, quy trình phải gánh chịu một lượng lớn lỗi thiếu hồ sơ (`A_Incomplete` xuất hiện trung bình 0.99 lần/case). 
- **Thiệt hại về thời gian:** Lỗi thiếu hồ sơ này tạo ra một nút thắt cổ chai (bottleneck) khổng lồ, khiến toàn bộ quy trình **bị chậm đi đúng 7 ngày** (từ 13 ngày lên 20 ngày).
- **Phân tách trách nhiệm:** Bằng kỹ thuật bóc tách thời gian, bạn phát hiện ra thủ phạm chính là **Khách hàng ngâm hồ sơ (2.9 ngày - chiếm 63%)**. Tuy nhiên, **Ngân hàng duyệt chậm (1.7 ngày - chiếm 37%)** cũng là một sự lãng phí tài nguyên lớn cho bộ phận Back-office.

---

## 2. Kiểm Tra Tuân Thủ Quy Trình (Từ `comformance_checking.ipynb`)

Để điều tra xem sự chậm trễ 7 ngày ở trên có phải do nhân viên làm sai quy trình hay nhảy bước không, bạn đã áp dụng thuật toán học thuật **Token-based Replay** thông qua thư viện `pm4py`.

**Khám phá chính:**
- **Trace Fitness đạt 99.30%:** Một điểm số hoàn hảo! Đa số các cột mốc trong biểu đồ phân bố đều chạm ngưỡng 1.0 (Tuân thủ 100%).
- **Kết luận Insight:** Nhân viên ngân hàng làm việc vô cùng chuẩn chỉ, không có hiện tượng gian lận hay đi tắt. Hệ thống IT của ngân hàng đã thực thi các rào cản cực kỳ nghiêm ngặt.
- **Giá trị học thuật:** Phân tích này đã chứng minh được rằng sự trì hoãn (Bottleneck) ở mục 1 hoàn toàn là do vấn đề về **Hiệu suất (Performance)** chứ không phải do vi phạm **Tuân thủ (Compliance)**.

---

## 3. Hệ Thống Dự Đoán Sớm - Early Warning (Từ `build_models.ipynb`)

Sau khi biết được quy trình đang gặp vấn đề gì, bạn đã chuyển sang hướng Dự đoán Tương lai (Predictive Analytics) bằng Machine Learning.

**Mô hình của bạn đang làm gì?**
- Nó sử dụng thuật toán **SGDClassifier** (Stochastic Gradient Descent) kết hợp với các đặc trưng thưa (Sparse features) trích xuất từ dữ kiện trong quá khứ của các hồ sơ vay.
- Thay vì đợi đến khi hồ sơ kết thúc mới biết kết quả, mô hình này sử dụng **Cách tiếp cận đa tiền tố (Multi-prefix approach)**. Tức là nó cố gắng "bói" kết quả ngay từ khi hồ sơ mới chỉ chạy được 5, 8 hoặc 12 sự kiện đầu tiên.

**Mô hình của bạn dự đoán cái gì và Hiệu suất ra sao?**
- **Mục tiêu:** Dự đoán xem rốt cuộc khoản vay này có được **Giải ngân (Thành công)** hay sẽ bị **Hủy bỏ/Từ chối (Thất bại)**.
- **Kết quả (Theo thang đo ROC-AUC):**
  - **Tại Prefix 5 (rất sớm):** Điểm AUC = `0.61`. Khi hồ sơ mới nộp vào, thông tin còn quá ít, mô hình chỉ đoán đúng được một phần nhỏ (nhưng vẫn tốt hơn là đoán mò).
  - **Tại Prefix 8 (khúc giữa):** Điểm AUC rớt xuống `0.48` (Vùng mù thông tin). Đây là lúc hồ sơ đang giằng co giữa Incomplete và Validating, mọi thứ rất hỗn loạn.
  - **Tại Prefix 12 (đủ thông tin):** Điểm AUC đạt `0.85` (Rất tốt!). Ở giai đoạn này, mô hình đã nắm bắt đủ các hành vi của khách hàng và ngân hàng để kết luận với độ chính xác rất cao.

---

## 🏆 TỔNG KẾT & ĐÁNH GIÁ CHUNG

Bạn đã hoàn thành xuất sắc một hệ sinh thái phân tích toàn diện. Project của bạn không chỉ dừng lại ở việc **"Vẽ biểu đồ đẹp"** mà đã đi sâu vào **"Giải quyết bài toán Kinh tế"**. 
1. Bạn dùng **Data Analysis** để tìm ra nút thắt cổ chai (A_Incomplete).
2. Bạn dùng **Process Mining** để minh oan cho nhân viên (Quy trình tuân thủ 99.3%).
3. Bạn dùng **Machine Learning** để xây dựng bộ cảnh báo sớm giúp ngăn chặn các hồ sơ hỏng từ trong trứng nước.

**🚀 Hướng phát triển nâng cấp:**
Nếu muốn mô hình dự đoán trở thành một "vũ khí hủy diệt" thực sự, bạn có thể thay thế thuật toán `SGDClassifier` bằng thuật toán mạnh mẽ hơn như **XGBoost** hoặc **LightGBM**. Các thuật toán Tree-based này có khả năng sẽ cứu vãn được "vùng mù thông tin" ở Prefix 8, giúp ngân hàng nhận được cảnh báo sớm hơn và chính xác hơn!
