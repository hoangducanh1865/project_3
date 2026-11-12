"""Nạp dữ liệu và tách theo kịch bản đánh giá: giấu một họ tấn công, lớp hiếm, chéo tập dữ liệu."""
import os

import numpy as np
import pandas as pd


def _norm(s):
    """Chuẩn hóa tên lớp để so khớp: chữ thường, chỉ giữ chữ và số."""
    return "".join(c for c in str(s).lower() if c.isalnum())


def tactic_of(name, tactics):
    """Chiến thuật ATT&CK của một lớp theo bảng conf/dataset/*.yaml; lớp không khớp mục nào là benign."""
    hit = {t for t, keys in tactics.items() for k in keys if _norm(k) in _norm(name)}
    if len(hit) > 1:
        raise ValueError(f"lớp {name} khớp nhiều chiến thuật: {hit}")
    return hit.pop() if hit else "benign"


def _read_table(ds):
    """Đọc CSV. Với file rất lớn (ds.benign_frac): đọc từng phần, chỉ giữ một tỉ lệ lưu lượng bình thường."""
    frac = ds.get("benign_frac")
    if str(ds.path).endswith(".parquet"):
        return pd.read_parquet(ds.path)
    if not frac:
        return pd.read_csv(ds.path)
    rng = np.random.default_rng(0)
    parts = []
    for ch in pd.read_csv(ds.path, chunksize=1_000_000):
        ben = ch[ds.label_col].astype(str).map(_norm) == _norm(ds.benign)
        ch = ch[~ben.to_numpy() | (rng.random(len(ch)) < frac)]
        parts.append(ch.astype({c: "float32" for c in ch.select_dtypes("float64").columns}))
    return pd.concat(parts, ignore_index=True)


def load_csv(ds):
    """Trả về (X float32, y chuỗi). Dùng cache .npz để các lần chạy sau nhanh hơn."""
    if os.path.exists(ds.cache):
        z = np.load(ds.cache, allow_pickle=False)
        return z["X"], z["y"]
    df = _read_table(ds)
    y = df.pop(ds.label_col).astype(str).to_numpy().astype(str)  # chuỗi độ dài cố định, lưu được vào npz
    df = df.drop(columns=list(ds.drop_cols), errors="ignore").select_dtypes("number")
    cols = df.columns.to_numpy().astype(str)
    X = df.to_numpy(dtype=np.float32)
    del df
    ok = np.isfinite(X).all(axis=1)
    print(f"bỏ {(~ok).sum()} dòng có NaN/Inf trên tổng {len(ok)}")
    X, y = X[ok], y[ok]
    keep = X.std(axis=0) > 0  # bỏ cột hằng
    X = X[:, keep]
    np.savez(ds.cache, X=X, y=y, cols=cols[keep], rows=np.flatnonzero(ok))
    return X, y


def load_columns(ds):
    """Tên cột của X và vị trí từng dòng của X trong file CSV gốc (đọc từ cache do load_csv tạo)."""
    z = np.load(ds.cache, allow_pickle=False)
    return z["cols"].tolist(), z["rows"]


def class_table(y):
    names, counts = np.unique(y, return_counts=True)
    return dict(zip(names.tolist(), counts.tolist()))


def make_split(X, y, ds, proto, eval_cap, seed):
    """Tách known-train/val/test và tập OOD. Lớp 0 luôn là lưu lượng bình thường.

    Có proto.heldout: OOD là họ tấn công đó, các lớp hiếm bị bỏ. Không có: OOD là các lớp hiếm.
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
        "X_va": z(va), "y_va": yk[va], "X_te": z(te), "y_te": yk[te], "X_ood": z(ood),
        "classes": [names[i] for i in known],
        "ood_classes": [names[i] for i in ood_ids], "ood_names": names[inv[ood]],
        "mu": mu, "sd": sd, "idx_te": te, "idx_ood": ood,
    }


def align_target(Zt, Zs, mode):
    """Hiệu chỉnh mạng đích: đưa đặc trưng mạng đích về thang của mạng nguồn, chỉ dùng flow không nhãn của mạng đích."""
    if mode == "z":
        m, s = Zt.mean(0), Zt.std(0) + 1e-6
        return lambda Z: (Z - m) / s
    q = np.linspace(0, 1, 201)
    Qt, Qs = np.quantile(Zt, q, axis=0) + q[:, None] * 1e-6, np.quantile(Zs, q, axis=0)  # cộng để Qt tăng ngặt
    return lambda Z: np.stack([np.interp(Z[:, j], Qt[:, j], Qs[:, j]) for j in range(Z.shape[1])], 1)


def cross_split(sp, Xt, yt, dt, eval_cap, per_class, seed, align=None):
    """Chéo tập dữ liệu: `sp` là phép tách trên mạng nguồn. Thay phần kiểm thử bằng dữ liệu mạng đích, chuẩn hoá theo mạng nguồn.

    Known-test là lưu lượng bình thường của mạng đích. OOD là mọi tấn công của mạng đích, tối đa per_class mẫu mỗi lớp.
    align (z, quantile): hiệu chỉnh thêm theo 200.000 flow không nhãn lấy ngẫu nhiên ở mạng đích.
    """
    rng = np.random.default_rng(seed)
    ben = np.array([_norm(n) == _norm(dt.benign) for n in yt])
    idx_b = rng.permutation(np.flatnonzero(ben))[:eval_cap]
    idx_a = np.concatenate([rng.permutation(np.flatnonzero(yt == c))[:per_class] for c in np.unique(yt[~ben])])
    z = lambda idx: ((Xt[idx] - sp["mu"]) / sp["sd"]).astype(np.float32)
    if align:
        fix = align_target(z(rng.permutation(len(Xt))[:200000]), sp["X_tr"], align)
        base, z = z, lambda idx: fix(base(idx)).astype(np.float32)
    return {**sp, "X_te": z(idx_b), "y_te": np.zeros(len(idx_b), dtype=np.int64), "X_ood": z(idx_a),
            "ood_classes": np.unique(yt[idx_a]).tolist(), "ood_names": yt[idx_a]}


def drop_named(sp, parts, cols):
    """Bỏ các cột có tên chứa một trong các chuỗi, dùng cho đặc trưng phụ thuộc ngăn xếp TCP."""
    hit = [any(p in c for p in parts) for c in cols]
    keep = np.flatnonzero(~np.array(hit))
    out = {**sp, "mu": sp["mu"][keep], "sd": sp["sd"][keep]}
    for key in ("X_tr", "X_va", "X_te", "X_ood"):
        out[key] = sp[key][:, keep]
    return out, [cols[i] for i in keep], [c for c, h in zip(cols, hit) if h]
