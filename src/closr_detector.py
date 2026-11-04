"""CLOSR của [16] với trọng số gốc: nhận ra họ tấn công đã biết và phát hiện OOD.

Mô hình này không có đầu chiến thuật nên không có tầng 2: flow lạ luôn là tầng 3. File trọng số không chứa tâm lớp và
tham số chuẩn hoá, nên build() tính lại từ tập train theo đúng cách chia của mã gốc (data/load_data.py, eval_closr.py).
"""
import json
import os
import random

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from .models import _chunks, _repo, _t, tactic_of
from .response import L_KNOWN, likelihood, respond

DROP = ["flow_id", "src_addr", "src_port", "dst_addr", "dst_port", "ip_prot", "timestamp"]
SPLIT_SEED = 39058032   # mặc định của eval_closr.py
RARE = 100              # sample_thres của mã gốc
ARCH = {"d_in": 72, "n_heads": 12, "d_out": 64, "neurons": [1024, 1024, 1024], "dropout": 0.1}


def make_model(dev):
    _repo()
    from model.model import CLOSRMLP
    return CLOSRMLP(d_in=ARCH["d_in"], n_classes=ARCH["n_heads"], d_out=ARCH["d_out"], neurons=ARCH["neurons"],
                    dropout=ARCH["dropout"], residual=False).to(dev)


class CLOSRDetector:
    has_tier2 = False

    def __init__(self, model, cents, thr, s_cal, info, dev="cpu"):
        self.model, self.cents, self.thr, self.s_cal, self.info, self.dev = model, cents, thr, s_cal, info, dev

    @torch.no_grad()
    def score(self, Xz):
        """-> (điểm OOD, lớp dự đoán). Công thức open-set của eval_closr.py, điểm cao là bất thường hơn."""
        sims = torch.cat([(F.normalize(self.model(_t(Xz[s], self.dev)), dim=-1) * self.cents[None]).sum(-1)
                          for s in _chunks(len(Xz), 4096)])
        osr = (sims ** 2 * sims.softmax(-1)).sum(-1)
        return (-osr).cpu().numpy(), sims.argmax(-1).cpu().numpy()

    def analyze(self, X):
        i = self.info
        s, pred = self.score(((X - i["mu"]) / i["sd"]).astype(np.float32))
        L = likelihood(s, self.s_cal)
        out = []
        for n in range(len(s)):
            fam = i["classes"][pred[n]]
            base = {"family": fam, "score": round(float(s[n]), 3)}
            if s[n] > self.thr:
                out.append({**base, "status": "alert", **respond(3, "unknown", int(L[n]), i["impact"])})
            elif pred[n] == 0:      # lớp 0 luôn là lưu lượng bình thường
                out.append({**base, "tier": 1, "status": "normal"})
            else:
                out.append({**base, "status": "alert", **respond(1, i["fam_tac"][pred[n]], L_KNOWN, i["impact"])})
        return out

    def state(self):
        return {"weights": {k: v.cpu() for k, v in self.model.state_dict().items()}, "cents": self.cents.cpu(),
                "thr": self.thr, "s_cal": self.s_cal, "info": self.info}

    @classmethod
    def from_state(cls, st, dev="cpu"):
        model = make_model(dev)
        model.load_state_dict(st["weights"])
        model.eval()
        return cls(model, st["cents"].to(dev), st["thr"], st["s_cal"], st["info"], dev)


def build(csv, weights, out_dir, tactics, impact, dev, seed=0, n_benign=200, n_known=10):
    """Dựng detector từ trọng số gốc: chia dữ liệu như mã gốc, tính tâm lớp, chọn ngưỡng và đánh giá."""
    from sklearn.metrics import f1_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(csv)
    y = df["label"].to_numpy().astype(str)
    feats = df.drop(columns=DROP + ["label"])
    X = feats.to_numpy()
    keep = ~np.all(X == 0, axis=0)      # mã gốc chỉ bỏ cột toàn số 0
    X, columns = X[:, keep], feats.columns[keep].tolist()
    assert X.shape[1] == ARCH["d_in"], X.shape

    names, counts = np.unique(y, return_counts=True)
    rare = names[counts < RARE].tolist()
    classes = ["benign"] + [c for c in names.tolist() if c != "benign" and c not in rare]
    assert len(classes) == ARCH["n_heads"], classes
    lookup = {c: i for i, c in enumerate(classes)}
    known = np.flatnonzero(~np.isin(y, rare))
    y_known = np.array([lookup[c] for c in y[known]])

    seeds = random.Random(SPLIT_SEED)
    tr, te = train_test_split(known, test_size=0.5, random_state=seeds.randint(0, 2 ** 32 - 1), shuffle=True,
                              stratify=y_known)
    mu, sd = X[tr].mean(axis=0), X[tr].std(axis=0, ddof=1)
    assert (sd > 0).all(), "có cột không đổi trong tập train"
    z = lambda idx: ((X[idx] - mu) / sd).astype(np.float32)

    model = make_model(dev)
    model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=False)["model_state_dict"])
    model.eval()

    # tâm lớp như util/distance.py: trung bình các embedding đã chuẩn hoá trên đầu của chính lớp đó
    ztr, ytr = z(tr), _t(np.array([lookup[c] for c in y[tr]]), dev)
    sums = torch.zeros(ARCH["n_heads"], ARCH["d_out"], device=dev)
    with torch.no_grad():
        for s in _chunks(len(ztr), 4096):
            e, yb = model(_t(ztr[s], dev)), ytr[s]
            for c in range(ARCH["n_heads"]):
                sums[c] += F.normalize(e[yb == c, c], dim=-1).sum(0)
    cents = F.normalize(sums, dim=-1)

    # nửa tập test để chọn ngưỡng (chỉ dữ liệu known), nửa còn lại để đánh giá
    cal, ev = train_test_split(te, test_size=0.5, random_state=seed, stratify=y[te])
    det = CLOSRDetector(model, cents, 0.0, None, {}, dev)
    det.s_cal, _ = det.score(z(cal))
    det.thr = float(np.quantile(det.s_cal, 0.95))
    ood = np.flatnonzero(np.isin(y, rare))
    s_ev, p_ev = det.score(z(ev))
    s_ood, _ = det.score(z(ood))
    y_ev = np.array([lookup[c] for c in y[ev]])
    metrics = {
        "auroc": float(roc_auc_score(np.r_[np.zeros(len(s_ev)), np.ones(len(s_ood))], np.r_[s_ev, s_ood])),
        "det_rate": float((s_ood > det.thr).mean()), "fpr_thr": float((s_ev > det.thr).mean()),
        "acc": float((p_ev == y_ev).mean()), "macro_f1": float(f1_score(y_ev, p_ev, average="macro")),
        "n_train": len(tr), "n_ood": len(ood),
    }
    det.info = {"classes": classes, "fam_tac": [tactic_of(c, tactics) for c in classes], "impact": dict(impact),
                "mu": mu.astype(np.float32), "sd": sd.astype(np.float32), "columns": columns, "metrics": metrics,
                "ood_classes": rare}

    os.makedirs(out_dir, exist_ok=True)
    torch.save(det.state(), os.path.join(out_dir, "model.pt"))
    rng = np.random.default_rng(seed)
    picks = [rng.permutation(ev[y[ev] == c])[:(n_benign if c == "benign" else n_known)] for c in classes] + [ood]
    rows = rng.permutation(np.concatenate(picks))
    df.iloc[rows].to_json(os.path.join(out_dir, "samples.json"), orient="split", index=False)
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    return metrics
