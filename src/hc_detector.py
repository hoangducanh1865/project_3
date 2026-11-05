"""Phần suy luận của HC-CLOSR, dùng chung cho đánh giá (src/models.py) và phục vụ web (deploy/modal_app.py)."""
import numpy as np
import torch
import torch.nn.functional as F

from .models import _chunks, _repo, _t
from .response import L_KNOWN, likelihood, respond


class HCDetector:
    """Tính điểm OOD ở mức họ và mức chiến thuật, phân 3 tầng rồi đề xuất biện pháp ứng phó.

    Mỗi tầng: likelihood CLOSR (công thức eval_closr.py) và khoảng cách KNN tới láng giềng thứ k của lớp dự đoán
    trên embedding của lớp đó [13]. Hai điểm được chuẩn hoá theo dữ liệu known (val) rồi cộng lại.
    Tầng 1: không OOD ở mức họ. Tầng 2: OOD ở mức họ, không OOD ở mức chiến thuật và chiến thuật dự đoán là một
    chiến thuật tấn công. Tầng 3: còn lại.
    """

    has_tier2 = True

    def __init__(self, model, levels, k, dev):
        self.model, self.levels, self.k, self.dev = model, levels, k, dev
        self.stats, self.thr, self.s_va, self.info = None, None, None, {}

    @classmethod
    def fit(cls, model, sp, f2t, K, T, m, seed, dev):
        """Tâm và chỉ mục KNN từ dữ liệu huấn luyện; chuẩn hoá và ngưỡng chỉ từ dữ liệu known (val)."""
        det = cls(model, [], m.k, dev)
        rng = np.random.default_rng(seed)
        ytr = sp["y_tr"]
        for start, stop, lab in [(0, K, ytr)] + ([(K, K + T, f2t[ytr])] if T else []):
            cents, index = [], []
            for c in range(stop - start):
                idx = rng.permutation(np.flatnonzero(lab == c))[: m.index_per_class]
                e = det.embed(sp["X_tr"][idx])[:, start + c]
                cents.append(F.normalize(e.mean(0), dim=-1))
                index.append(e)
            det.levels.append((slice(start, stop), torch.stack(cents), index))
        r_va = det.raw(sp["X_va"])
        det.stats = {lv: [(float(a.mean()), float(a.std() + 1e-12)) for a in r_va[lv][:2]] for lv in r_va}
        det.s_va = {lv: det.unified(r_va, lv) for lv in r_va}
        det.thr = {lv: float(np.quantile(det.s_va[lv], m.quantile)) for lv in det.s_va}
        return det

    @torch.no_grad()
    def embed(self, Xn):
        return torch.cat([F.normalize(self.model(_t(Xn[s], self.dev)), dim=-1) for s in _chunks(len(Xn), 4096)])

    @torch.no_grad()
    def raw(self, Xn):
        """-> {tầng: (điểm CLOSR, điểm KNN, lớp dự đoán)}, điểm cao là bất thường hơn."""
        out = {}
        e_all = self.embed(Xn)
        for name, (heads, cents, index) in zip(("fam", "tac"), self.levels):
            e = e_all[:, heads]
            sims = (e * cents[None]).sum(-1)
            osr = (sims ** 2 * sims.softmax(-1)).sum(-1)
            pred = sims.argmax(-1)
            knn = torch.zeros(len(Xn), device=self.dev)
            for c in range(len(index)):
                rows = torch.nonzero(pred == c).squeeze(1)
                k = min(self.k, len(index[c]))
                for s in _chunks(len(rows), 4096):
                    r = rows[s]
                    d = 1 - e[r, c] @ index[c].T
                    knn[r] = d.topk(k, largest=False).values[:, -1]
            out[name] = ((-osr).cpu().numpy(), knn.cpu().numpy(), pred.cpu().numpy())
        return out

    @torch.no_grad()
    def parts(self, Xn):
        """Thành phần điểm của từng flow: độ tương đồng với tâm và khoảng cách KNN tới mọi lớp, ở từng mức."""
        e_all = self.embed(Xn)
        out = {}
        for name, (heads, cents, index) in zip(("fam", "tac"), self.levels):
            e = e_all[:, heads]
            out[f"sim_{name}"] = (e * cents[None]).sum(-1).cpu().numpy()
            out[f"knn_{name}"] = torch.stack([torch.cat([
                (1 - e[s, c] @ index[c].T).topk(min(self.k, len(index[c])), largest=False).values[:, -1]
                for s in _chunks(len(Xn), 4096)]) for c in range(len(index))], 1).cpu().numpy()
        return out

    def unified(self, r, lv):
        (m1, s1), (m2, s2) = self.stats[lv]
        return (r[lv][0] - m1) / s1 + (r[lv][1] - m2) / s2

    def attack(self, Xn):
        """Điểm tấn công: càng xa tâm lưu lượng bình thường (trong không gian của lớp đó) càng cao."""
        return -(self.embed(Xn)[:, 0] @ self.levels[0][1][0]).cpu().numpy()

    def tiers(self, Xn):
        r = self.raw(Xn)
        f, t = self.unified(r, "fam"), self.unified(r, "tac")
        tac_pred = r["tac"][2]
        tier = np.where(f <= self.thr["fam"], 1, np.where((t <= self.thr["tac"]) & (tac_pred != 0), 2, 3))
        return r, f, tier, tac_pred

    def analyze(self, X):
        """X: đặc trưng gốc theo đúng thứ tự info["columns"] -> kết quả và biện pháp đề xuất của từng flow."""
        i = self.info
        Xz = ((X - i["mu"]) / i["sd"]).astype(np.float32)
        r, f, tier, tac_pred = self.tiers(Xz)
        fam_pred = r["fam"][2]
        L = likelihood(f, self.s_va["fam"])
        out = []
        for n in range(len(Xz)):
            t, fam = int(tier[n]), str(i["classes"][fam_pred[n]])
            base = {"tier": t, "family": fam, "score": round(float(f[n]), 3)}
            if t == 1 and fam_pred[n] == 0:     # lớp 0 luôn là lưu lượng bình thường
                out.append({**base, "status": "normal"})
            elif t == 1:                        # tấn công đã biết: chiến thuật lấy từ họ, không từ đầu chiến thuật
                out.append({**base, "status": "alert", **respond(1, i["fam_tac"][fam_pred[n]], L_KNOWN, i["impact"])})
            else:
                out.append({**base, "status": "alert",
                            **respond(t, i["tac_names"][tac_pred[n]], int(L[n]), i["impact"])})
        return out

    def state(self):
        weights = {k: v.cpu() for k, v in self.model.state_dict().items()}
        # clone: e là lát cắt của embedding đầy đủ, không clone thì torch.save ghi cả tensor gốc
        levels = [(s.start, s.stop, c.cpu(), [e.cpu().clone() for e in ix]) for s, c, ix in self.levels]
        return {"weights": weights, "levels": levels, "k": self.k, "stats": self.stats, "thr": self.thr,
                "s_va": self.s_va, "info": self.info}

    @classmethod
    def from_state(cls, st, dev="cpu"):
        _repo()
        from model.model import CLOSRMLP
        a = st["info"]["arch"]
        model = CLOSRMLP(d_in=a["d_in"], n_classes=a["n_heads"], d_out=a["d_out"], neurons=a["neurons"],
                         dropout=a["dropout"], residual=False).to(dev)
        model.load_state_dict(st["weights"])
        model.eval()
        levels = [(slice(a_, b_), c.to(dev), [e.to(dev) for e in ix]) for a_, b_, c, ix in st["levels"]]
        det = cls(model, levels, st["k"], dev)
        det.stats, det.thr, det.s_va, det.info = st["stats"], st["thr"], st["s_va"], st["info"]
        return det
