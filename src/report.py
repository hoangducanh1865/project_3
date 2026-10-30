"""Gom result.json thành bảng Markdown. Dùng: python -m src.report --root $OUT_ROOT"""
import argparse
import glob
import json
import os

import pandas as pd

METRICS = ["auroc", "fpr95", "det_rate", "fpr_thr", "acc", "macro_f1", "fit_seconds"]
NAMES = {"auroc": "AUROC", "fpr95": "FPR95", "det_rate": "Tỉ lệ phát hiện OOD", "fpr_thr": "FPR tại ngưỡng",
         "acc": "Acc", "macro_f1": "Macro-F1", "fit_seconds": "Thời gian huấn luyện (s)"}

HC = {"auroc": "AUROC hợp nhất", "auroc_closr_only": "AUROC chỉ CLOSR", "auroc_knn_only": "AUROC chỉ KNN",
      "auroc_tactic_level": "AUROC mức chiến thuật", "tier1_known": "Known xếp tầng 1",
      "ood_tier1": "OOD tầng 1", "ood_tier2": "OOD tầng 2", "ood_tier3": "OOD tầng 3",
      "ood_tier_acc": "OOD đúng tầng", "ood_tactic_acc_tier2": "Đúng chiến thuật (tầng 2)"}


def load(root):
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "**", "result.json"), recursive=True)):
        r = json.load(open(p))
        r.pop("config", None)
        r["file"] = p
        rows.append(r)
    return pd.DataFrame(rows)


def build(df):
    out = ["# Kết quả baseline tuần 4", "",
           f"Số lần chạy: {len(df)}. Điểm cao hơn là bất thường hơn; OOD là lớp dương.",
           "FPR95: tỉ lệ known-test báo nhầm khi bắt được 95% OOD. Tỉ lệ phát hiện OOD và FPR tại ngưỡng: ngưỡng chọn "
           "từ phân vị 95 của dữ liệu known (val), không dùng dữ liệu OOD.", ""]
    df = df.copy()
    df["heldout"] = df["heldout"].fillna("-")
    for (proto, held), g in df.groupby(["protocol", "heldout"]):
        ood = ", ".join(g.iloc[0]["ood_classes"])
        out += [f"## {proto.upper()} – OOD: {ood}", ""]
        t = g.set_index("model")[[m for m in METRICS if m in g]].rename(columns=NAMES)
        out += [t.round(4).to_markdown(), ""]
    hc = [c for c in HC if c in df]
    if "auroc_knn_only" in df:
        g = df.dropna(subset=["auroc_knn_only"]).set_index(["protocol", "heldout"])[hc].rename(columns=HC)
        out += ["## HC-CLOSR: thành phần điểm, phân tầng và chiến thuật", "",
                "Tầng đúng của OOD: 2 nếu chiến thuật thật còn trong tập huấn luyện (biến thể), ngược lại 3.", "",
                g.round(4).to_markdown(), ""]
    p1 = df[df.protocol == "p1"]
    if len(p1):
        out += ["## P1: AUROC theo họ tấn công bị loại", "",
                p1.pivot_table(index="model", columns="heldout", values="auroc").round(4).to_markdown(), ""]
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("OUT_ROOT", "outputs"))
    a = ap.parse_args()
    df = load(a.root)
    if df.empty:
        raise SystemExit(f"không thấy result.json dưới {a.root}")
    md = build(df)
    open(os.path.join(a.root, "bao_cao_tuan4.md"), "w").write(md)
    df.to_csv(os.path.join(a.root, "results.csv"), index=False)
    print(md)
