# Mẫu dữ liệu

Mỗi file `sample_*.csv` là **mẫu nhỏ (tối đa 300 dòng)** lấy từ file gốc, chỉ để xem cấu trúc cột và nhãn.
Không dùng để huấn luyện. Lấy mẫu phân tầng theo nhãn (tối đa 60 dòng mỗi nhãn, 100 dòng BENIGN), nên tỉ lệ nhãn
trong mẫu **không phản ánh** tỉ lệ thật (thực tế BENIGN chiếm đa số).

Tạo lại: `python3 fetch_samples.py [tên thư mục…]` (chỉ cần Python chuẩn, đọc từng đoạn file qua HTTP Range).

| Thư mục | Nguồn mẫu | Số cột | Cột nhãn | Ghi chú |
|---|---|---|---|---|
| `CIC-IDS2017_original/` | Mirror HF `c01dsnap/CIC-IDS2017` của bản gốc CIC | 79 | `Label` | Lỗi mã hóa nhãn (`Web Attack � XSS`); tên cột có khoảng trắng đầu |
| `CIC-IDS2017_improved/` | Bản sửa lỗi Engelen/Liu [2][3] (distrinet-research.be) | 91 | `Label` | Có nhãn `… - Attempted` cho flow tấn công không thành công |
| `CSE-CIC-IDS2018_original/` | Mirror HF `pcy12345BSU/CSE-CIC-IDS-2018` | 80 | `Label` | |
| `NF-ToN-IoT-v2/` | Mirror HF `Nora9029/NF-ToN-IoT-v2` | 45 | `Label` (0/1), `Attack` (tên) | **Bản v2** (43 đặc trưng); v3 cần đăng nhập kho UQ, thêm 10 đặc trưng thời gian |
| `CIC-IoT2023/` | Mirror HF `bencorn/CIC-IoT-2023` (Merged01.csv) | 40 | `Label` | Đặc trưng theo cửa sổ gói tin, không phải CICFlowMeter |
| `CICIoMT2024/` | Mirror HF `somnath0100/CICIoMT2024Small` | 84 | `Label` | Mirror để `NeedManualLabel`; nhãn đã được lấy từ tên file |

**Các bộ chưa có mẫu:**
- **NetFlow v3:** kho UQ (rdm.uq.edu.au) yêu cầu đăng nhập; cần tự đăng nhập để tải từ https://staff.itee.uq.edu.au/marius/NIDS_datasets/
- **CSE-CIC-IDS2018 bản sửa lỗi [3]:** file zip 10 GB, chỉ đọc tuần tự được; 1,5 GB đầu của ngày 14/02 toàn BENIGN và máy chủ ngắt kết nối khi đọc tiếp. Cấu trúc giống `CIC-IDS2017_improved/` (91 cột). Tải cả file tại https://intrusion-detection.distrinet-research.be/CNS2022/Dataset_Download.html
- **CICAPT-IIoT, LYCOS-IDS2017:** chưa tìm thấy link tải trực tiếp không cần form.

**Lưu ý:** dữ liệu trên Hugging Face là bản sao do người dùng tải lên, không phải nguồn chính thức. Khi làm đồ án thật,
hãy tải từ trang chính thức (link trong `references/papers/README.md` và phần trả lời trước).
