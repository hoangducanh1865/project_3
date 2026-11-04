"""Các mô hình baseline. Mỗi hàm build_* huấn luyện và trả về scorer.

scorer(X) -> (điểm OOD, nhãn dự đoán hoặc None). Điểm cao hơn là bất thường hơn.
"""
import math
import os
import sys

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def _t(x, dev):
    return torch.as_tensor(x, device=dev)


def _chunks(n, bs=8192):
    for i in range(0, n, bs):
        yield slice(i, min(i + bs, n))


def _mlp(d_in, hidden, d_out, dropout=0.0):
    layers, d = [], d_in
    for h in hidden:
        layers += [nn.Linear(d, h), nn.ReLU(), nn.Dropout(dropout)]
        d = h
    return nn.Sequential(*layers), nn.Linear(d, d_out)


def _num_embed(m, X, dev):
    """Embedding cho đặc trưng số (Gorishniy 2022): ple theo phân vị hoặc plr tuần hoàn. -> (module, số chiều vào MLP)."""
    kind = m.get("num_embed")
    if not kind:
        return None, X.shape[1]
    import rtdl_num_embeddings as rn
    if kind == "ple":
        Xb = torch.as_tensor(X[np.random.default_rng(0).permutation(len(X))[:100000]])
        bins = rn.compute_bins(Xb + 1e-6 * torch.randn_like(Xb), n_bins=m.n_bins)   # nhiễu nhỏ: cột hằng trong mẫu nhỏ
        emb = rn.PiecewiseLinearEmbeddings(bins, m.d_embedding, activation=True, version="B")
    else:
        emb = rn.PeriodicEmbeddings(X.shape[1], m.d_embedding, n_frequencies=m.n_frequencies,
                                    frequency_init_scale=m.sigma, lite=False)
    return nn.Sequential(emb, nn.Flatten(1)).to(dev), X.shape[1] * m.d_embedding


class _Embedded(nn.Module):
    def __init__(self, emb, net):
        super().__init__()
        self.emb, self.net = emb, net

    def forward(self, x):
        return self.net(self.emb(x))


def _with_embed(emb, net):
    return net if emb is None else _Embedded(emb, net)


# ---------------------------------------------------------------- MLP, MLP+KNN
def build_mlp(cfg, sp, dev):
    m = cfg.model
    K = len(sp["classes"])
    emb, d_in = _num_embed(m, sp["X_tr"], dev)
    body, head = _mlp(d_in, m.hidden, K, m.dropout)
    body, head = _with_embed(emb, body.to(dev)), head.to(dev)
    opt = torch.optim.Adam(list(body.parameters()) + list(head.parameters()), lr=m.lr)
    X, y = _t(sp["X_tr"], dev), _t(sp["y_tr"], dev)
    body.train(); head.train()
    for _ in range(m.epochs):
        perm = torch.randperm(len(X), device=dev)
        for i in range(0, len(X), m.batch_size):
            b = perm[i:i + m.batch_size]
            loss = F.cross_entropy(head(body(X[b])), y[b])
            opt.zero_grad(); loss.backward(); opt.step()
    body.eval(); head.eval()

    @torch.no_grad()
    def forward(Xn):
        emb, logits = [], []
        for s in _chunks(len(Xn)):
            e = body(_t(Xn[s], dev))
            emb.append(e); logits.append(head(e))
        return torch.cat(emb), torch.cat(logits)

    def attack(Xn):
        return (1 - forward(Xn)[1].softmax(-1)[:, 0]).cpu().numpy()

    if m.score == "msp":
        def scorer(Xn):
            _, lg = forward(Xn)
            p = lg.softmax(-1)
            return (1 - p.max(-1).values).cpu().numpy(), p.argmax(-1).cpu().numpy()
        scorer.attack = attack
        return scorer

    # KNN: khoảng cách tới láng giềng thứ k của lớp dự đoán, theo [13]
    emb_tr, _ = forward(sp["X_tr"])
    rng = np.random.default_rng(cfg.seed)
    index = []
    for c in range(K):
        idx = np.flatnonzero(sp["y_tr"] == c)
        idx = rng.permutation(idx)[: m.index_per_class]
        index.append(emb_tr[torch.as_tensor(idx, device=dev)])

    @torch.no_grad()
    def scorer(Xn):
        emb, lg = forward(Xn)
        pred = lg.argmax(-1)
        out = torch.zeros(len(Xn), device=dev)
        for c in range(K):
            rows = torch.nonzero(pred == c).squeeze(1)
            k = min(m.k, len(index[c]))
            for s in _chunks(len(rows), 4096):
                r = rows[s]
                d = torch.cdist(emb[r], index[c])
                out[r] = d.topk(k, largest=False).values[:, -1]
        return out.cpu().numpy(), pred.cpu().numpy()
    scorer.attack = attack
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
        return np.concatenate([clf.predict_proba(Xn[s]) for s in _chunks(len(Xn), m.batch)])

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
    return lambda Xn: (-clf.score_samples(Xn), None)


