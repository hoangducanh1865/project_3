"""Độ đo phát hiện OOD và phân loại đóng."""
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, roc_curve


def detection_metrics(s_known, s_ood, s_val):
    """Điểm cao hơn nghĩa là bất thường hơn. OOD là lớp dương.

    - auroc: AUROC phân biệt OOD với known-test.
    - fpr95: tỉ lệ known-test bị báo nhầm khi ngưỡng bắt được 95% OOD.
    - det_rate: tỉ lệ OOD bị phát hiện với ngưỡng chọn chỉ từ dữ liệu known (phân vị 95 của val).
    - fpr_thr: tỉ lệ known-test bị báo nhầm với ngưỡng đó.
    """
    y = np.r_[np.zeros(len(s_known)), np.ones(len(s_ood))]
    s = np.r_[s_known, s_ood]
    fpr, tpr, _ = roc_curve(y, s)
    thr = np.quantile(s_val, 0.95)
    return {
        "auroc": float(roc_auc_score(y, s)),
        "fpr95": float(fpr[np.searchsorted(tpr, 0.95)]),
        "det_rate": float((s_ood > thr).mean()),
        "fpr_thr": float((s_known > thr).mean()),
    }


def closed_metrics(y_true, y_pred):
    return {
        "acc": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }
