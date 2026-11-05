"""Thử kết hợp điểm tấn công và cách chọn chiến thuật cho OOD trên điểm đã lưu, không huấn luyện lại.

Điểm khoảng cách tới tâm và KNN của mạng nơ-ron được đổi thành -log p-value thực nghiệm so với flow bình thường ở val
rồi kết hợp theo Fisher. XGBoost và các đối chứng chỉ để so sánh, không gộp vào điểm.
Dùng (từ gốc repo): python scripts/fuse.py <thư mục jobs> [model mạng nơ-ron]
"""
import collections
import glob
import json
import os
import sys

import numpy as np
from omegaconf import OmegaConf
from sklearn.metrics import roc_auc_score

sys.path.insert(0, ".")
from src.models import tactic_of  # noqa: E402


def load(root):
    runs = collections.defaultdict(dict)
    for p in glob.glob(f"{root}/*/scores.npz"):
        r = json.load(open(os.path.join(os.path.dirname(p), "result.json")))
        c = r["config"]
        name = r["model"] + (f"_e{c['model']['epochs']}" if c["model"].get("epochs", 10) != 10 else "") \
            + (f"_w{c['model']['tactic_weight']}" if c["model"].get("tactic_weight", 1) != 1 else "")
        key = (c["dataset"]["name"], r["protocol"], str(r["heldout"]), c["protocol"].get("align"),
               bool(r["dropped_features"]), r["seed"])
        runs[key][name] = (r, p)
    return runs


def survival(a, ref):
    ref = np.sort(ref)
    return -np.log((len(ref) - np.searchsorted(ref, a, side="left") + 1) / (len(ref) + 1))


def report(te, ood, va):
    thr = np.quantile(va, 0.95)
    y = np.r_[np.zeros(len(te)), np.ones(len(ood))]
    return roc_auc_score(y, np.r_[te, ood]), float((ood > thr).mean()), float((te > thr).mean())


def split(z, fn):
    """fn(tiền tố) -> điểm trên một phần; trả về (te chỉ flow bình thường, ood, va chỉ flow bình thường)."""
    return fn("te")[z["y_te"] == 0], fn("ood"), fn("va")[z["y_va"] == 0]


def nb(z, name):
    """Các điểm tấn công của một mạng nơ-ron."""
    cos = split(z, lambda a: -z[f"{a}_sim_fam"][:, 0])
    knn = split(z, lambda a: z[f"{a}_knn_fam"][:, 0])
    join = [survival(x, cos[2]) + survival(y, knn[2]) for x, y in zip(cos, knn)]
    return {f"{name}.cos": cos, f"{name}.knn": knn, f"{name}.cos+knn": tuple(join)}


def tactics_of(r):
    t = r["config"]["dataset"]["tactics"]
    target = r["config"]["protocol"].get("target")
    if target:      # P2: tên họ của mạng đích tra theo bảng của mạng đích
        t = OmegaConf.load(f"conf/dataset/{target}.yaml").tactics
    return OmegaConf.create(OmegaConf.to_container(t) if OmegaConf.is_config(t) else t)


def tactic_rows(r, z, zx):
    """Độ chính xác chiến thuật trên các flow OOD có chiến thuật còn trong tập huấn luyện, buộc phải chọn chiến thuật tấn công."""
    src = r["config"]["dataset"]["tactics"]
    fam = np.array([tactic_of(c, src) for c in z["classes"]])
    names = np.array(sorted(set(fam) - {"benign"}))
    tab = tactics_of(r)
    true = np.array([tactic_of(n, tab) for n in z["ood_names"]])
    keep = np.isin(true, names)
    if not keep.any():
        return None
    acc = lambda pred: float((pred[keep] == true[keep]).mean())
    out = {"n": int(keep.sum()), "ngẫu nhiên": 1 / len(names),
           "nb.tâm chiến thuật": acc(names[z["ood_sim_tac"][:, 1:].argmax(1)]),
           "nb.KNN chiến thuật": acc(names[z["ood_knn_tac"][:, 1:].argmin(1)]),
           "nb.tâm họ": acc(fam[1 + z["ood_sim_fam"][:, 1:].argmax(1)]),
           "nb.KNN họ": acc(fam[1 + z["ood_knn_fam"][:, 1:].argmin(1)])}
    if zx is not None:
        out["xgb"] = acc(fam[1 + zx["ood_proba"][:, 1:].argmax(1)])
    return out


def main(root, neural="hc_closr"):
    runs = load(root)
    table, tact = {}, {}
    for key, ms in sorted(runs.items(), key=str):
        if neural not in ms:
            continue
        r, p = ms[neural]
        z = np.load(p)
        row = dict(nb(z, "nb"))
        zx = None
        if "xgboost" in ms:
            zx = np.load(ms["xgboost"][1])
            if not (np.array_equal(zx["y_va"], z["y_va"]) and len(zx["ood_names"]) == len(z["ood_names"])):
                raise ValueError(f"{key}: hai mô hình không cùng phép tách")
            x = split(zx, lambda a: 1 - zx[f"{a}_proba"][:, 0])
            row["xgb"] = x
        table[key] = {n: report(*v) for n, v in row.items()}
        for n in ("raw_knn", "iforest"):    # đối chứng chỉ học lưu lượng bình thường
            if n in ms:
                za = np.load(ms[n][1])
                table[key][n] = report(*split(za, lambda a: za[f"{a}_attack"]))
        tact[key] = tactic_rows(r, z, zx)

    with open(os.path.join(root, "..", "fuse.json"), "w") as f:
        json.dump({"table": [[list(map(str, k)), v] for k, v in table.items()],
                   "tactics": [[list(map(str, k)), v] for k, v in tact.items()]}, f, ensure_ascii=False)
    names = sorted({n for v in table.values() for n in v})
    print("kịch bản".ljust(38) + "".join(n.rjust(16) for n in names))
    for k, v in table.items():
        print("/".join(map(str, k)).ljust(38) + "".join(
            (" ".join(f"{x:.2f}" for x in v[n]) if n in v else "-").rjust(16) for n in names))
    both = [v for v in table.values() if "xgb" in v]
    print("\nTrung bình AUROC, số kịch bản hơn XGBoost từ 0,005, thua từ 0,005:")
    for n in names if both else []:
        d = [v[n][0] - v["xgb"][0] for v in both if n in v]
        print(f"  {n:18s} {np.mean([v[n][0] for v in both if n in v]):.3f}  hơn {sum(x >= .005 for x in d)}  "
              f"thua {sum(x <= -.005 for x in d)}  kém nhất {min(d):+.3f}  FPR tb {np.mean([v[n][2] for v in both if n in v]):.3f}")
    print("\nChiến thuật OOD:")
    for k, v in tact.items():
        if v:
            print("/".join(map(str, k)).ljust(38), {a: round(b, 3) for a, b in v.items()})


if __name__ == "__main__":
    main(*sys.argv[1:])
