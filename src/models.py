"""Các mô hình. Mỗi hàm build_* huấn luyện và trả về scorer.

scorer(X) -> (điểm OOD, nhãn dự đoán hoặc None). Điểm cao hơn là bất thường hơn.
scorer.attack(X) -> điểm tấn công, so flow với lưu lượng bình thường.
scorer.tactic(X) -> chiến thuật tấn công dự đoán của từng flow, không có với mô hình chỉ học lưu lượng bình thường.
"""
import math

import numpy as np
import torch
import torch.nn.functional as F

from .common import chunks, tensor, use_closr_repo
from .data import tactic_of
from .hc_detector import HCDetector
from .metrics import tactic_accuracy
from .response import likelihood, respond


def _nearest_tactic(scores, classes, tactics):
    """Chiến thuật của họ tấn công gần nhất: scores có một cột cho mỗi lớp, cột 0 là benign nên không được chọn."""
    fam = np.array([tactic_of(c, tactics) for c in classes])
    return fam[1 + scores[:, 1:].argmax(1)]



def _as_attack(scorer):
    """Mô hình chỉ học lưu lượng bình thường: điểm bất thường cũng là điểm tấn công."""
    scorer.attack = lambda Xn: scorer(Xn)[0]
    return scorer


# ---------------------------------------------------------------- XGBoost
def build_xgboost(cfg, sp, dev):
    import xgboost as xgb
    m = cfg.model
    clf = xgb.XGBClassifier(
        n_estimators=m.n_estimators, max_depth=m.max_depth, learning_rate=m.lr,
        tree_method="hist", device="cuda" if dev.type == "cuda" else "cpu",
        objective="multi:softprob", random_state=cfg.seed)
    clf.fit(sp["X_tr"], sp["y_tr"])

    def scorer(Xn):
        p = clf.predict_proba(Xn)
        return 1 - p.max(1), p.argmax(1)
    scorer.attack = lambda Xn: 1 - clf.predict_proba(Xn)[:, 0]
    scorer.tactic = lambda Xn: _nearest_tactic(clf.predict_proba(Xn), sp["classes"], cfg.dataset.tactics)
    return scorer


# ---------------------------------------------------------------- Một đặc trưng
def build_stump(cfg, sp, dev):
    """Mức sàn của mọi kịch bản: một đặc trưng duy nhất, chọn trên train theo AUROC benign và tấn công (kiểm tra của Flood 2024)."""
    from sklearn.metrics import roc_auc_score
    idx = np.random.default_rng(cfg.seed).permutation(len(sp["X_tr"]))[:200_000]
    X, y = sp["X_tr"][idx], sp["y_tr"][idx] != 0
    auc = np.array([roc_auc_score(y, c) if c.std() > 0 else .5 for c in X.T])
    j = int(np.abs(auc - .5).argmax())
    sign = 1 if auc[j] >= .5 else -1

    def scorer(Xn):
        return sign * Xn[:, j], None
    scorer.attack = lambda Xn: sign * Xn[:, j]
    scorer.extra = lambda sp_: {"stump_feature": str(sp_["cols"][j]), "stump_train_auroc": float(max(auc[j], 1 - auc[j]))}
    return scorer


# ---------------------------------------------------------------- TabPFN
def build_tabpfn(cfg, sp, dev):
    """TabPFN v2 (Hollmann 2025): không huấn luyện, nạp tối đa m.max_train mẫu làm ngữ cảnh.

    TabPFN chỉ hỗ trợ 10 lớp nên học ở mức chiến thuật. Nhãn dự đoán trả về là họ đầu tiên của chiến thuật, chỉ dùng để
    phân biệt bình thường với tấn công; acc và macro_f1 của mô hình này không có ý nghĩa.
    """
    from tabpfn import TabPFNClassifier
    from tabpfn.constants import ModelVersion
    m = cfg.model
    rng = np.random.default_rng(cfg.seed)
    fam_tac = [tactic_of(c, cfg.dataset.tactics) for c in sp["classes"]]
    names = ["benign"] + sorted(set(fam_tac) - {"benign"})
    f2t = np.array([names.index(t) for t in fam_tac])
    first = np.array([fam_tac.index(t) for t in names])
    y = f2t[sp["y_tr"]]
    per = m.max_train // len(names)
    idx = np.concatenate([rng.permutation(np.flatnonzero(y == c))[:per] for c in range(len(names))])
    clf = TabPFNClassifier.create_default_for_version(ModelVersion.V2, device=str(dev), n_estimators=m.n_estimators,
                                                      random_state=cfg.seed, ignore_pretraining_limits=True)
    clf.fit(sp["X_tr"][idx], y[idx])

    def proba(Xn):
        return np.concatenate([clf.predict_proba(Xn[s]) for s in chunks(len(Xn), m.batch)])

    def scorer(Xn):
        p = proba(Xn)
        return 1 - p.max(1), first[p.argmax(1)]
    scorer.attack = lambda Xn: 1 - proba(Xn)[:, 0]
    return scorer


