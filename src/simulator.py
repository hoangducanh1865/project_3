"""Giả lập luồng lưu lượng mạng 24/7 bằng cách phát lại flow thật của LYCOS-IDS2017 chưa dùng để huấn luyện.

Đặc trưng flow giữ nguyên. Chỉ IP được gán theo kịch bản tấn công (deploy/scenarios.json) để các flow của một chiến
dịch có chung nguồn và đích. IP kẻ tấn công thuộc dải dành cho tài liệu (RFC 5737).
"""
import math

import numpy as np
import pandas as pd

WEB, FTP, SSH = "192.168.10.50", "192.168.10.51", "192.168.10.52"
WORKSTATIONS = ["192.168.10.8", "192.168.10.9", "192.168.10.14", "192.168.10.15", "192.168.10.25"]
TARGET = {"ftp_patator": FTP, "ssh_patator": SSH}
MEAN_GAP, MIN_GAP, MAX_GAP = 40, 15, 120    # phút giữa hai chiến dịch
TZ_HOURS = 7


def benign_rate(minute):
    """Số flow bình thường mỗi phút: cao trong giờ làm việc, thấp ban đêm (giờ Việt Nam)."""
    hour = (minute / 60 + TZ_HOURS) % 24
    return 120 + 240 * max(0.0, math.sin(math.pi * (hour - 7) / 12))


def build_pool(X, y, rows, columns, sp, csv, path, seed=0, cap_benign=30000, cap_attack=5000):
    """Chỉ lấy flow không dùng để huấn luyện: known-test, họ bị giấu và các lớp hiếm."""
    rng = np.random.default_rng(seed)
    known = [str(c) for c in sp["classes"]]
    te, ood = sp["idx_te"], sp["idx_ood"]
    picks = [rng.permutation(te[y[te] == c])[:(cap_benign if c == known[0] else cap_attack)] for c in known]
    picks.append(rng.permutation(ood)[:cap_attack])
    unseen = sorted(set(np.unique(y).tolist()) - set(known) - {str(c) for c in sp["ood_classes"]})
    picks += [np.flatnonzero(y == c) for c in unseen]
    idx = np.concatenate(picks)
    meta = pd.read_csv(csv, usecols=["src_addr", "dst_addr"]).iloc[rows[idx]]
    np.savez(path, X=X[idx], y=y[idx], src=meta["src_addr"].to_numpy().astype(str),
             dst=meta["dst_addr"].to_numpy().astype(str), columns=np.array(columns))
    return {str(c): int(n) for c, n in zip(*np.unique(y[idx], return_counts=True))}


class Simulator:
    def __init__(self, pool, scenarios):
        self.X, self.src, self.dst = pool["X"], pool["src"], pool["dst"]
        names = pool["y"]
        self.by_class = {str(c): np.flatnonzero(names == c) for c in np.unique(names)}
        self.scenarios = scenarios

    def _start(self, sim, minute, rng):
        sc = self.scenarios[int(rng.integers(len(self.scenarios)))]
        sim["count"] += 1
        sim["active"] = {
            "id": sim["count"], "scenario": sc["id"], "name": sc["name"], "narrative": sc["narrative"],
            "attacker": f"{rng.choice(['203.0.113', '198.51.100'])}.{rng.integers(2, 250)}",
            "workstation": str(rng.choice(WORKSTATIONS)), "phase": 0, "left": sc["phases"][0]["minutes"],
            "phases": sc["phases"], "start": minute,
        }
        return sim["active"]

    def _attack_flows(self, camp, rng):
        phase = camp["phases"][camp["phase"]]
        family = phase["family"]
        idx = rng.choice(self.by_class[family], rng.poisson(phase["flows_per_min"]))
        # botnet: máy trong mạng bị nhiễm gọi ra máy chủ điều khiển
        pair = (camp["workstation"], camp["attacker"]) if family == "bot" else \
            (camp["attacker"], TARGET.get(family, WEB))
        return idx, pair, family

    def tick(self, sim, minute, rng):
        """-> (X, danh sách {src, dst, truth, campaign}, kịch bản vừa kết thúc nếu có)."""
        if sim.get("active") is None and minute >= sim["next_start"]:
            self._start(sim, minute, rng)
        idx = rng.choice(self.by_class["benign"], rng.poisson(benign_rate(minute)))
        flows = [{"src": str(self.src[i]), "dst": str(self.dst[i]), "truth": None, "campaign": None} for i in idx]
        parts, ended = [idx], None
        camp = sim.get("active")
        if camp:
            a_idx, (src, dst), family = self._attack_flows(camp, rng)
            parts.append(a_idx)
            flows += [{"src": src, "dst": dst, "truth": family, "campaign": camp["id"]}] * len(a_idx)
            camp["left"] -= 1
            if camp["left"] <= 0:
                camp["phase"] += 1
                if camp["phase"] < len(camp["phases"]):
                    camp["left"] = camp["phases"][camp["phase"]]["minutes"]
                else:
                    ended, sim["active"] = camp, None
                    gap = float(np.clip(rng.exponential(MEAN_GAP), MIN_GAP, MAX_GAP))
                    sim["next_start"] = minute + int(gap)
        order = rng.permutation(sum(len(p) for p in parts))
        X = self.X[np.concatenate(parts)[order]]
        return X, [flows[i] for i in order], ended
