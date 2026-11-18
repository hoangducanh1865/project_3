"""Tính sẵn 24 giờ luồng giả lập bằng HC-CLOSR, ghi thành file tĩnh cho web (không cần máy chủ chạy liên tục).

Dùng: python scripts/precompute_live.py --art $ART --out web/public/live
Web phát lại vòng 24 giờ này theo giờ trong ngày (web/app/api/[path]/route.ts).
"""
import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.hc_detector import HCDetector  # noqa: E402
from src.policy import plan  # noqa: E402
from src.simulator import Simulator  # noqa: E402
from src.stream import step  # noqa: E402


def main(a):
    det = HCDetector.from_state(torch.load(f"{a.art}/hc_closr/model.pt", map_location="cpu", weights_only=False))
    pool = np.load(f"{a.art}/stream/pool.npz", allow_pickle=False)
    sim_engine = Simulator(pool, json.load(open(f"{a.art}/stream/scenarios.json")))
    sim = {"count": 0, "next_start": 3, "active": None}
    state = {"series": [], "incidents": [], "recent": [], "campaigns": []}
    every = {}
    for minute in range(a.minutes):
        before = sim.get("active")
        X, flows, ended = sim_engine.tick(sim, minute, np.random.default_rng(minute))
        if sim.get("active") and not before:
            c = sim["active"]
            state["campaigns"].append({k: c[k] for k in ("id", "name", "narrative", "start", "scenario")}
                                      | {"files": [p["file"] for p in c["phases"]]})
        results = det.analyze(X) if len(X) else []
        for f, r in zip(flows, results):
            if r["status"] == "alert":
                f.update(sim_engine.evidence(f["row"]), score=r["score"])
        step(state, flows, results, minute, det.info["impact"], ended)
        for inc in state["incidents"]:
            every[inc["id"]] = json.loads(json.dumps(inc, default=float))
        if minute % 60 == 0:
            print(minute, len(every), flush=True)
    os.makedirs(a.out, exist_ok=True)
    card = json.load(open(f"{a.art}/stream/card.json"))
    role = {d["ip"]: d["role"] for d in card["devices"]}
    for inc in every.values():     # ai thực hiện, ai duyệt, AI được làm đến đâu (conf/policy.yaml)
        inc["policy"] = plan(inc["level"], role.get(inc["dst"]))
    out = {"minutes": a.minutes, "series": state["series"], "incidents": list(every.values()),
           "campaigns": state["campaigns"]}
    json.dump(out, open(f"{a.out}/timeline.json", "w"), ensure_ascii=False, default=float)
    json.dump(card, open(f"{a.out}/card.json", "w"), ensure_ascii=False)
    # danh mục nhãn (ATT&CK, D3FEND) kèm nhận định AI có dẫn nguồn, cho trang Nhãn và chi tiết sự cố
    root = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    labels = json.load(open(f"{root}/labels/catalog.json"))
    notes = json.load(open(f"{root}/ai_notes.json")) if os.path.exists(f"{root}/ai_notes.json") else {}
    for fid, f in labels["families"].items():
        f["ai"] = notes.get(fid)
    labels["report"] = open(f"{root}/labels/report.md").read()
    json.dump(labels, open(f"{a.out}/labels.json", "w"), ensure_ascii=False)
    import yaml
    json.dump(yaml.safe_load(open(os.path.join(root, "..", "conf", "policy.yaml"))), open(f"{a.out}/policy.json", "w"),
              ensure_ascii=False)
    print("xong", len(every), "sự cố", os.path.getsize(f"{a.out}/timeline.json") // 1024, "KB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--minutes", type=int, default=1440)
    main(ap.parse_args())