# ---------------------------------------------------------------- Isolation Forest
def build_iforest(cfg, sp, dev):
    from sklearn.ensemble import IsolationForest
    m = cfg.model
    rng = np.random.default_rng(cfg.seed)
    Xb = sp["X_tr"][sp["y_tr"] == 0]
    Xb = Xb[rng.permutation(len(Xb))[: m.max_train]]
    clf = IsolationForest(n_estimators=m.n_estimators, random_state=cfg.seed, n_jobs=-1).fit(Xb)

    def scorer(Xn):
        return -clf.score_samples(Xn), None
    return _as_attack(scorer)


def build_raw_knn(cfg, sp, dev):
    """Đối chứng không cần học: khoảng cách tới láng giềng thứ k trong flow bình thường, trên đặc trưng đã chuẩn hoá."""
    m = cfg.model
    rng = np.random.default_rng(cfg.seed)
    Xb = sp["X_tr"][sp["y_tr"] == 0]
    index = tensor(Xb[rng.permutation(len(Xb))[: m.index_per_class]], dev)

    @torch.no_grad()
    def scorer(Xn):
        d = [torch.cdist(tensor(Xn[s], dev), index).topk(m.k, largest=False).values[:, -1] for s in chunks(len(Xn), 4096)]
        return torch.cat(d).cpu().numpy(), None
    return _as_attack(scorer)


