"""Danh mục nguồn dữ liệu cho web: thiết bị (devices.csv) và từng tệp PCAP với thời gian thu, mục tiêu, kết quả gán nhãn lại.

Dùng: python scripts/build_sources.py --data <thư mục DataSense đã trích> --out web/public/live/sources.json
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.datasense import family_of  # noqa: E402


def main(a):
    dev = pd.read_csv(f"{a.data}/devices.csv")
    att = pd.read_csv(f"{a.data}/attacks.csv")
    att = att.groupby("filename", as_index=False).agg(
        category=("category", "first"), attack_name=("attack_name", "first"), target=("attack_target", "first"),
        start=("start_timestamp", "min"), end=("end_timestamp", "max"))
    rel = pd.read_csv(f"{a.data}/relabel_all.csv")
    rel["kind"] = rel.label.fillna("dropped").where(rel.label.isna() | (rel.label == "benign"), "attack")
    counts = rel.pivot_table(index="file", columns="kind", values="n", aggfunc="sum", fill_value=0)
    files = []
    for r in att.itertuples():
        if r.filename not in counts.index:
            continue      # tệp chưa đọc (DoS, DDoS chỉ đọc một phần)
        c = counts.loc[r.filename]
        fam = None if r.category == "benign" else family_of(r.attack_name)
        files.append({"file": r.filename, "category": r.category, "attack": r.attack_name, "family": fam,
                      "targets": [t for part in str(r.target).split("--") for t in part.split(",")],
                      "start": int(r.start), "end": int(r.end), "flows": int(c.sum()),
                      "attack_flows": int(c.get("attack", 0)), "benign_flows": int(c.get("benign", 0)),
                      "dropped": int(c.get("dropped", 0))})
    out = {"dataset": "DataSense CIC IIoT 2025", "capture": "PCAP thu trên mạng testbed, mỗi tệp một lần tấn công",
           "devices": dev[["ip", "mac", "device_name", "role", "type"]].fillna("").to_dict("records"),
           "files": sorted(files, key=lambda f: f["start"]), "unread": int(len(att) - len(files))}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), ensure_ascii=False)
    print(len(files), "tệp,", out["unread"], "tệp chưa đọc,", os.path.getsize(a.out) // 1024, "KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    main(ap.parse_args())
