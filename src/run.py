"""Chạy một mô hình trên một kịch bản. Ví dụ:

python -m src.run dataset=nf_ton protocol.heldout=ddos model=hc_closr
python -m src.run dataset=nf_ton protocol=cross protocol.target=nf_cic model=xgboost
"""
import json
import logging
import os
import time

import hydra
import numpy as np
import torch
from hydra.core.hydra_config import HydraConfig
from omegaconf import OmegaConf

from .data import class_table, cross_split, drop_named, load_columns, load_csv, make_split, tactic_of
from .metrics import attack_metrics, closed_metrics, detection_metrics, tactic_accuracy
from .models import BUILDERS

log = logging.getLogger(__name__)


def load_scenario(cfg):
    """-> (phép tách, nhãn gốc, các đặc trưng đã bỏ). Mọi số liệu đều đo trên phép tách này."""
    proto = cfg.protocol
    X, y = load_csv(cfg.dataset)
    log.info("lớp trong dữ liệu: %s", class_table(y))
    cols, _ = load_columns(cfg.dataset)
    tactics = cfg.dataset.tactics
    if proto.name == "cross":
        dt = OmegaConf.load(os.path.join(os.path.dirname(__file__), "..", "conf", "dataset", f"{proto.target}.yaml"))
        Xt, yt = load_csv(dt)
        cols_t, _ = load_columns(dt)
        common = [c for c in cols if c in cols_t]
        log.info("%d cột chung, thiếu ở đích: %s", len(common), sorted(set(cols) - set(common)))
        X, Xt = X[:, [cols.index(c) for c in common]], Xt[:, [cols_t.index(c) for c in common]]
        cols, tactics = common, dt.tactics
        sp = make_split(X, y, cfg.dataset, proto, cfg.eval_cap, cfg.seed)
        sp = cross_split(sp, Xt, yt, dt, cfg.eval_cap, proto.per_class, cfg.seed, proto.get("align"))
    else:
        sp = make_split(X, y, cfg.dataset, proto, cfg.eval_cap, cfg.seed)
    dropped = []
    if cfg.clean:
        sp, cols, dropped = drop_named(sp, cfg.dataset.stack_features, cols)
        log.info("bỏ đặc trưng: %s", dropped)
    sp["cols"] = cols
    sp["ood_tactics"] = np.array([tactic_of(c, tactics) for c in sp["ood_names"]])
    log.info("known=%s | OOD=%s | train=%d test=%d ood=%d", sp["classes"], sp["ood_classes"],
             len(sp["X_tr"]), len(sp["X_te"]), len(sp["X_ood"]))
    return sp, y, dropped


@hydra.main(version_base="1.3", config_path="../conf", config_name="config")
def main(cfg):
    dev = torch.device("cuda" if cfg.device == "auto" and torch.cuda.is_available() else
                       "cpu" if cfg.device == "auto" else cfg.device)
    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    sp, y, dropped = load_scenario(cfg)

    t0 = time.time()
    scorer = BUILDERS[cfg.model.kind](cfg, sp, dev)
    fit_s = time.time() - t0

    s_va, _ = scorer(sp["X_va"])
    s_kn, pred = scorer(sp["X_te"])
    s_ood, _ = scorer(sp["X_ood"])
    benign_te, benign_va = sp["X_te"][sp["y_te"] == 0], sp["X_va"][sp["y_va"] == 0]
    res = {
        "dataset": cfg.dataset.name, "protocol": cfg.protocol.name, "heldout": cfg.protocol.get("heldout"),
        "target": cfg.protocol.get("target"), "align": cfg.protocol.get("align"),
        "model": cfg.model.name, "seed": cfg.seed, "device": str(dev),
        "n_train": len(sp["X_tr"]), "n_known_test": len(sp["X_te"]), "n_ood": len(sp["X_ood"]),
        "known_classes": sp["classes"], "ood_classes": sp["ood_classes"], "dropped_features": dropped,
        "fit_seconds": round(fit_s, 1),
        **detection_metrics(s_kn, s_ood, s_va),
        **(closed_metrics(sp["y_te"], pred) if pred is not None else {}),
        **attack_metrics(scorer.attack(benign_te), scorer.attack(sp["X_ood"]), scorer.attack(benign_va)),
        **(scorer.extra(sp) if hasattr(scorer, "extra") else {}),
        "config": OmegaConf.to_container(cfg, resolve=True),
    }
    if hasattr(scorer, "tactic"):
        known = sorted({tactic_of(c, cfg.dataset.tactics) for c in sp["classes"]} - {"benign"})
        res["tactic_acc"] = tactic_accuracy(scorer.tactic(sp["X_ood"]), sp["ood_tactics"], known)

    with open(os.path.join(HydraConfig.get().runtime.output_dir, "result.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=str)
    log.info("%s", {k: v for k, v in res.items() if k not in ("config", "known_classes")})
    if cfg.artifact_dir:
        from .export import export
        export(cfg, scorer, sp, y, res)


if __name__ == "__main__":
    main()
