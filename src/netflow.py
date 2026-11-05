"""Lấy mẫu các bộ NetFlow v3 (Sarhan và cộng sự, cùng 53 đặc trưng trên nhiều mạng) thành bảng số để dùng như LYCOS.

Bỏ IP, cổng và mã truy vấn DNS, số đo lấy log1p. Benign và mỗi họ tấn công giữ tối đa CAP dòng, sau khi trộn ngẫu nhiên
từng phần của file. Đổi nhãn dos thành dos_attack để khi giấu họ này chỉ khớp đúng một lớp (ddos cũng chứa chuỗi dos).
Dùng: python -m src.netflow <thư mục chứa NF-*-v3.csv> <thư mục ra>
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

FILES = {"nf_ton": "NF-ToN-IoT-v3.csv", "nf_cic": "NF-CICIDS2018-v3.csv"}
DROP = ["IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT", "Label", "FLOW_START_MILLISECONDS", "FLOW_END_MILLISECONDS", "DNS_QUERY_ID"]
CAP = 300_000
BENIGN_CAP = 900_000


def convert(path, seed=0):
    rng = np.random.default_rng(seed)
    kept, seen = {}, {}
    for ch in pd.read_csv(path, chunksize=1_000_000):
        ch = ch.astype({c: "float32" for c in ch.select_dtypes("float64").columns})
        for name, part in ch.groupby("Attack"):
            limit = BENIGN_CAP if name == "Benign" else CAP
            seen[name] = seen.get(name, 0) + len(part)
            kept.setdefault(name, []).append(part)
            if sum(map(len, kept[name])) > 3 * limit:   # giữ ngẫu nhiên, không lấy phần đầu file
                d = pd.concat(kept[name])
                kept[name] = [d.iloc[rng.permutation(len(d))[:limit]]]
    print(path, seen, flush=True)
    frames = []
    for name, parts in kept.items():
        d = pd.concat(parts)
        limit = BENIGN_CAP if name == "Benign" else CAP
        frames.append(d.iloc[rng.permutation(len(d))[:limit]])
    d = pd.concat(frames, ignore_index=True)
    label = d.pop("Attack").astype(str).str.lower().replace({"dos": "dos_attack"})
    d = d.drop(columns=DROP, errors="ignore").apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0)
    out = np.log1p(d.clip(lower=0)).astype("float32")
    out["label"] = label.to_numpy()
    return out


def main(src, out):
    os.makedirs(out, exist_ok=True)
    for name, f in FILES.items():
        convert(glob.glob(f"{src}/**/{f}", recursive=True)[0]).to_csv(f"{out}/{name}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