# ---------------------------------------------------------------- Autoencoder
def build_autoencoder(cfg, sp, dev):
    m = cfg.model
    d = sp["X_tr"].shape[1]
    sizes = [d] + list(m.hidden)
    layers = []
    for a, b in zip(sizes[:-1], sizes[1:]):
        layers += [nn.Linear(a, b), nn.ReLU()]
    rev = sizes[::-1]
    for i, (a, b) in enumerate(zip(rev[:-1], rev[1:])):
        layers += [nn.Linear(a, b)] + ([nn.ReLU()] if i < len(rev) - 2 else [])
    net = nn.Sequential(*layers).to(dev)
    rng = np.random.default_rng(cfg.seed)
    Xb = sp["X_tr"][sp["y_tr"] == 0]
    X = _t(Xb[rng.permutation(len(Xb))[: m.max_train]], dev)
    opt = torch.optim.Adam(net.parameters(), lr=m.lr)
    net.train()
    for _ in range(m.epochs):
        perm = torch.randperm(len(X), device=dev)
        for i in range(0, len(X), m.batch_size):
            b = X[perm[i:i + m.batch_size]]
            loss = F.mse_loss(net(b), b)
            opt.zero_grad(); loss.backward(); opt.step()
    net.eval()

    @torch.no_grad()
    def scorer(Xn):
        out = []
        for s in _chunks(len(Xn)):
            x = _t(Xn[s], dev)
            out.append(((net(x) - x) ** 2).mean(1).cpu())
        return torch.cat(out).numpy(), None
    return scorer


# ---------------------------------------------------------------- CLAD, CLOSR ([16])
def _repo():
    """Thêm mã nguồn gốc của [16] (github.com/jackwilkie/CLOSR) vào sys.path."""
    d = os.path.abspath(os.environ.get("CLOSR_DIR", "third_party/CLOSR"))
    if not os.path.isdir(d):
        raise FileNotFoundError(f"không thấy {d}. Chạy: git clone https://github.com/jackwilkie/CLOSR {d}")
    if d not in sys.path:
        sys.path.insert(0, d)


def _train_contrastive(model, crit, sp, m, dev):
    X, y = _t(sp["X_tr"], dev), _t(sp["y_tr"], dev)
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


def build_clad(cfg, sp, dev):
    _repo()
    from losses.clad_loss import CLADLoss
    from model.model import ContrastiveMLP
    m = cfg.model
    model = ContrastiveMLP(d_in=sp["X_tr"].shape[1], n_classes=len(sp["classes"]), d_out=m.d_out,
                           neurons=list(m.neurons), dropout=m.dropout, residual=False).to(dev)
    _train_contrastive(model, CLADLoss(m=m.margin, squared=True), sp, m, dev)

    @torch.no_grad()
    def embed(Xn):
        return torch.cat([model(_t(Xn[s], dev)) for s in _chunks(len(Xn))])

    ben = embed(sp["X_tr"][sp["y_tr"] == 0])
    centroid = F.normalize(ben.mean(0), dim=-1)
    return lambda Xn: (-(embed(Xn) @ centroid).cpu().numpy(), None)


