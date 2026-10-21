# project_3

Project 3 (HUST, kỳ 20261): phát hiện tấn công mạng bằng học tương phản và đề xuất biện pháp ứng phó trước các tấn công Out-of-Domain (OOD). Đề tài C3, phát triển từ bài [16] (CLAD/CLOSR).

## Quy trình làm việc

Viết mã trên laptop, `git push`, rồi notebook Colab chỉ `pull` và chạy. Kết quả ghi lên Google Drive, không vào repo.

## Bố cục

| Thư mục | Nội dung |
|---|---|
| `conf/` | Cấu hình Hydra: `dataset/`, `protocol/` (P0, P1), `model/` (7 baseline) |
| `src/` | `data.py` nạp và tách dữ liệu, `models.py` các baseline, `metrics.py`, `run.py` chạy một lần, `report.py` gom bảng |
| `notebooks/` | Notebook Colab chạy thực nghiệm |
| `datasets/` | Hướng dẫn và script lấy mẫu dữ liệu (không chứa dữ liệu) |
| `agents/` | Ghi chép tri thức cho agent, xem `CLAUDE.md` |

## Chạy

Cần GPU. Mở `notebooks/week_4_baseline.ipynb` trên Colab (T4), hoặc chạy từ thư mục gốc:

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

## Không có trong repo

Dữ liệu, tài liệu tham khảo, báo cáo đã nộp và lịch sử chat với agent chỉ có trên máy cục bộ (xem `.gitignore`).
