"""Modal: API suy luận (CPU) cho web giám sát xâm nhập mạng.

Chạy từ thư mục gốc repo, dùng hồ sơ Modal đang đăng nhập:
  python deploy/setup_modal.py                           # tạo secret từ .env
  PYTHONPATH=. modal run deploy/modal_app.py             # dựng CLOSR [16] từ trọng số gốc
  modal volume put project3-model <thư mục> /hc_closr    # nạp HC-CLOSR đã huấn luyện (xem scripts/kaggle)
  PYTHONPATH=. modal deploy deploy/modal_app.py          # triển khai API
"""
import json
import os

import modal

CLOSR_SHA = "79da4d1f2a6f4e5ecf92c4588195aaf163df40f8"
VOL = "/vol"
MAX_FLOWS = 2000
NAMES = {"hc_closr": "HC-CLOSR (đề xuất)", "closr": "CLOSR [16], trọng số gốc"}

app = modal.App("project3-hc-closr")
volume = modal.Volume.from_name("project3-model", create_if_missing=True)
secret = modal.Secret.from_name("project3")


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


@app.function(image=prep_image, gpu="T4", cpu=4, memory=16384, timeout=1800, volumes={VOL: volume}, secrets=[secret])
def prepare_closr(tactics: dict, impact: dict):
    import torch
    from huggingface_hub import hf_hub_download
    from src.closr_detector import build
    csv = hf_hub_download("hoangducanh1865/project_3-data", "lycos2017/lycos.csv", repo_type="dataset",
                          token=os.environ["HF_TOKEN"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    metrics = build(csv, "/opt/CLOSR/weights/closr.pt.tar", f"{VOL}/closr", tactics, impact, dev)
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