# ---------------------------------------------------------------- CLOSR
def _train_contrastive(model, crit, sp, m, dev):
    X, y = tensor(sp["X_tr"], dev), tensor(sp["y_tr"], dev)
    cnt = torch.bincount(y).float()
    w = (1.0 / cnt)[y]  # lấy mẫu cân bằng theo lớp
    steps = m.epochs * m.steps_per_epoch
    warm = max(1, int(0.1 * steps))
    opt = torch.optim.AdamW(model.parameters(), lr=m.lr, weight_decay=m.weight_decay)
    model.train()
    for t in range(steps):
        lr = m.lr * (t + 1) / warm if t < warm else m.lr * 0.5 * (1 + math.cos(math.pi * (t - warm) / max(1, steps - warm)))
        for g in opt.param_groups:
            g["lr"] = lr
        idx = torch.multinomial(w, m.batch_size, replacement=True)
        loss = crit(x=model(X[idx]), y=y[idx])
        opt.zero_grad(); loss.backward(); opt.step()
        if (t + 1) % max(1, steps // 10) == 0:
            print(f"  bước {t + 1}/{steps} loss={loss.item():.4f}", flush=True)
    model.eval()


def build_closr(cfg, sp, dev):
    use_closr_repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    m = cfg.model
    K = len(sp["classes"])
    model = CLOSRMLP(d_in=sp["X_tr"].shape[1], n_classes=K, d_out=m.d_out, neurons=list(m.neurons),
                     dropout=m.dropout, residual=False).to(dev)
    _train_contrastive(model, CLOSRLoss(m=m.margin, squared=True, n_classes=K), sp, m, dev)

    # tâm của từng lớp, tính từ không gian embedding riêng của lớp đó
    sums = torch.zeros(K, m.d_out, device=dev)
    ytr = tensor(sp["y_tr"], dev)
    with torch.no_grad():
        for s in chunks(len(sp["X_tr"]), 4096):
            e, yb = model(tensor(sp["X_tr"][s], dev)), ytr[s]
            for c in range(K):
                sel = e[yb == c, c]
                if len(sel):
                    sums[c] += F.normalize(sel, dim=-1).sum(0)
    centroids = F.normalize(sums, dim=-1)

    @torch.no_grad()
    def similarity(Xn):
        return torch.cat([(F.normalize(model(tensor(Xn[s], dev)), dim=-1) * centroids[None]).sum(-1)
                          for s in chunks(len(Xn))])

    def scorer(Xn):
        sims = similarity(Xn)
        osr = (sims ** 2 * sims.softmax(-1)).sum(-1)  # công thức của eval_closr.py trong mã gốc
        return (-osr).cpu().numpy(), sims.argmax(-1).cpu().numpy()

    scorer.attack = lambda Xn: -similarity(Xn)[:, 0].cpu().numpy()
    scorer.tactic = lambda Xn: _nearest_tactic(similarity(Xn).cpu().numpy(), sp["classes"], cfg.dataset.tactics)
    return scorer


def build_closr_knn(cfg, sp, dev):
    """CLOSR + KNN, không có đầu chiến thuật: ablation của HC-CLOSR."""
    use_closr_repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    m = cfg.model
    K = len(sp["classes"])
    model = CLOSRMLP(d_in=sp["X_tr"].shape[1], n_classes=K, d_out=m.d_out, neurons=list(m.neurons),
                     dropout=m.dropout, residual=False).to(dev)
    _train_contrastive(model, CLOSRLoss(m=m.margin, squared=True, n_classes=K), sp, m, dev)
    det = HCDetector.fit(model, sp, None, K, 0, m, cfg.seed, dev)

    def scorer(Xn):
        r = det.raw(Xn)
        return det.unified(r, "fam"), r["fam"][2]
    scorer.attack = det.attack
    scorer.tactic = lambda Xn: _nearest_tactic(det.similarity(Xn), sp["classes"], cfg.dataset.tactics)
    return scorer


# ---------------------------------------------------------------- HC-CLOSR (đề xuất)
def build_hc_closr(cfg, sp, dev):
    """Encoder CLOSR [16] với hai nhóm đầu embedding: K đầu theo họ tấn công và T đầu theo chiến thuật."""
    use_closr_repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    from omegaconf import OmegaConf
    m = cfg.model
    K = len(sp["classes"])
    fam_tac = [tactic_of(c, cfg.dataset.tactics) for c in sp["classes"]]
    tac_names = ["benign"] + sorted(set(fam_tac) - {"benign"})
    T = len(tac_names)
    f2t = torch.as_tensor([tac_names.index(t) for t in fam_tac], device=dev)
    print(f"  chiến thuật đã biết: {dict(zip(sp['classes'], fam_tac))}", flush=True)

    d_in = sp["X_tr"].shape[1]
    model = CLOSRMLP(d_in=d_in, n_classes=K + T, d_out=m.d_out, neurons=list(m.neurons),
                     dropout=m.dropout, residual=False).to(dev)
    fam_loss = CLOSRLoss(m=m.margin, squared=True, n_classes=K)
    tac_loss = CLOSRLoss(m=m.margin, squared=True, n_classes=T)
    crit = lambda x, y: fam_loss(x=x[:, :K], y=y) + m.tactic_weight * tac_loss(x=x[:, K:], y=f2t[y])
    _train_contrastive(model, crit, sp, m, dev)

    det = HCDetector.fit(model, sp, f2t.cpu().numpy(), K, T, m, cfg.seed, dev)
    det.info = {
        "arch": {"d_in": d_in, "n_heads": K + T, "d_out": m.d_out, "neurons": list(m.neurons), "dropout": m.dropout},
        "classes": [str(c) for c in sp["classes"]], "fam_tac": fam_tac, "tac_names": tac_names,
        "impact": OmegaConf.to_container(m.impact), "mu": sp["mu"], "sd": sp["sd"],
    }

    def scorer(Xn):
        r = det.raw(Xn)
        return det.unified(r, "fam"), r["fam"][2]

    def extra(sp_):
        """Phân tầng và mức ứng phó trên flow OOD."""
        _, f_ood, tier_ood, tac_ood = det.tiers(sp_["X_ood"])
        true_tac = sp_["ood_tactics"]
        # tầng đúng của OOD: 2 nếu chiến thuật thật còn trong tập huấn luyện, ngược lại 3
        exp_tier = np.where(np.isin(true_tac, tac_names[1:]), 2, 3)
        res = {f"ood_tier{k}": float((tier_ood == k).mean()) for k in (1, 2, 3)}
        res["ood_tier_acc"] = float((tier_ood == exp_tier).mean())
        near = _nearest_tactic(det.similarity(sp_["X_ood"]), sp["classes"], cfg.dataset.tactics)
        res["tactic_acc_family"] = tactic_accuracy(near, true_tac, tac_names[1:])
        L = likelihood(f_ood, det.s_va["fam"])
        pred = np.array(tac_names)[tac_ood]
        levels = [respond(t, p, l, m.impact)["level"] for t, p, l in zip(tier_ood, pred, L) if t > 1]
        lv, cnt = np.unique(levels, return_counts=True) if levels else ([], [])
        res["ood_response_levels"] = dict(zip(map(str, lv), map(int, cnt)))
        return res

    scorer.extra = extra
    scorer.detector = det
    scorer.attack = det.attack
    scorer.tactic = lambda Xn: np.array(tac_names)[1 + det.similarity(Xn, 1)[:, 1:].argmax(1)]
    return scorer


BUILDERS = {
    "stump": build_stump, "xgboost": build_xgboost, "tabpfn": build_tabpfn, "iforest": build_iforest,
    "raw_knn": build_raw_knn, "closr": build_closr, "closr_knn": build_closr_knn, "hc_closr": build_hc_closr,
}
