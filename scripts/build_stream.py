"""Dựng dữ liệu cho web từ DataSense: kho flow (pool.npz), kịch bản và thẻ mô tả (card.json).

Chạy trên Colab sau khi huấn luyện mô hình web (cùng họ bị giấu và seed):
    python scripts/build_stream.py --data $DATA/datasense --model $ART/hc_closr --heldout <họ> --out $ART/stream
Rồi nạp: modal volume put project3-model $ART/stream /stream
"""
import argparse
import json
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd
from omegaconf import OmegaConf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.data import load_columns, load_csv, make_split, tactic_of  # noqa: E402
from src.simulator import build_pool  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
RULES = [
    "Flow chạm IP hoặc MAC của 6 máy tấn công (192.168.1.100 đến .105), nằm trong khung thời gian của lần tấn công "
    "(attacks.csv, dung sai 2 giây) và đầu còn lại là thiết bị mục tiêu: gán họ tấn công.",
    "Họ quét và Mirai nhắm nhiều máy: chỉ cần chạm máy tấn công trong khung thời gian.",
    "Họ giả IP nguồn (land flood, ip-spoofing): flow tới mục tiêu trong khung thời gian, IP nguồn không thuộc thiết bị "
    "đã biết hoặc trùng IP đích: gán họ tấn công.",
    "Flow trong tệp tấn công không chạm máy tấn công: lưu lượng nền của thiết bị, gán bình thường.",
    "Flow chạm máy tấn công nhưng ngoài khung thời gian hoặc tới máy không phải mục tiêu: không rõ, bỏ.",
]


def relabel_table(data):
    r = pd.read_csv(f"{data}/relabel_all.csv")
    r["cat"] = r.file.str.split("_").str[1]
    out = []
    for cat, g in r.groupby("cat"):
        tot = int(g.n.sum())
        ben = int(g[g.label == "benign"].n.sum())
        drop = int(g[g.label.isna()].n.sum())
        out.append({"category": cat, "files": int(g.file.nunique()), "flows": tot, "attack": tot - ben - drop,
                    "benign": ben, "dropped": drop})
    return out


def main(a):
    ds = OmegaConf.load(os.path.join(ROOT, "conf/dataset/datasense.yaml"))
    ds.path, ds.cache = f"{a.data}/datasense_flows.parquet", "/tmp/datasense_cache.npz"
    X, y = load_csv(ds)
    columns, rows = load_columns(ds)
    sp = make_split(X, y, ds, {"heldout": a.heldout}, 10 ** 9, a.seed)
    os.makedirs(a.out, exist_ok=True)
    counts = build_pool(X, y, rows, columns, sp, f"{a.out}/pool.npz", ds.path)
    shutil.copy(os.path.join(ROOT, "deploy/scenarios.json"), f"{a.out}/scenarios.json")

    import torch
    st = torch.load(f"{a.model}/model.pt", map_location="cpu", weights_only=False)
    info = st["info"]
    dev = pd.read_csv(f"{a.data}/devices.csv")
    att = pd.read_csv(f"{a.data}/attacks.csv")
    card = {
        "version": time.strftime("%Y%m%d%H%M%S"),
        "dataset": {
            "name": "DataSense: CIC IIoT Dataset 2025", "url": "https://www.unb.ca/cic/datasets/iiot-dataset-2025.html",
            "paper": "A. Firouzi, S. Dadkhah, S. A. Maret, A. A. Ghorbani, Electronics 14(20), 4095, 2025",
            "captured": [pd.to_datetime(att.start_timestamp.min(), unit="ms").strftime("%d/%m/%Y"),
                         pd.to_datetime(att.end_timestamp.max(), unit="ms").strftime("%d/%m/%Y")],
            "devices": len(dev), "attackers": int((dev.role == "attacker").sum()),
            "flows": int(len(y)), "classes": {str(k): int(v) for k, v in zip(*np.unique(y, return_counts=True))},
            "extractor": "NFStream 6.6 (flow hai chiều, idle 120 s, active 1800 s)",
        },
        "relabel": {"rules": RULES, "table": relabel_table(a.data)},
        "model": {
            "name": "HC-CLOSR", "heldout": a.heldout, "seed": a.seed, "trained": time.strftime("%d/%m/%Y"),
            "classes": [str(c) for c in info["classes"]], "n_features": len(info["columns"]),
            "features": info["columns"], "metrics": info["metrics"],
            "threshold": {"quantile": 0.95, "value": round(float(st["thr"]["fam"]), 3),
                          "meaning": "phân vị 95 của điểm OOD trên flow đã biết ở tập val: 5% flow đã biết bị coi là OOD"},
            "tactics": {str(c): tactic_of(c, ds.tactics) for c in info["classes"]} | {a.heldout: tactic_of(a.heldout, ds.tactics)},
        },
        "pool": counts,
        "devices": dev[["ip", "device_name", "role", "type"]].to_dict("records"),
    }
    with open(f"{a.out}/card.json", "w") as f:
        json.dump(card, f, ensure_ascii=False, indent=1, default=str)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--heldout", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    main(ap.parse_args())
