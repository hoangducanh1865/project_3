"""Giả lập luồng 24/7 bằng cách phát lại flow thật của DataSense (CIC IIoT 2025) chưa dùng để huấn luyện.

Mỗi flow giữ nguyên IP, cổng, giao thức, thời điểm trong PCAP gốc và tên tệp PCAP, nên mọi cảnh báo trên web truy
ngược được tới gói tin gốc. Một chiến dịch gồm vài pha (deploy/scenarios.json), mỗi pha phát lại một tệp PCAP tấn công
có thật của họ đó, gồm cả lưu lượng nền của thiết bị trong lúc bị tấn công. Phần giả lập chỉ là thời điểm phát lại.
"""
import math

import numpy as np
import pandas as pd

META = ["src_ip", "dst_ip", "src_port", "dst_port", "protocol", "bidirectional_first_seen_ms",
        "bidirectional_last_seen_ms", "file", "rule"]
SHOW = ["bidirectional_packets", "bidirectional_bytes", "bidirectional_duration_ms", "src2dst_packets",
        "dst2src_packets", "bidirectional_syn_packets", "bidirectional_rst_packets", "bidirectional_fin_packets",
        "bidirectional_psh_packets", "bidirectional_mean_ps", "bidirectional_mean_piat_ms"]
MEAN_GAP, MIN_GAP, MAX_GAP = 40, 15, 120    # phút giữa hai chiến dịch
TZ_HOURS = 7


def benign_rate(minute):
    """Số flow bình thường mỗi phút: cao trong giờ làm việc, thấp ban đêm (giờ Việt Nam)."""
    hour = (minute / 60 + TZ_HOURS) % 24
    return 60 + 120 * max(0.0, math.sin(math.pi * (hour - 7) / 12))


def build_pool(X, y, rows, columns, sp, path, table, seed=0, cap_benign=40000):
    """Kho flow cho web: chỉ lấy flow không dùng để huấn luyện (known-test và họ bị giấu), kèm định danh gốc."""
    rng = np.random.default_rng(seed)
    te, ood = sp["idx_te"], sp["idx_ood"]
    ben = te[y[te] == "benign"]
    idx = np.concatenate([rng.permutation(ben)[:cap_benign], te[y[te] != "benign"], ood])
    meta = pd.read_parquet(table, columns=META).iloc[rows[idx]]
    np.savez(path, X=X[idx], y=y[idx], columns=np.array(columns),
             **{k: meta[k].astype(str if k in ("src_ip", "dst_ip", "file", "rule") else np.int64).to_numpy()
                for k in META})
    return {str(c): int(n) for c, n in zip(*np.unique(y[idx], return_counts=True))}


class Simulator:
    def __init__(self, pool, scenarios):
        self.p = {k: pool[k] for k in pool.files}
        y, files = self.p["y"], self.p["file"]
        cols = self.p["columns"].tolist()
        self.show = [cols.index(c) for c in SHOW if c in cols]
        self.show_names = [c for c in SHOW if c in cols]
        ben = np.flatnonzero(y == "benign")
        self.benign = ben
        # Thang so sánh cho "vì sao cảnh báo": trung vị và IQR của flow bình thường trong kho
        Xb = self.p["X"][ben]
        self.med = np.median(Xb, 0)
        self.iqr = np.maximum(np.quantile(Xb, 0.75, 0) - np.quantile(Xb, 0.25, 0), 1e-6)
        self.cols = cols
        order = np.argsort(self.p["bidirectional_first_seen_ms"], kind="stable")
        self.by_file = {}
        for i in order:
            self.by_file.setdefault(str(files[i]), []).append(int(i))
        self.files_of = {}
        for f, idx in self.by_file.items():
            fams = {str(y[i]) for i in idx} - {"benign"}
            for fam in fams:
                self.files_of.setdefault(fam, []).append(f)
        self.scenarios = [s for s in scenarios if all(p["family"] in self.files_of for p in s["phases"])]

    def flow(self, i, campaign=None):
        p = self.p
        truth = str(p["y"][i])
        return {"src": str(p["src_ip"][i]), "dst": str(p["dst_ip"][i]), "sport": int(p["src_port"][i]),
                "dport": int(p["dst_port"][i]), "proto": int(p["protocol"][i]),
                "t0": int(p["bidirectional_first_seen_ms"][i]), "t1": int(p["bidirectional_last_seen_ms"][i]),
                "file": str(p["file"][i]), "truth": None if truth == "benign" else truth, "campaign": campaign,
                "row": int(i)}

    def evidence(self, i):
        """Số đo gốc của flow và 3 đặc trưng lệch nhiều nhất so với flow bình thường (theo trung vị và IQR)."""
        x = self.p["X"][i]
        z = (x - self.med) / self.iqr
        top = np.argsort(-np.abs(z))[:3]
        return {"feat": {n: float(x[j]) for n, j in zip(self.show_names, self.show)},
                "top": [{"name": self.cols[j], "value": float(x[j]), "median": float(self.med[j]),
                         "z": round(float(z[j]), 1)} for j in top]}

    def _start(self, sim, minute, rng):
        sc = self.scenarios[int(rng.integers(len(self.scenarios)))]
        sim["count"] += 1
        phases = [{**ph, "file": str(rng.choice(self.files_of[ph["family"]]))} for ph in sc["phases"]]
        sim["active"] = {"id": sim["count"], "scenario": sc["id"], "name": sc["name"], "narrative": sc["narrative"],
                         "phase": 0, "step": 0, "phases": phases, "start": minute}
        return sim["active"]

    def tick(self, sim, minute, rng):
        """-> (X, danh sách flow kèm định danh gốc, chiến dịch vừa kết thúc nếu có)."""
        if sim.get("active") is None and minute >= sim["next_start"]:
            self._start(sim, minute, rng)
        idx = list(rng.choice(self.benign, rng.poisson(benign_rate(minute))))
        flows = [self.flow(i) for i in idx]
        ended = None
        camp = sim.get("active")
        if camp:
            ph = camp["phases"][camp["phase"]]
            rows = self.by_file[ph["file"]]
            part = np.array_split(np.array(rows), ph["minutes"])[camp["step"]]   # phát lại tệp theo đúng thứ tự thời gian
            idx += part.tolist()
            flows += [self.flow(i, camp["id"]) for i in part]
            camp["step"] += 1
            if camp["step"] >= ph["minutes"]:
                camp["phase"], camp["step"] = camp["phase"] + 1, 0
                if camp["phase"] >= len(camp["phases"]):
                    ended, sim["active"] = camp, None
                    gap = float(np.clip(rng.exponential(MEAN_GAP), MIN_GAP, MAX_GAP))
                    sim["next_start"] = minute + int(gap)
        order = rng.permutation(len(idx))
        X = self.p["X"][np.array(idx, dtype=np.int64)[order]] if idx else self.p["X"][:0]
        return X, [flows[i] for i in order], ended