def build_closr(cfg, sp, dev):
    _repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    m = cfg.model
    K = len(sp["classes"])
    emb, d_in = _num_embed(m, sp["X_tr"], dev)
    model = _with_embed(emb, CLOSRMLP(d_in=d_in, n_classes=K, d_out=m.d_out, neurons=list(m.neurons),
                                      dropout=m.dropout, residual=False).to(dev))
    _train_contrastive(model, CLOSRLoss(m=m.margin, squared=True, n_classes=K), sp, m, dev)

    # tâm của từng lớp, tính từ không gian embedding riêng của lớp đó
    sums = torch.zeros(K, m.d_out, device=dev)
    ytr = _t(sp["y_tr"], dev)
    with torch.no_grad():
        for s in _chunks(len(sp["X_tr"]), 4096):
            e, yb = model(_t(sp["X_tr"][s], dev)), ytr[s]
            for c in range(K):
                sel = e[yb == c, c]
                if len(sel):
                    sums[c] += F.normalize(sel, dim=-1).sum(0)
    centroids = F.normalize(sums, dim=-1)

    @torch.no_grad()
    def scorer(Xn):
        sims = []
        for s in _chunks(len(Xn)):
            e = F.normalize(model(_t(Xn[s], dev)), dim=-1)
            sims.append((e * centroids[None]).sum(-1))
        sims = torch.cat(sims)
        osr = (sims ** 2 * sims.softmax(-1)).sum(-1)  # công thức của eval_closr.py trong [24]
        return (-osr).cpu().numpy(), sims.argmax(-1).cpu().numpy()

    @torch.no_grad()
    def attack(Xn):
        return -torch.cat([F.normalize(model(_t(Xn[s], dev))[:, 0], dim=-1) @ centroids[0]
                           for s in _chunks(len(Xn))]).cpu().numpy()
    scorer.attack = attack
    return scorer


def build_closr_knn(cfg, sp, dev):
    """CLOSR + KNN, không có đầu chiến thuật: đối chứng để tách đóng góp của tầng chiến thuật trong HC-CLOSR."""
    _repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    from .hc_detector import HCDetector
    m = cfg.model
    K = len(sp["classes"])
    emb, d_in = _num_embed(m, sp["X_tr"], dev)
    model = _with_embed(emb, CLOSRMLP(d_in=d_in, n_classes=K, d_out=m.d_out, neurons=list(m.neurons),
                                      dropout=m.dropout, residual=False).to(dev))
    _train_contrastive(model, CLOSRLoss(m=m.margin, squared=True, n_classes=K), sp, m, dev)
    det = HCDetector.fit(model, sp, None, K, 0, m, cfg.seed, dev)

    def scorer(Xn):
        r = det.raw(Xn)
        return det.unified(r, "fam"), r["fam"][2]
    scorer.attack = det.attack
    return scorer


# ---------------------------------------------------------------- HC-CLOSR (đề xuất)
def tactic_of(name, tactics):
    """Chiến thuật ATT&CK của một lớp theo bảng conf/dataset/*.yaml; lớp không khớp mục nào là benign."""
    from .data import _norm
    hit = {t for t, keys in tactics.items() for k in keys if _norm(k) in _norm(name)}
    if len(hit) > 1:
        raise ValueError(f"lớp {name} khớp nhiều chiến thuật: {hit}")
    return hit.pop() if hit else "benign"


