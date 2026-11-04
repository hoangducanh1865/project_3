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

from .data import class_table, cross_split, drop_top_features, load_columns, load_csv, load_ts, make_split
from .metrics import alert_metrics, attack_metrics, closed_metrics, detection_metrics
from .models import BUILDERS, tactic_of
from .variants import evaluate_variants

log = logging.getLogger(__name__)


@hydra.main(version_base="1.3", config_path="../conf", config_name="config")
def main(cfg):
    dev = torch.device("cuda" if cfg.device == "auto" and torch.cuda.is_available() else
                       "cpu" if cfg.device == "auto" else cfg.device)
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)

    X, y = load_csv(cfg.dataset)
    log.info("lớp trong dữ liệu: %s", class_table(y))
    cols, _ = load_columns(cfg.dataset)
    proto = cfg.protocol
    ts = load_ts(cfg.dataset) if proto.name == "p3" else None
    if proto.name == "p2":
        dt = OmegaConf.load(os.path.join(os.path.dirname(__file__), "..", "conf", "dataset", f"{proto.target}.yaml"))
        Xt, yt = load_csv(dt)
        cols_t, _ = load_columns(dt)
        common = [c for c in cols if c in cols_t]
        log.info("P2: %d cột chung, thiếu ở đích: %s", len(common), sorted(set(cols) - set(common)))
        X, Xt = X[:, [cols.index(c) for c in common]], Xt[:, [cols_t.index(c) for c in common]]
        cols = common
    sp = make_split(X, y, cfg.dataset, proto, cfg.eval_cap, cfg.seed, ts)
    del X
    if proto.name == "p2":
        log.info("lớp ở mạng đích: %s", class_table(yt))
        sp = cross_split(sp, Xt, yt, dt, cfg.eval_cap, proto.per_class, cfg.seed)
        del Xt
    dropped = []
    if proto.get("drop_top"):
        sp, cols, dropped = drop_top_features(sp, proto.drop_top, cols, cfg.seed, "cuda" if dev.type == "cuda" else "cpu")
        log.info("bỏ đặc trưng: %s", dropped)
    log.info("known=%s | OOD=%s | train=%d test=%d ood=%d", sp["classes"], sp["ood_classes"],
             len(sp["X_tr"]), len(sp["X_te"]), len(sp["X_ood"]))

    sp["cols"] = cols
    t0 = time.time()
    scorer = BUILDERS[cfg.model.kind](cfg, sp, dev)
    fit_s = time.time() - t0

    s_va, _ = scorer(sp["X_va"])
    s_kn, pred = scorer(sp["X_te"])
    s_ood, pred_ood = scorer(sp["X_ood"])
    res = {
        "protocol": cfg.protocol.name, "heldout": cfg.protocol.get("heldout"),
        "model": cfg.model.name, "seed": cfg.seed, "device": str(dev),
        "n_train": len(sp["X_tr"]), "n_known_test": len(sp["X_te"]), "n_ood": len(sp["X_ood"]),
        "known_classes": sp["classes"], "ood_classes": sp["ood_classes"],
        "fit_seconds": round(fit_s, 1),
        **detection_metrics(s_kn, s_ood, s_va),
        **(closed_metrics(sp["y_te"], pred) if pred is not None else {}),
        **(alert_metrics(s_kn, pred, sp["y_te"], s_ood, pred_ood, s_va) if pred is not None else {}),
        **(attack_metrics(scorer.attack(sp["X_te"][sp["y_te"] == 0]), scorer.attack(sp["X_ood"]),
                          scorer.attack(sp["X_va"][sp["y_va"] == 0])) if hasattr(scorer, "attack") else {}),
        **(scorer.extra(sp) if hasattr(scorer, "extra") else {}),
        **({"variants": evaluate_variants(scorer, sp, cols, s_va, proto.variants)} if proto.get("variants") else {}),
        "dropped_features": dropped,
        "config": OmegaConf.to_container(cfg, resolve=True),
    }
    if pred_ood is not None and cfg.dataset.get("tactics") and len(sp["ood_names"]):
        # chiến thuật suy từ họ dự đoán: đối chứng cho đầu chiến thuật của HC-CLOSR, dùng được với mọi mô hình
        fam_tac = np.array([tactic_of(c, cfg.dataset.tactics) for c in sp["classes"]])
        true_tac = np.array([tactic_of(c, cfg.dataset.tactics) for c in sp["ood_names"]])
        res["ood_tactic_by_family"] = float((fam_tac[pred_ood] == true_tac).mean())
    out = os.path.join(HydraConfig.get().runtime.output_dir, "result.json")
    with open(out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)
    log.info("%s", {k: v for k, v in res.items() if k not in ("config", "known_classes")})
    if cfg.artifact_dir:
        from .export import export
        export(cfg, scorer, sp, y, res)


if __name__ == "__main__":
    main()
