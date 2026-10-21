"""Gom result.json thành bảng Markdown. Dùng: python -m src.report --root $OUT_ROOT"""
import argparse
import glob
import json
import os

import pandas as pd

METRICS = ["auroc", "fpr95", "det_rate", "fpr_thr", "acc", "macro_f1", "fit_seconds"]
NAMES = {"auroc": "AUROC", "fpr95": "FPR95", "det_rate": "Tỉ lệ phát hiện OOD", "fpr_thr": "FPR tại ngưỡng",
         "acc": "Acc", "macro_f1": "Macro-F1", "fit_seconds": "Thời gian huấn luyện (s)"}


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
