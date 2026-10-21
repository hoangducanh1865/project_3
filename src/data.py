"""Nạp LYCOS-IDS2017 và tách dữ liệu theo giao thức P0/P1."""
import os

import numpy as np
import pandas as pd


def _norm(s):
    """Chuẩn hóa tên lớp để so khớp: chữ thường, chỉ giữ chữ và số."""
    return "".join(c for c in str(s).lower() if c.isalnum())


def load_csv(ds):
    """Trả về (X float32, y chuỗi). Dùng cache .npz để các lần chạy sau nhanh hơn."""
    if os.path.exists(ds.cache):
        z = np.load(ds.cache, allow_pickle=False)
        return z["X"], z["y"]
    df = pd.read_csv(ds.path)
    y = df.pop(ds.label_col).astype(str).to_numpy().astype(str)  # chuỗi độ dài cố định, lưu được vào npz
    df = df.drop(columns=list(ds.drop_cols), errors="ignore")
    X = df.select_dtypes("number").to_numpy(dtype=np.float32)
    del df
    ok = np.isfinite(X).all(axis=1)
    print(f"bỏ {(~ok).sum()} dòng có NaN/Inf trên tổng {len(ok)}")
    X, y = X[ok], y[ok]
    X = X[:, X.std(axis=0) > 0]  # bỏ cột hằng
    np.savez(ds.cache, X=X, y=y)
    return X, y


def class_table(y):
    names, counts = np.unique(y, return_counts=True)
    return dict(zip(names.tolist(), counts.tolist()))


def make_split(X, y, ds, proto, eval_cap, seed):
    """Tách known-train/val/test và tập OOD.

    P0: OOD là các lớp hiếm. P1: OOD là họ tấn công `proto.heldout`, các lớp hiếm bị bỏ.
    Lớp 0 luôn là lưu lượng bình thường.
    """
    rng = np.random.default_rng(seed)
    names, inv = np.unique(y, return_inverse=True)
    counts = np.bincount(inv)
    norm = [_norm(n) for n in names]
    if _norm(ds.benign) not in norm:
        raise ValueError(f"không thấy lớp bình thường '{ds.benign}' trong {class_table(y)}")
    benign = norm.index(_norm(ds.benign))

    heldout = proto.get("heldout")
    if heldout:
        ood_ids = [i for i, n in enumerate(norm) if _norm(heldout) in n]
        if len(ood_ids) != 1:
            raise ValueError(f"heldout='{heldout}' khớp {len(ood_ids)} lớp. Các lớp: {class_table(y)}")
    else:
        ood_ids = [i for i in range(len(names)) if counts[i] < ds.rare_threshold]
    known = [benign] + [i for i in range(len(names))
                        if i != benign and counts[i] >= ds.rare_threshold and i not in ood_ids]

    remap = np.full(len(names), -1, dtype=np.int64)
    remap[known] = np.arange(len(known))
    yk = remap[inv]
    tr, va, te = [], [], []
    for k in range(len(known)):
        idx = rng.permutation(np.flatnonzero(yk == k))
        n_te = len(idx) // 2
        n_va = max(1, int(0.05 * len(idx)))
        te.append(idx[:n_te])
        va.append(idx[n_te:n_te + n_va])
        tr.append(idx[n_te + n_va:][: ds.max_per_class])
    tr, va, te = map(np.concatenate, (tr, va, te))
    ood = np.flatnonzero(np.isin(inv, ood_ids))

    def cap(idx):
        return rng.permutation(idx)[:eval_cap] if len(idx) > eval_cap else idx

    va, te, ood = cap(va), cap(te), cap(ood)
    mu, sd = X[tr].mean(0), X[tr].std(0)
    sd[sd == 0] = 1.0
    z = lambda idx: ((X[idx] - mu) / sd).astype(np.float32)
    return {
        "X_tr": z(tr), "y_tr": yk[tr],
        "X_va": z(va), "X_te": z(te), "y_te": yk[te], "X_ood": z(ood),
        "classes": [names[i] for i in known],
        "ood_classes": [names[i] for i in ood_ids],
    }
