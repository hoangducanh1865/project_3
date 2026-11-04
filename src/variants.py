"""PV: tự sinh biến thể của flow tấn công trong không gian đặc trưng, sau khi mô hình đã huấn luyện xong.

Mô phỏng hai thay đổi kẻ tấn công làm được mà không đổi bản chất tấn công, giữ quan hệ giữa các đặc trưng:
- dilate(a): chạy chậm đi a lần. Thời lượng và khoảng cách gói nhân a, tốc độ chia a.
- pad(b): thêm b byte vào mỗi gói có dữ liệu theo chiều đi, tối đa 1460 byte mỗi gói.
Đây là đánh giá độ bền trong không gian đặc trưng, không phải traffic thật: bộ trích đặc trưng có thể tách flow khác đi
(ví dụ flow dài quá thời gian chờ), và pad không tính lại các cột độ lệch chuẩn. Mọi biến đổi là tự thiết kế.
"""
import numpy as np

TIME = ("flow_duration", "iat_", "fwd_iat_", "bwd_iat_", "active_", "idle_")
RATE = ("bytes_per_s", "pkt_per_s", "fwd_pkt_per_s", "bwd_pkt_per_s", "fwd_bulk_rate_mean", "bwd_bulk_rate_mean")
MSS = 1460


def dilate(raw, cols, a):
    out = raw.copy()
    for j, c in enumerate(cols):
        if c.startswith(TIME):
            out[:, j] *= a
        elif c in RATE:
            out[:, j] /= a
    return out


def pad(raw, cols, b):
    out = raw.copy()
    col = lambda name: out[:, cols.index(name)] if name in cols else None
    tot, n, cnt, bwd = col("fwd_pkt_len_tot"), col("fwd_non_empty_pkt_cnt"), col("fwd_pkt_cnt"), col("bwd_pkt_len_tot")
    bwd_cnt = col("bwd_pkt_cnt")
    old_tot = tot.copy()
    new_tot = np.minimum(old_tot + b * n, np.maximum(old_tot, MSS * n))
    ratio = (new_tot + 1) / (old_tot + 1)
    tot[:] = new_tot
    for name, value in (("fwd_pkt_len_mean", new_tot / np.maximum(cnt, 1)),
                        ("pkt_len_mean", (new_tot + bwd) / np.maximum(cnt + bwd_cnt, 1)),
                        ("fwd_pkt_len_max", np.minimum(col("fwd_pkt_len_max") + b * (n > 0), MSS)),
                        ("fwd_subflow_bytes_mean", col("fwd_subflow_bytes_mean") * ratio),
                        ("bytes_per_s", col("bytes_per_s") * (new_tot + bwd + 1) / (old_tot + bwd + 1))):
        col(name)[:] = value
    col("pkt_len_max")[:] = np.maximum(col("pkt_len_max"), col("fwd_pkt_len_max"))
    return out


def evaluate_variants(scorer, sp, cols, s_val, spec):
    """Tỉ lệ phát hiện (det) và cảnh báo (alert) trên biến thể của tấn công OOD và của tấn công đã biết."""
    thr = np.quantile(s_val, 0.95)
    mu, sd = sp["mu"], sp["sd"]
    groups = {"ood": sp["X_ood"], "known": sp["X_te"][sp["y_te"] != 0]}
    names = [(dilate, a, f"dilate{a}") for a in spec.dilate] + [(pad, b, f"pad{b}") for b in spec.pad]
    out = {}
    for fn, v, name in [(None, None, "goc")] + names:
        out[name] = {}
        for g, Xz in groups.items():
            raw = Xz * sd + mu
            Xv = Xz if fn is None else ((fn(raw, cols, v) - mu) / sd).astype(np.float32)
            s, p = scorer(Xv)
            res = {"det": float((s > thr).mean())}
            if p is not None:
                res["alert"] = float(((s > thr) | (p != 0)).mean())
            out[name][g] = res
    return out
