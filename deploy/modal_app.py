"""Modal: API suy luận (CPU) cho web giám sát xâm nhập mạng.

Chạy từ thư mục gốc repo, dùng hồ sơ Modal đang đăng nhập:
  python deploy/setup_modal.py                           # tạo secret từ .env
  PYTHONPATH=. modal run deploy/modal_app.py::main       # dựng CLOSR [16] từ trọng số gốc
  PYTHONPATH=. modal run deploy/modal_app.py::stream     # dựng kho flow và nạp kịch bản cho luồng giả lập
  modal volume put project3-model <thư mục> /hc_closr    # nạp HC-CLOSR đã huấn luyện (xem scripts/kaggle)
  PYTHONPATH=. modal deploy deploy/modal_app.py          # triển khai API
"""
import json
import os
import time

import modal

CLOSR_SHA = "79da4d1f2a6f4e5ecf92c4588195aaf163df40f8"
VOL = "/vol"
MAX_FLOWS = 2000
HELDOUT = "slowloris"   # họ tấn công bị giấu khi huấn luyện HC-CLOSR (scripts/kaggle/run_hc_closr.py)
NAMES = {"hc_closr": "HC-CLOSR (đề xuất)", "closr": "CLOSR [16], trọng số gốc"}

app = modal.App("project3-hc-closr")
volume = modal.Volume.from_name("project3-model", create_if_missing=True)
secret = modal.Secret.from_name("project3")
store = modal.Dict.from_name("project3-live", create_if_missing=True)


def with_code(image):
    return (image.apt_install("git")
            .run_commands(f"git clone https://github.com/jackwilkie/CLOSR /opt/CLOSR && "
                          f"git -C /opt/CLOSR checkout {CLOSR_SHA}")
            .env({"CLOSR_DIR": "/opt/CLOSR"})
            .add_local_python_source("src"))


prep_image = with_code(modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch", "numpy", "pandas", "scikit-learn", "huggingface_hub"))
serve_image = with_code(modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch", index_url="https://download.pytorch.org/whl/cpu"
).pip_install("numpy", "pandas", "fastapi[standard]"))


@app.function(image=prep_image, cpu=8, memory=16384, timeout=3600, volumes={VOL: volume}, secrets=[secret])
def prepare_closr(tactics: dict, impact: dict):
    from huggingface_hub import hf_hub_download
    from src.closr_detector import build
    csv = hf_hub_download("hoangducanh1865/project_3-data", "lycos2017/lycos.csv", repo_type="dataset",
                          token=os.environ["HF_TOKEN"])
    metrics = build(csv, "/opt/CLOSR/weights/closr.pt.tar", f"{VOL}/closr", tactics, impact, "cpu")
    volume.commit()
    return metrics


@app.local_entrypoint()
def main():
    from pathlib import Path

    import yaml
    conf = Path(__file__).resolve().parents[1] / "conf"
    tactics = yaml.safe_load((conf / "dataset/lycos.yaml").read_text())["tactics"]
    impact = yaml.safe_load((conf / "model/hc_closr.yaml").read_text())["impact"]
    print(prepare_closr.remote(tactics, impact))


@app.function(image=prep_image, cpu=4, memory=16384, timeout=1800, volumes={VOL: volume}, secrets=[secret])
def prepare_stream(ds_conf: dict, scenarios: list):
    from types import SimpleNamespace

    from huggingface_hub import hf_hub_download
    from src.data import load_columns, load_csv, make_split
    from src.simulator import build_pool
    csv = hf_hub_download("hoangducanh1865/project_3-data", "lycos2017/lycos.csv", repo_type="dataset",
                          token=os.environ["HF_TOKEN"])
    ds = SimpleNamespace(**ds_conf, path=csv, cache="/tmp/lycos_cache.npz")
    X, y = load_csv(ds)
    columns, rows = load_columns(ds)
    # cùng seed và họ bị giấu với lúc huấn luyện, không giới hạn số mẫu để lấy trọn tập test
    sp = make_split(X, y, ds, {"heldout": HELDOUT}, 10 ** 9, 0)
    os.makedirs(f"{VOL}/stream", exist_ok=True)
    counts = build_pool(X, y, rows, columns, sp, csv, f"{VOL}/stream/pool.npz")
    with open(f"{VOL}/stream/scenarios.json", "w") as f:
        json.dump(scenarios, f, ensure_ascii=False)
    volume.commit()
    return counts


@app.local_entrypoint()
def stream():
    from pathlib import Path

    import yaml
    root = Path(__file__).resolve().parents[1]
    conf = yaml.safe_load((root / "conf/dataset/lycos.yaml").read_text())
    keys = ("label_col", "benign", "drop_cols", "rare_threshold", "max_per_class")
    print(prepare_stream.remote({k: conf[k] for k in keys}, json.loads((root / "deploy/scenarios.json").read_text())))


@app.function(image=serve_image, cpu=1, memory=2048, scaledown_window=2, timeout=55, volumes={VOL: volume},
              schedule=modal.Cron("* * * * *"))
