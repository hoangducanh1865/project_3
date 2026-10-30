"""Đề xuất biện pháp ứng phó cho từng cảnh báo (slide tuần 2, mục 3.4, 4.1, 4.2).

Đầu vào: tầng (1 đã biết, 2 biến thể của chiến thuật đã biết, 3 hành vi hoàn toàn mới), chiến thuật dự đoán,
L (khả năng, 1-5, từ điểm OOD) và I (tác động, 1-5, theo chiến thuật). R = L x I -> mức M0-M4.
Biện pháp lấy từ D3FEND (đã tra API, xem agents/claude/knowledge.md); dòng discovery là quy tắc tự đề xuất.
Toàn bộ bảng là quy tắc thiết kế, chưa đối chiếu chuyên gia.
"""
import numpy as np

# (mức, tên, ví dụ hành động, đảo ngược được)
LEVELS = [
    (3, "M0", "theo dõi: ghi log, tăng độ chi tiết giám sát", True),
    (6, "M1", "cảnh báo: gửi cảnh báo, đưa vào hàng đợi xác minh", True),
    (12, "M2", "hạn chế mềm: giới hạn kết nối mới theo nguồn, thu thập bằng chứng", True),
    (16, "M3", "ngăn chặn: chặn nguồn có thời hạn, ngắt phiên", True),
    (25, "M4", "cô lập: cách ly máy chủ, thu hồi thông tin xác thực", False),
]

# Ngay lập tức (Isolate, Evict) và củng cố sau (Harden, Deceive), theo D3FEND [22]
D3FEND = {
    "impact": (["Inbound Traffic Filtering", "Network Traffic Filtering"], []),
    "credential_access": (["Network Traffic Filtering", "Credential Transmission Scoping", "Credential Revocation",
                           "Authentication Cache Invalidation"],
                          ["Multi-factor Authentication", "One-time Password", "Strong Password Policy",
                           "Decoy User Credential"]),
    "initial_access": (["Inbound Traffic Filtering", "Network Traffic Filtering"],
                       ["Process Segment Execution Prevention", "Segment Address Offset Randomization"]),
    "command_and_control": (["Outbound Traffic Filtering", "DNS Denylisting", "Network Traffic Filtering",
                             "File Eviction"], ["Decoy File", "Restore File"]),
    # D3FEND trả rỗng cho T1046, T1595: quy tắc tự đề xuất
    "discovery": (["giới hạn kết nối mới (tự đề xuất)", "chặn nguồn quét có thời hạn (tự đề xuất)"],
                  ["đóng cổng không dùng (tự đề xuất)"]),
}
# Tầng 3: hành động chung có trong danh sách Isolate của cả 6 kỹ thuật đã tra
GENERIC = (["Network Traffic Filtering có thời hạn", "lưu bằng chứng"], [])


def likelihood(score, val_scores):
    """L từ 1 đến 5 theo vị trí của điểm OOD so với dữ liệu known (val). Chưa dùng tần suất cảnh báo."""
    q = np.quantile(val_scores, [0.95, 0.99, 0.999, 1.0])
    return 1 + np.searchsorted(q, score, side="right")


def respond(tier, tactic, L, impact):
    """Một cảnh báo -> mức ứng phó và danh sách biện pháp."""
    tac = tactic if tier < 3 else "unknown"
    I = int(impact.get(tac, impact["unknown"]))
    R = int(L) * I
    _, level, action, reversible = next(lv for lv in LEVELS if R <= lv[0])
    now, later = D3FEND.get(tac, GENERIC) if tier < 3 else GENERIC
    # Tầng 1: tự động. Tầng 2-3: từ M3 phải có chuyên viên duyệt. M4 luôn duyệt (khó đảo ngược).
    if level == "M4" or (tier > 1 and level == "M3"):
        mode = "chuyên viên duyệt"
    elif level == "M2":
        mode = "tự động, báo chuyên viên"
    else:
        mode = "tự động"
    return {"tier": int(tier), "tactic": tac, "L": int(L), "I": I, "R": R, "level": level, "action": action,
            "reversible": reversible, "mode": mode, "d3fend_now": now, "d3fend_later": later}
