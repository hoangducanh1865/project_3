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


def alert_metrics(s_known, pred_known, y_known, s_ood, pred_ood, s_val):
    """Góc nhìn vận hành: flow gây cảnh báo khi điểm OOD vượt ngưỡng hoặc mô hình xếp vào một lớp tấn công đã biết.

    - alert_rate: tỉ lệ flow OOD gây cảnh báo. - fpr_alert: tỉ lệ flow bình thường gây cảnh báo.
    - auroc_benign: AUROC của điểm OOD khi chỉ so OOD với flow bình thường.
    """
    thr = np.quantile(s_val, 0.95)
    ben = y_known == 0
    alert = lambda s, p: (s > thr) | (p != 0)
    y = np.r_[np.zeros(ben.sum()), np.ones(len(s_ood))]
    return {
        "alert_rate": float(alert(s_ood, pred_ood).mean()),
        "fpr_alert": float(alert(s_known[ben], pred_known[ben]).mean()),
        "auroc_benign": float(roc_auc_score(y, np.r_[s_known[ben], s_ood])),
    }


def attack_metrics(a_benign, a_ood, a_val_benign):
    """Điểm tấn công so với flow bình thường (bài toán nhị phân), ngưỡng là phân vị 95 của flow bình thường ở val."""
    return {f"atk_{k}": v for k, v in detection_metrics(a_benign, a_ood, a_val_benign).items()}