def tick():
    """Mỗi phút: sinh lưu lượng của một phút, chạy HC-CLOSR rồi cập nhật sự cố. Máy tắt ngay sau đó để tiết kiệm."""
    import numpy as np
    import torch
    from src.hc_detector import HCDetector
    from src.simulator import Simulator
    from src.stream import step
    torch.set_num_threads(1)
    t0 = time.time()
    minute = int(t0 // 60)
    state = {k: store.get(k, []) for k in ("series", "incidents", "recent", "campaigns")}
    sim = store.get("sim", {"count": 0, "next_start": minute, "active": None})
    if state["series"] and state["series"][-1]["t"] >= minute * 60:
        return "đã chạy phút này"
    det = HCDetector.from_state(torch.load(f"{VOL}/hc_closr/model.pt", map_location="cpu", weights_only=False))
    pool = np.load(f"{VOL}/stream/pool.npz", allow_pickle=False)
    assert pool["columns"].tolist() == det.info["columns"]
    simulator = Simulator(pool, json.load(open(f"{VOL}/stream/scenarios.json")))
    before = sim.get("active")
    X, flows, ended = simulator.tick(sim, minute, np.random.default_rng(minute))
    if sim.get("active") and not before:
        c = sim["active"]
        state["campaigns"].append({k: c[k] for k in ("id", "name", "narrative", "start", "scenario")})
    opened = step(state, flows, det.analyze(X), minute, det.info["impact"], ended)
    for k, v in state.items():
        store[k] = v
    store["sim"] = sim
    print(f"tick: {len(flows)} flow, mở {len(opened)} sự cố, {time.time() - t0:.1f} giây")


@app.function(image=modal.Image.debian_slim(python_version="3.12").pip_install("fastapi[standard]"), cpu=0.25,
              memory=256, scaledown_window=60, secrets=[secret])
@modal.asgi_app()
def live():
    """API đọc trạng thái luồng giả lập, không nạp mô hình nên khởi động nhanh."""
    from fastapi import Depends, FastAPI, Header, HTTPException
    from pydantic import BaseModel

    class Decision(BaseModel):
        id: str
        decision: str

    def auth(x_api_key: str = Header(default="")):
        if x_api_key != os.environ["API_KEY"]:
            raise HTTPException(401, "sai khoá API")

    api = FastAPI(dependencies=[Depends(auth)])

    @api.get("/state")
    def state():
        decisions = store.get("decisions", {})
        incidents = [{**i, "decision": decisions.get(i["id"])} for i in store.get("incidents", [])]
        return {"updated": store.get("updated", None), "summary": store.get("summary", None),
                "series": store.get("series", [])[-60:], "incidents": incidents[::-1][:100]}

    @api.post("/decide")
    def decide(body: Decision):
        if body.decision not in ("approved", "rejected", "undo"):
            raise HTTPException(422, "quyết định không hợp lệ")
        decisions = store.get("decisions", {})
        decisions.pop(body.id, None) if body.decision == "undo" else decisions.update({body.id: body.decision})
        store["decisions"] = decisions
        return {"ok": True}

    return api


@app.cls(image=serve_image, cpu=2, memory=4096, scaledown_window=300, volumes={VOL: volume}, secrets=[secret])
class Api:
    @modal.enter()
    def load(self):
        import torch
        from src.closr_detector import CLOSRDetector
        from src.hc_detector import HCDetector
        torch.set_num_threads(2)
        self.models = {}
        for key, cls in (("hc_closr", HCDetector), ("closr", CLOSRDetector)):
            if os.path.exists(f"{VOL}/{key}/model.pt"):
                st = torch.load(f"{VOL}/{key}/model.pt", map_location="cpu", weights_only=False)
                self.models[key] = (cls.from_state(st), json.load(open(f"{VOL}/{key}/samples.json")))

    @modal.asgi_app()
    def web(self):
        import numpy as np
        import pandas as pd
        from fastapi import Depends, FastAPI, Header, HTTPException
        from pydantic import BaseModel

        class Flows(BaseModel):
            columns: list[str]
            rows: list[list]

        def auth(x_api_key: str = Header(default="")):
            if x_api_key != os.environ["API_KEY"]:
                raise HTTPException(401, "sai khoá API")

        def pick(model: str):
            if model not in self.models:
                raise HTTPException(404, f"chưa có mô hình {model}")
            return self.models[model]

        api = FastAPI(dependencies=[Depends(auth)])

        @api.get("/meta")
        def meta():
            return {"max_flows": MAX_FLOWS, "models": [
                {"id": key, "name": NAMES[key], "has_tier2": det.has_tier2, "n_columns": len(det.info["columns"]),
                 "ood_classes": det.info["ood_classes"], "metrics": det.info["metrics"]}
                for key, (det, _) in self.models.items()]}

        @api.get("/samples")
        def samples(model: str):
            return pick(model)[1]

        @api.post("/analyze")
        def analyze(body: Flows, model: str):
            det = pick(model)[0]
            cols = det.info["columns"]
            if len(body.rows) > MAX_FLOWS:
                raise HTTPException(413, f"tối đa {MAX_FLOWS} flow mỗi lần")
            missing = [c for c in cols if c not in body.columns]
            if missing:
                raise HTTPException(422, {"missing_columns": missing})
            df = pd.DataFrame(body.rows, columns=body.columns)
            X = df[cols].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float32)
            ok = np.isfinite(X).all(axis=1)
            out = iter(det.analyze(X[ok]) if ok.any() else [])
            return {"flows": [next(out) if good else {"status": "invalid"} for good in ok]}

        return api
