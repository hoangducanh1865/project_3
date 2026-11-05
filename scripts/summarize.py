"""Gom result.json thành bảng trung bình theo kịch bản và mô hình.

Dùng: python scripts/summarize.py <thư mục chứa các result.json> [file csv]
"""
import glob
import json
import sys

import pandas as pd

METRICS = {"atk_auroc": "AUROC", "atk_det_rate": "TPR", "atk_fpr_thr": "FPR", "tactic_acc": "Tactic"}


def load(root):
    rows = []
    for p in glob.glob(f"{root}/**/result.json", recursive=True):
        r = json.load(open(p))
        rows.append({"dataset": r["dataset"], "scenario": r["heldout"] or f"to {r['target']}", "model": r["model"],
                     "seed": r["seed"], **{k: r.get(k) for k in METRICS}})
    return pd.DataFrame(rows)


def main(root, out=None):
    df = load(root).rename(columns=METRICS)
    table = df.groupby(["dataset", "scenario", "model"])[list(METRICS.values())].mean()
    table["runs"] = df.groupby(["dataset", "scenario", "model"]).size()
    print(table.round(3).to_string())
    if out:
        table.round(4).to_csv(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
