"""HF Space: API cho web giám sát và luồng giả lập mỗi phút (thay Modal). Trạng thái giữ trong bộ nhớ.

Lúc khởi động tải mô hình HC-CLOSR và kho flow DataSense từ HF dataset private (secret HF_TOKEN).
Khoá API (secret API_KEY) giống MODAL_API_KEY phía Vercel.
"""
import json
import os
import threading
import time
import urllib.request

import numpy as np
import pandas as pd
import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from huggingface_hub import snapshot_download
from pydantic import BaseModel

from src.hc_detector import HCDetector
from src.simulator import Simulator
from src.stream import message, step, to_notify

REPO = "hoangducanh1865/project_3-data"
MAX_FLOWS, MAX_NOTIFY = 2000, 3
WEB_URL = "https://project3-ids.vercel.app"
TIER = {1: "tấn công đã biết", 2: "biến thể của chiến thuật đã biết", 3: "hành vi hoàn toàn mới"}
TACTIC = {"impact": "Impact", "credential_access": "Credential Access", "initial_access": "Initial Access",
          "discovery": "Discovery", "unknown": "Chưa xác định"}
torch.set_num_threads(2)

root = snapshot_download(REPO, repo_type="dataset", allow_patterns=["datasense/art/*"], token=os.environ["HF_TOKEN"])
ART = f"{root}/datasense/art"
det = HCDetector.from_state(torch.load(f"{ART}/hc_closr/model.pt", map_location="cpu", weights_only=False))
samples = json.load(open(f"{ART}/hc_closr/samples.json"))
card = json.load(open(f"{ART}/stream/card.json"))
pool = np.load(f"{ART}/stream/pool.npz", allow_pickle=False)
assert pool["columns"].tolist() == det.info["columns"]
sim_engine = Simulator(pool, json.load(open(f"{ART}/stream/scenarios.json")))
state = {"series": [], "incidents": [], "recent": [], "campaigns": [], "summary": None, "updated": None}
sim = {"count": 0, "next_start": int(time.time() // 60) + 2, "active": None}
decisions = {}
lock = threading.Lock()


def send_telegram(text):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", body, {"content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status == 200
    except Exception as e:
        print("lỗi gửi Telegram:", type(e).__name__)
        return False


def tick(minute):
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
    for inc in to_notify(state["incidents"])[:MAX_NOTIFY]:
        if not send_telegram(message(inc, TIER, TACTIC, WEB_URL)):
            break
        inc["notified"] = True


def loop():
    last = None
    while True:
        minute = int(time.time() // 60)
        if minute != last:
            t0 = time.time()
            try:
                with lock:
                    tick(minute)
                print(f"tick {minute}: {time.time() - t0:.1f} s", flush=True)
            except Exception as e:
                print("lỗi tick:", repr(e), flush=True)
            last = minute
        time.sleep(2)


threading.Thread(target=loop, daemon=True).start()


def auth(x_api_key: str = Header(default="")):
    if x_api_key != os.environ["API_KEY"]:
        raise HTTPException(401, "sai khoá API")


api = FastAPI()


@api.get("/")
def health():
    return {"ok": True, "updated": state["updated"]}


class Decision(BaseModel):
    id: str
    decision: str


class Flows(BaseModel):
    columns: list[str]
    rows: list[list]


@api.get("/state", dependencies=[Depends(auth)])
def get_state():
    with lock:
        inc = [{**i, "decision": decisions.get(i["id"])} for i in state["incidents"]]
        return {"updated": state["updated"], "summary": state["summary"], "series": state["series"][-60:],
                "incidents": inc[::-1][:100]}


@api.post("/decide", dependencies=[Depends(auth)])
def decide(body: Decision):
    if body.decision not in ("approved", "rejected", "undo"):
        raise HTTPException(422, "quyết định không hợp lệ")
    decisions.pop(body.id, None) if body.decision == "undo" else decisions.update({body.id: body.decision})
    return {"ok": True}


@api.get("/card", dependencies=[Depends(auth)])
def get_card():
    return card


@api.get("/meta", dependencies=[Depends(auth)])
def meta():
    return {"max_flows": MAX_FLOWS, "models": [{"id": "hc_closr", "name": "HC-CLOSR (đề xuất), DataSense 2025",
            "has_tier2": True, "n_columns": len(det.info["columns"]), "ood_classes": det.info["ood_classes"],
            "metrics": det.info["metrics"]}]}


@api.get("/samples", dependencies=[Depends(auth)])
def get_samples(model: str = "hc_closr"):
    return samples


@api.post("/analyze", dependencies=[Depends(auth)])
def analyze(body: Flows, model: str = "hc_closr"):
    cols = det.info["columns"]
    if len(body.rows) > MAX_FLOWS:
        raise HTTPException(413, f"tối đa {MAX_FLOWS} flow mỗi lần")
    missing = [c for c in cols if c not in body.columns]
    if missing:
        raise HTTPException(422, {"missing_columns": missing})
    X = pd.DataFrame(body.rows, columns=body.columns)[cols].apply(pd.to_numeric, errors="coerce").to_numpy(np.float32)
    ok = np.isfinite(X).all(axis=1)
    with lock:
        out = iter(det.analyze(X[ok]) if ok.any() else [])
    return {"flows": [next(out) if g else {"status": "invalid"} for g in ok]}
