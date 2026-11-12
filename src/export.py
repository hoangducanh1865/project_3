"""Xuất mô hình HC-CLOSR đã huấn luyện và lưu lượng mẫu để web demo dùng (xem deploy/modal_app.py)."""
import json
import os

import numpy as np
import pandas as pd
import torch

from .data import load_columns

KEEP = ("auroc", "fpr95", "det_rate", "fpr_thr", "acc", "macro_f1", "n_train", "heldout", "seed", "ood_tier1",
        "ood_tier2", "ood_tier3")


def pick_samples(y, sp, seed, n_benign=200, n_known=10, n_ood=40, n_unseen=5):
    """Chỉ lấy flow không dùng để huấn luyện: known-test, OOD và các lớp hiếm bị bỏ khỏi tập huấn luyện."""
    rng = np.random.default_rng(seed)
    te, ood = sp["idx_te"], sp["idx_ood"]
    known = [str(c) for c in sp["classes"]]
    picks = [rng.permutation(te[y[te] == known[0]])[:n_benign]]
    picks += [rng.permutation(te[y[te] == c])[:n_known] for c in known[1:]]
    picks.append(rng.permutation(ood)[:n_ood])
    unseen = sorted(set(np.unique(y).tolist()) - set(known) - {str(c) for c in sp["ood_classes"]})
    picks += [rng.permutation(np.flatnonzero(y == c))[:n_unseen] for c in unseen]
    return rng.permutation(np.concatenate(picks))


def export(cfg, scorer, sp, y, res):
    os.makedirs(cfg.artifact_dir, exist_ok=True)
    det = scorer.detector
    columns, rows = load_columns(cfg.dataset)
    det.info.update(columns=columns, metrics={k: res.get(k) for k in KEEP},
                    ood_classes=[str(c) for c in sp["ood_classes"]])
    torch.save(det.state(), os.path.join(cfg.artifact_dir, "model.pt"))

    idx = pick_samples(y, sp, cfg.seed)
    if str(cfg.dataset.path).endswith(".parquet"):
        df = pd.read_parquet(cfg.dataset.path).iloc[np.sort(rows[idx])]
    else:
        want = set(rows[idx].tolist())
        keep = lambda i: i != 0 and i - 1 not in want   # dòng 0 là tiêu đề
        df = pd.read_csv(cfg.dataset.path, skiprows=keep)
    df.to_json(os.path.join(cfg.artifact_dir, "samples.json"), orient="split", index=False)
    with open(os.path.join(cfg.artifact_dir, "metrics.json"), "w") as f:
        json.dump(det.info["metrics"], f, ensure_ascii=False, indent=2, default=str)
    print(f"đã xuất {len(df)} flow mẫu và mô hình vào {cfg.artifact_dir}", flush=True)
