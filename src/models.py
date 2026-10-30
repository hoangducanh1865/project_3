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


# ---------------------------------------------------------------- MLP, MLP+KNN
def build_mlp(cfg, sp, dev):
    m = cfg.model
    K = len(sp["classes"])
    body, head = _mlp(sp["X_tr"].shape[1], m.hidden, K, m.dropout)
    body, head = body.to(dev), head.to(dev)
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

    if m.score == "msp":
        def scorer(Xn):
            _, lg = forward(Xn)
            p = lg.softmax(-1)
            return (1 - p.max(-1).values).cpu().numpy(), p.argmax(-1).cpu().numpy()
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
    model = CLOSRMLP(d_in=sp["X_tr"].shape[1], n_classes=K, d_out=m.d_out, neurons=list(m.neurons),
                     dropout=m.dropout, residual=False).to(dev)
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
    """Encoder CLOSR [16] với hai nhóm đầu embedding: K đầu theo họ tấn công và T đầu theo chiến thuật.

    Mỗi tầng: likelihood CLOSR (công thức eval_closr.py) và khoảng cách KNN tới láng giềng thứ k của lớp dự đoán
    trên embedding của lớp đó [13]. Hai điểm được chuẩn hoá theo dữ liệu known (val) rồi cộng lại.
    Tầng 1: không OOD ở mức họ. Tầng 2: OOD ở mức họ, không OOD ở mức chiến thuật và chiến thuật dự đoán là một
    chiến thuật tấn công. Tầng 3: còn lại.
    """
    _repo()
    from losses.closr_loss import CLOSRLoss
    from model.model import CLOSRMLP
    from .response import likelihood, respond
    m = cfg.model
    K = len(sp["classes"])
    fam_tac = [tactic_of(c, cfg.dataset.tactics) for c in sp["classes"]]
    tac_names = ["benign"] + sorted(set(fam_tac) - {"benign"})
    T = len(tac_names)
    f2t = torch.as_tensor([tac_names.index(t) for t in fam_tac], device=dev)
    print(f"  chiến thuật đã biết: {dict(zip(sp['classes'], fam_tac))}", flush=True)

    model = CLOSRMLP(d_in=sp["X_tr"].shape[1], n_classes=K + T, d_out=m.d_out, neurons=list(m.neurons),
                     dropout=m.dropout, residual=False).to(dev)
    fam_loss = CLOSRLoss(m=m.margin, squared=True, n_classes=K)
    tac_loss = CLOSRLoss(m=m.margin, squared=True, n_classes=T)
    crit = lambda x, y: fam_loss(x=x[:, :K], y=y) + m.tactic_weight * tac_loss(x=x[:, K:], y=f2t[y])
    _train_contrastive(model, crit, sp, m, dev)

    @torch.no_grad()
    def embed(Xn):
        return torch.cat([F.normalize(model(_t(Xn[s], dev)), dim=-1) for s in _chunks(len(Xn), 4096)])

    # tâm và chỉ mục KNN của từng lớp, trên embedding riêng của lớp đó
    rng = np.random.default_rng(cfg.seed)
    ytr = sp["y_tr"]
    levels = []
    for heads, lab in ((slice(0, K), ytr), (slice(K, K + T), f2t.cpu().numpy()[ytr])):
        n = heads.stop - heads.start
        cents, index = [], []
        for c in range(n):
            idx = rng.permutation(np.flatnonzero(lab == c))[: m.index_per_class]
            e = embed(sp["X_tr"][idx])[:, heads.start + c]
            cents.append(F.normalize(e.mean(0), dim=-1))
            index.append(e)
        levels.append((heads, torch.stack(cents), index))

    @torch.no_grad()
    def raw(Xn):
        """-> {tầng: (điểm CLOSR, điểm KNN, lớp dự đoán)}, điểm cao là bất thường hơn."""
        out = {}
        e_all = embed(Xn)
        for name, (heads, cents, index) in zip(("fam", "tac"), levels):
            e = e_all[:, heads]
            sims = (e * cents[None]).sum(-1)
            osr = (sims ** 2 * sims.softmax(-1)).sum(-1)
            pred = sims.argmax(-1)
            knn = torch.zeros(len(Xn), device=dev)
            for c in range(len(index)):
                rows = torch.nonzero(pred == c).squeeze(1)
                k = min(m.k, len(index[c]))
                for s in _chunks(len(rows), 4096):
                    r = rows[s]
                    d = 1 - e[r, c] @ index[c].T
                    knn[r] = d.topk(k, largest=False).values[:, -1]
            out[name] = ((-osr).cpu().numpy(), knn.cpu().numpy(), pred.cpu().numpy())
        return out

    # chuẩn hoá và ngưỡng chỉ từ dữ liệu known (val)
    r_va = raw(sp["X_va"])
    stats = {lv: [(a.mean(), a.std() + 1e-12) for a in r_va[lv][:2]] for lv in r_va}

    def unified(r, lv):
        (m1, s1), (m2, s2) = stats[lv]
        return (r[lv][0] - m1) / s1 + (r[lv][1] - m2) / s2

    s_va = {lv: unified(r_va, lv) for lv in r_va}
    thr = {lv: np.quantile(s_va[lv], m.quantile) for lv in s_va}

    def scorer(Xn):
        r = raw(Xn)
        return unified(r, "fam"), r["fam"][2]

    def tiers(Xn):
        r = raw(Xn)
        f, t = unified(r, "fam"), unified(r, "tac")
        tac_pred = r["tac"][2]
        tier = np.where(f <= thr["fam"], 1, np.where((t <= thr["tac"]) & (tac_pred != 0), 2, 3))
        return r, f, tier, tac_pred

    def extra(sp_):
        """Độ đo riêng của HC-CLOSR: AUROC từng thành phần, phân tầng, chiến thuật và mức ứng phó trên OOD."""
        from sklearn.metrics import roc_auc_score
        r_kn, f_kn, tier_kn, _ = tiers(sp_["X_te"])
        r_ood, f_ood, tier_ood, tac_ood = tiers(sp_["X_ood"])
        y = np.r_[np.zeros(len(f_kn)), np.ones(len(f_ood))]
        auc = lambda a, b: float(roc_auc_score(y, np.r_[a, b]))
        res = {"auroc_closr_only": auc(r_kn["fam"][0], r_ood["fam"][0]),
               "auroc_knn_only": auc(r_kn["fam"][1], r_ood["fam"][1]),
               "auroc_tactic_level": auc(unified(r_kn, "tac"), unified(r_ood, "tac")),
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
        # ứng phó cho mỗi cảnh báo OOD bị phát hiện
        L = likelihood(f_ood, s_va["fam"])
        acts = [respond(t, p, l, m.impact) for t, p, l in zip(tier_ood, pred_names, L) if t > 1]
        lv, cnt = np.unique([a["level"] for a in acts], return_counts=True) if acts else ([], [])
        res["ood_response_levels"] = dict(zip(map(str, lv), map(int, cnt)))
        res["ood_response_examples"] = acts[:3]
        return res

    scorer.extra = extra
    return scorer


BUILDERS = {
    "mlp": build_mlp, "xgboost": build_xgboost, "iforest": build_iforest,
    "autoencoder": build_autoencoder, "clad": build_clad, "closr": build_closr,
    "hc_closr": build_hc_closr,
}
