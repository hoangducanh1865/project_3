# project_3

Project 3 (HUST, kỳ 20261): phát hiện tấn công mạng bằng học tương phản và đề xuất biện pháp ứng phó trước các tấn công Out-of-Domain (OOD). Đề tài C3, phát triển từ bài [16] (CLAD/CLOSR).

## Quy trình làm việc

Viết mã trên laptop, `git push`, rồi notebook Colab chỉ `pull` và chạy. Kết quả ghi lên Google Drive, không vào repo.

## Bố cục

| Thư mục | Nội dung |
|---|---|
| `conf/` | Cấu hình Hydra: `dataset/`, `protocol/` (P0, P1), `model/` (7 baseline và HC-CLOSR) |
| `src/` | `data.py` nạp và tách dữ liệu, `models.py` các mô hình, `response.py` đề xuất biện pháp ứng phó, `metrics.py`, `run.py` chạy một lần, `report.py` gom bảng |
| `notebooks/` | `baseline.ipynb` chạy thực nghiệm, `colab.ipynb` mở SSH vào phiên Colab |
| `scripts/` | `colab_ssh.sh`, kernel Kaggle trong `kaggle/`, `recover_results.py` khôi phục kết quả từ log |
| `deploy/` | API suy luận trên Modal |
| `web/` | Web giám sát xâm nhập mạng (Next.js, triển khai trên Vercel) |
| `datasets/` | Hướng dẫn và script lấy mẫu dữ liệu (không chứa dữ liệu) |
| `agents/` | Ghi chép tri thức cho agent, xem `CLAUDE.md` |

## Chạy

Cần GPU. Mở `notebooks/baseline.ipynb` trên Colab (T4), hoặc chạy từ thư mục gốc:

```bash
pip install -r requirements.txt
git clone https://github.com/jackwilkie/CLOSR third_party/CLOSR   # mã gốc của [16]
export LYCOS_CSV=/đường/dẫn/lycos.csv OUT_ROOT=/nơi/lưu/kết/quả
python -m src.run protocol=p0 model=mlp_msp
python -m src.run -m protocol=p1 protocol.heldout=slowloris,portscan model=mlp_msp,xgboost,closr
python -m src.report
```

| Giao thức | OOD khi kiểm thử |
|---|---|
| P0 | Các lớp hiếm (dưới 100 mẫu), như [16] |
| P1 | Họ tấn công `protocol.heldout`, bị loại khỏi tập huấn luyện |

Baseline: MLP (điểm MSP), MLP + KNN theo [13], XGBoost, Isolation Forest, Autoencoder, CLAD, CLOSR. CLAD và CLOSR dùng mã gốc của [16] (Apache-2.0) với ngân sách huấn luyện nhỏ hơn bản gốc.

Phương pháp đề xuất: `model=hc_closr` (HC-CLOSR), cùng ngân sách huấn luyện với CLOSR.

## Web demo

Web tại https://project3-ids.vercel.app gọi API trên Modal qua route server, khoá API không lộ ra trình duyệt.

Luồng giả lập chạy 24/7 trên Modal (`tick`, mỗi phút một lần): phát lại flow thật của LYCOS-IDS2017 chưa dùng để huấn luyện (`src/simulator.py`) theo kịch bản trong `deploy/scenarios.json` (Gemini soạn bằng `deploy/gen_scenarios.py`), chạy HC-CLOSR rồi gom cảnh báo thành sự cố (`src/stream.py`). Trình tự tấn công và IP là giả lập.

```bash
pip install modal pyyaml
python deploy/setup_modal.py                          # tạo secret từ .env
PYTHONPATH=. modal run deploy/modal_app.py::main      # dựng CLOSR [16] từ trọng số gốc
PYTHONPATH=. modal run deploy/modal_app.py::stream    # dựng kho flow và nạp kịch bản cho luồng giả lập
modal volume put project3-model <thư mục> /hc_closr   # nạp HC-CLOSR, thư mục do scripts/kaggle xuất ra
PYTHONPATH=. modal deploy deploy/modal_app.py         # triển khai API
```

Web cần ba biến môi trường trên Vercel: `MODAL_API_URL`, `MODAL_LIVE_URL`, `MODAL_API_KEY`.

## Không có trong repo

Báo cáo các tuần (`reports/`), tài liệu tham khảo và lịch sử chat với agent chỉ có trên máy cục bộ (xem `.gitignore`). Dữ liệu và kết quả nằm trên Google Drive.
