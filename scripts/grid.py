"""Lưới thí nghiệm cho run_queue.py, cố định trước khi xem kết quả. Dùng: python scripts/grid.py <tên lưới> > file"""
import sys

HELD = ["slowloris", "ssh", "bot", "portscan"]
NF_HELD = ["ddos", "dos_attack", "xss", "injection", "password", "scanning", "backdoor"]
DROP = "'+protocol.drop_like=[hdr_len,tcp_init_win]'"
P2 = ["protocol=p2", "dataset=lycos18 protocol=p2 protocol.target=lycos protocol.heldout=to17"]
NF_P1 = [f"dataset=nf_ton protocol=p1 protocol.heldout={h}" for h in NF_HELD]
NF_P2 = ["dataset=nf_ton protocol=p2 protocol.target=nf_cic protocol.heldout=to_cic",
         "dataset=nf_cic protocol=p2 protocol.target=nf_ton protocol.heldout=to_ton"]
PE_P1 = [f"protocol=pe protocol.heldout={h}" for h in HELD]
PE_P2 = [f"{p} {DROP}" for p in P2]
# Bản sạch: bỏ dấu vết ngăn xếp TCP của máy trong testbed, là bộ kịch bản chính để phát triển
NF_DROP = "protocol.drop_like=[TTL,TCP_WIN]"
NF_PE_P1 = [f"dataset=nf_ton protocol=pe protocol.heldout={h} '{NF_DROP}'" for h in NF_HELD]
NF_PE_P2 = [f"{s} '+{NF_DROP}'" for s in NF_P2]
CLEAN = NF_PE_P1 + NF_PE_P2 + PE_P1 + PE_P2
# Xác nhận: 12 kịch bản chưa dùng khi chọn quy tắc kết hợp (10 họ từ 10.000 flow của NF-CIC và 2 họ còn lại của NF-ToN).
# Quy tắc cố định trước khi chạy: điểm tấn công là Fisher của cos và KNN trên embedding.
NF_CIC_HELD = ["bot", "hoic", "loic-http", "goldeneye", "hulk", "slowhttptest", "dos_attacks-slowloris", "ftp",
               "infilteration", "ssh"]
CONFIRM = [f"dataset=nf_cic protocol=pe protocol.heldout={h} '{NF_DROP}'" for h in NF_CIC_HELD] \
    + [f"dataset=nf_ton protocol=pe protocol.heldout={h} '{NF_DROP}'" for h in ("ransomware", "mitm")]
CROSS = [f"{s} +protocol.align={a}" for s in NF_PE_P2 + PE_P2 for a in ("z", "quantile")]


def rows(scenarios, models, seeds):
    return [f"{s} model={m} seed={k}" for m in models for k in seeds for s in scenarios]


GRIDS = {
    # Vị trí hiện tại trên dữ liệu đã làm sạch: mô hình nhanh trước để có mốc so sánh
    "standing": rows(NF_P1 + NF_P2 + PE_P1 + PE_P2, ["stump", "xgboost"], range(3))
    + rows(NF_P1 + NF_P2 + PE_P1 + PE_P2, ["hc_closr", "closr_knn"], range(3)),
    # Mốc trên bản sạch. eval_cap là tham số không đổi, chỉ để mã băm khác lần chạy cũ chưa lưu điểm
    "clean": rows(NF_PE_P1 + NF_PE_P2, ["stump", "xgboost"], range(3))
    + rows(PE_P1 + PE_P2, ["xgboost eval_cap=50000"], range(3))
    + rows(NF_PE_P1 + NF_PE_P2, ["hc_closr"], range(3)),
    # Hiệu chỉnh mạng đích bằng flow không nhãn và huấn luyện lâu hơn
    "align": rows(CROSS, ["xgboost", "hc_closr"], [2]),
    "confirm": rows(CONFIRM, ["xgboost", "hc_closr"], [3]) + rows(CLEAN, ["xgboost", "hc_closr"], [3]),
    # Đối chứng chỉ học lưu lượng bình thường, cùng phép tách với HC-CLOSR
    "anomaly": rows(CLEAN, ["raw_knn", "iforest"], [2, 3]) + rows(CONFIRM, ["raw_knn", "iforest"], [3]),
    # CLOSR [16] làm baseline, cùng phép tách với HC-CLOSR: P1 trước, P2 sau
    "closr": rows(CONFIRM, ["closr"], [3]) + rows(NF_PE_P1 + PE_P1, ["closr"], [3, 2]) + rows(NF_PE_P2 + PE_P2, ["closr"], [3, 2]),
    "long": rows(CLEAN, ["hc_closr model.epochs=30"], [2]),
}

if __name__ == "__main__":
    print("\n".join(GRIDS[sys.argv[1]]))
