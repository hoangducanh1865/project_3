"""Hàm dùng chung cho các mô hình."""
import os
import sys

import torch


def tensor(x, dev):
    return torch.as_tensor(x, device=dev)


def chunks(n, bs=8192):
    for i in range(0, n, bs):
        yield slice(i, min(i + bs, n))


def use_closr_repo():
    """Thêm mã nguồn gốc của CLOSR (github.com/jackwilkie/CLOSR) vào sys.path."""
    d = os.path.abspath(os.environ.get("CLOSR_DIR", "third_party/CLOSR"))
    if not os.path.isdir(d):
        raise FileNotFoundError(f"không thấy {d}. Chạy: git clone https://github.com/jackwilkie/CLOSR {d}")
    if d not in sys.path:
        sys.path.insert(0, d)
