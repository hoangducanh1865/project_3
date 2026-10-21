"""Chạy một baseline trên một giao thức. Dùng: python -m src.run protocol=p1 protocol.heldout=slowloris model=closr"""
import json
import logging
import os
import time

import hydra
import numpy as np
import torch
from hydra.core.hydra_config import HydraConfig
from omegaconf import OmegaConf

from .data import class_table, load_csv, make_split
from .metrics import closed_metrics, detection_metrics
from .models import BUILDERS

log = logging.getLogger(__name__)


@hydra.main(version_base="1.3", config_path="../conf", config_name="config")
def main(cfg):
    dev = torch.device("cuda" if cfg.device == "auto" and torch.cuda.is_available() else
                       "cpu" if cfg.device == "auto" else cfg.device)
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    X, y = load_csv(cfg.dataset)
    log.info("lớp trong dữ liệu: %s", class_table(y))
    sp = make_split(X, y, cfg.dataset, cfg.protocol, cfg.eval_cap, cfg.seed)
    del X, y
    log.info("known=%s | OOD=%s | train=%d test=%d ood=%d", sp["classes"], sp["ood_classes"],
             len(sp["X_tr"]), len(sp["X_te"]), len(sp["X_ood"]))

    t0 = time.time()
    scorer = BUILDERS[cfg.model.kind](cfg, sp, dev)
    fit_s = time.time() - t0

    s_va, _ = scorer(sp["X_va"])
    s_kn, pred = scorer(sp["X_te"])
    s_ood, _ = scorer(sp["X_ood"])
    res = {
        "protocol": cfg.protocol.name, "heldout": cfg.protocol.get("heldout"),
        "model": cfg.model.name, "seed": cfg.seed, "device": str(dev),
        "n_train": len(sp["X_tr"]), "n_known_test": len(sp["X_te"]), "n_ood": len(sp["X_ood"]),
        "known_classes": sp["classes"], "ood_classes": sp["ood_classes"],
        "fit_seconds": round(fit_s, 1),
        **detection_metrics(s_kn, s_ood, s_va),
        **(closed_metrics(sp["y_te"], pred) if pred is not None else {}),
        "config": OmegaConf.to_container(cfg, resolve=True),
    }
    out = os.path.join(HydraConfig.get().runtime.output_dir, "result.json")
    with open(out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)
    log.info("%s", {k: v for k, v in res.items() if k not in ("config", "known_classes")})


if __name__ == "__main__":
    main()