def build_hc_closr(cfg, sp, dev):
    """Encoder CLOSR [16] với hai nhóm đầu embedding: K đầu theo họ tấn công và T đầu theo chiến thuật."""
    _repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    from omegaconf import OmegaConf
    from .hc_detector import HCDetector
    from .response import likelihood, respond
    m = cfg.model
    K = len(sp["classes"])
    fam_tac = [tactic_of(c, cfg.dataset.tactics) for c in sp["classes"]]
    tac_names = ["benign"] + sorted(set(fam_tac) - {"benign"})
    T = len(tac_names)
    f2t = torch.as_tensor([tac_names.index(t) for t in fam_tac], device=dev)
    print(f"  chiến thuật đã biết: {dict(zip(sp['classes'], fam_tac))}", flush=True)

    d_in = sp["X_tr"].shape[1]
    emb, d_net = _num_embed(m, sp["X_tr"], dev)
    model = _with_embed(emb, CLOSRMLP(d_in=d_net, n_classes=K + T, d_out=m.d_out, neurons=list(m.neurons),
                                      dropout=m.dropout, residual=False).to(dev))
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
        """Độ đo riêng của HC-CLOSR: AUROC từng thành phần, phân tầng, chiến thuật và mức ứng phó trên OOD."""
        from sklearn.metrics import roc_auc_score
        r_kn, f_kn, tier_kn, _ = det.tiers(sp_["X_te"])
        r_ood, f_ood, tier_ood, tac_ood = det.tiers(sp_["X_ood"])
        y = np.r_[np.zeros(len(f_kn)), np.ones(len(f_ood))]
        auc = lambda a, b: float(roc_auc_score(y, np.r_[a, b]))
        res = {"auroc_closr_only": auc(r_kn["fam"][0], r_ood["fam"][0]),
               "auroc_knn_only": auc(r_kn["fam"][1], r_ood["fam"][1]),
               "auroc_tactic_level": auc(det.unified(r_kn, "tac"), det.unified(r_ood, "tac")),
               "tier1_known": float((tier_kn == 1).mean())}
        # tầng đúng của OOD: 2 nếu chiến thuật thật còn trong tập huấn luyện, ngược lại 3
        true_tac = np.array([tactic_of(c, cfg.dataset.tactics) for c in sp_["ood_names"]])
        exp_tier = np.where(np.isin(true_tac, tac_names[1:]), 2, 3)
        res.update({f"ood_tier{k}": float((tier_ood == k).mean()) for k in (1, 2, 3)})
        res["ood_tier_acc"] = float((tier_ood == exp_tier).mean())
        res["ood_expected_tier"] = {str(c): int(t) for c, t in zip(*np.unique(
            np.c_[sp_["ood_names"], exp_tier], axis=0).T)}
        sel = tier_ood == 2
        pred_names = np.array(tac_names)[tac_ood]
        res["ood_tactic_acc_tier2"] = float((pred_names[sel] == true_tac[sel]).mean()) if sel.any() else None
        # chiến thuật hệ thống thật sự báo: tầng 1 theo họ dự đoán, các tầng còn lại theo đầu chiến thuật
        used = np.where(tier_ood == 1, np.array(fam_tac)[r_ood["fam"][2]], pred_names)
        res["ood_tactic_acc"] = float((used == true_tac).mean())
        res["ood_as_benign"] = float((used == "benign").mean())
        # ứng phó cho mỗi cảnh báo OOD bị phát hiện
        L = likelihood(f_ood, det.s_va["fam"])
        acts = [respond(t, p, l, m.impact) for t, p, l in zip(tier_ood, pred_names, L) if t > 1]
        lv, cnt = np.unique([a["level"] for a in acts], return_counts=True) if acts else ([], [])
        res["ood_response_levels"] = dict(zip(map(str, lv), map(int, cnt)))
        res["ood_response_examples"] = acts[:3]
        return res

    scorer.extra = extra
    scorer.detector = det
    scorer.attack = det.attack
    return scorer


BUILDERS = {
    "mlp": build_mlp, "xgboost": build_xgboost, "iforest": build_iforest,
    "autoencoder": build_autoencoder, "clad": build_clad, "closr": build_closr,
    "hc_closr": build_hc_closr, "closr_knn": build_closr_knn, "tabpfn": build_tabpfn, "stump": build_stump,
}
