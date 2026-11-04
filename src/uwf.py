"""Tải các bộ UWF-ZeekData (datasets.uwf.edu) và gộp thành bảng số để dùng như LYCOS.

Mỗi flow là một dòng Zeek conn.log, nhãn là kỹ thuật ATT&CK do nhóm tác giả gán. Bỏ IP và cổng, số đo lấy log1p, trạng
thái kết nối và dịch vụ mã hoá one-hot, chuỗi history đếm theo ký tự. Một flow có nhiều chiến thuật xuất hiện lặp lại
(nhãn Duplicate): giữ một dòng theo uid. Dùng: python -m src.uwf <thư mục ra>
"""
import io
import os
import re
import sys
import urllib.request

import numpy as np
import pandas as pd

BASE = "https://datasets.uwf.edu/data"
SPLITS = {"uwf": ["UWF-ZeekDataFall22", "UWF-ZeekData24", "UWF-ZeekDataFall24-2"],
          "uwf25": ["UWF-ZeekDataSum25-1", "UWF-ZeekDataSum25-2"]}
NUM = ["duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts", "orig_ip_bytes", "resp_ip_bytes", "missed_bytes"]
STATES = ["S0", "S1", "S2", "S3", "SF", "REJ", "RSTO", "RSTR", "RSTOS0", "RSTRH", "SH", "SHR", "OTH"]
SERVICES = ["http", "ssl", "dns", "ssh", "ftp", "smb", "krb", "dce_rpc", "ntlm", "gssapi"]
HISTORY = "ShADadFfRrTtQq"
CAP = 300_000       # số dòng tối đa mỗi nhãn ở mỗi bộ, đủ lớn so với max_per_class khi huấn luyện


def links(url):
    html = urllib.request.urlopen(url, timeout=120).read().decode()
    return [h for h in re.findall(r'href="([^"]+)"', html) if not h.startswith((".", "_"))]


def features(d):
    out = pd.DataFrame({c: np.log1p(pd.to_numeric(d[c], errors="coerce").fillna(0).astype("float32")) for c in NUM})
    for p in ("tcp", "udp", "icmp"):
        out[f"proto_{p}"] = (d["proto"] == p).astype("float32")
    for s in STATES:
        out[f"state_{s}"] = (d["conn_state"] == s).astype("float32")
    service = d["service"].astype(str)
    for s in SERVICES:
        out[f"service_{s}"] = service.str.contains(s, regex=False).astype("float32")
    history = d["history"].astype(str)
    for ch in HISTORY:
        out[f"hist_{ch}"] = history.str.count(ch).astype("float32")
    out["timestamp"] = (pd.to_numeric(d["ts"]) * 1e6).astype("int64")
    out["label"] = d["label_technique"].astype(str).str.lower().to_numpy()
    return out


def load(name, seed=0):
    parts = []
    root = f"{BASE}/{name}/parquet"
    for week in links(root + "/"):
        for f in links(f"{root}/{week}"):
            if f.endswith(".parquet"):
                raw = urllib.request.urlopen(f"{root}/{week}{f}", timeout=600).read()
                d = pd.read_parquet(io.BytesIO(raw))
                d = d[d["label_technique"].astype(str) != "Duplicate"].drop_duplicates("uid")
                parts.append(features(d))
    df = pd.concat(parts, ignore_index=True)
    print(name, df["label"].value_counts().to_dict(), flush=True)
    return df.groupby("label", group_keys=False).sample(frac=1, random_state=seed).groupby("label").head(CAP)


def main(out):
    os.makedirs(out, exist_ok=True)
    for split, names in SPLITS.items():
        pd.concat([load(n) for n in names], ignore_index=True).to_csv(f"{out}/{split}.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
