"""Sinh dữ liệu cho trang 'Diễn tập tấn công' của web: mỗi họ một kịch bản phát động được.

Dùng đúng pipeline thật: lấy flow tấn công của từng họ trong kho phát lại (flow CHƯA dùng để huấn luyện),
cho HC-CLOSR chấm điểm, gom thành một sự cố bằng src/stream.step. Web chỉ điều khiển thời điểm phát động và
máy mục tiêu; điểm OOD, tầng, biện pháp D3FEND đều tính sẵn ở đây.

    python scripts/build_attacks.py --art $ART --out web/public/live/attacks.json
"""
import argparse
import json
import os
import sys
from collections import Counter

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.hc_detector import HCDetector  # noqa: E402
from src.simulator import Simulator  # noqa: E402
from src.stream import step  # noqa: E402

CAP_ATTACK = 220        # số flow tấn công tối đa mỗi kịch bản
BENIGN_FRAC = 0.35      # thêm lưu lượng nền cùng tệp cho sát thực tế
KEEP = ("tier", "tactic", "L", "I", "R", "level", "action", "reversible", "mode", "d3fend_now", "d3fend_later",
        "family", "alerts", "flows", "truth", "evidence", "files")


def common(values):
    return Counter(map(str, values)).most_common(1)[0][0]


def build_one(det, sim, pool, fam, rng, attackers):
    y, files = pool["y"], pool["pcap"]
    a = np.flatnonzero(y == fam)
    if len(a) < 10:
        return None, "quá ít flow trong kho"
    file = common(files[a])                       # tệp PCAP có nhiều flow họ này nhất
    rows = a[files[a] == file]
    rows = rows[rng.permutation(len(rows))[:CAP_ATTACK]]
    # flow hai chiều: chọn đầu là máy tấn công làm nguồn, đầu kia làm đích, để sơ đồ mạng vẽ từ máy tấn công tới mục
    # tiêu. Mô hình không dùng IP nên việc chọn hướng này chỉ ảnh hưởng hiển thị. Họ giả mạo IP: nguồn là IP giả.
    sips, dips = pool["src_ip"][rows], pool["dst_ip"][rows]
    atk = [s if s in attackers else (d if d in attackers else s) for s, d in zip(sips, dips)]
    tgt = [d if (s in attackers and d not in attackers) else (s if d in attackers else d) for s, d in zip(sips, dips)]
    src_ip, dst_ip = common(atk), common(tgt)
    ben = np.flatnonzero(y == "benign")
    ben = ben[files[ben] == file]
    ben = ben[rng.permutation(len(ben))[:int(len(rows) * BENIGN_FRAC)]]
    idx = np.concatenate([rows, ben])
    results = det.analyze(pool["X"][idx])
    flows = []
    for i, r in zip(idx.tolist(), results):
        f = sim.flow(i)
        f["src"], f["dst"] = src_ip, dst_ip       # gom về một cặp nguồn, đích (mô hình không dùng IP)
        if r["status"] == "alert":
            f.update(sim.evidence(i), score=r["score"])
        flows.append(f)
    state = {"series": [], "incidents": [], "recent": [], "campaigns": []}
    step(state, flows, results, 0, det.info["impact"], None)
    inc = next((i for i in state["incidents"] if i["key"] == f"{src_ip}>{dst_ip}"), None)
    if inc is None:
        return None, "mô hình không đủ cảnh báo để mở sự cố"
    return {"family": fam, "known": fam in [str(c) for c in det.info["classes"]], "file": file,
            "src_ip": src_ip, "dst_ip": dst_ip,
            "incident": {k: inc[k] for k in KEEP if k in inc}}, None


def main(a):
    det = HCDetector.from_state(torch.load(f"{a.art}/hc_closr/model.pt", map_location="cpu", weights_only=False))
    pool = np.load(f"{a.art}/stream/pool.npz", allow_pickle=False)
    sim = Simulator(pool, [])
    rng = np.random.default_rng(0)
    card0 = json.load(open(f"{a.art}/stream/card.json"))
    attackers = {d["ip"] for d in card0["devices"] if d["role"] == "attacker"}
    fams = sorted(set(map(str, pool["y"])) - {"benign"})
    out, skipped = [], []
    for fam in fams:
        sc, why = build_one(det, sim, pool, fam, rng, attackers)
        if sc:
            out.append(sc)
            print(f"{fam}: tầng {sc['incident']['tier']} mức {sc['incident']['level']} "
                  f"{sc['incident']['alerts']}/{sc['incident']['flows']} {'đã biết' if sc['known'] else 'OOD'}")
        else:
            skipped.append(fam)
            print(f"{fam}: bỏ ({why})")
    card = json.load(open(f"{a.art}/stream/card.json"))
    data = {
        "generated": card.get("version", ""), "heldout": card["model"].get("heldout"),
        "note": ("Flow tấn công thật của DataSense, lấy từ tệp PCAP và CHƯA dùng để huấn luyện. "
                 "Điểm OOD, tầng và biện pháp D3FEND do HC-CLOSR cùng bảng ứng phó tính sẵn (không suy luận trực tiếp "
                 "khi bấm). Bạn chọn loại tấn công và máy mục tiêu, phát động để xem sự cố hiện lên luồng."),
        "scenarios": out, "skipped": skipped,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(data, open(a.out, "w"), ensure_ascii=False, default=float)
    print(f"xong {len(out)} kịch bản, bỏ {len(skipped)}, {os.path.getsize(a.out) // 1024} KB -> {a.out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", required=True)
    main(ap.parse_args())
