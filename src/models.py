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


BUILDERS = {
    "mlp": build_mlp, "xgboost": build_xgboost, "iforest": build_iforest,
    "autoencoder": build_autoencoder, "clad": build_clad, "closr": build_closr,
}
