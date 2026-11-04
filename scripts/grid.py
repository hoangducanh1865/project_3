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


def rows(scenarios, models, seeds):
    return [f"{s} model={m} seed={k}" for m in models for k in seeds for s in scenarios]


GRIDS = {
    # Vị trí hiện tại trên dữ liệu đã làm sạch: mô hình nhanh trước để có mốc so sánh
    "standing": rows(NF_P1 + NF_P2 + PE_P1 + PE_P2, ["stump", "xgboost"], range(3))
    + rows(NF_P1 + NF_P2 + PE_P1 + PE_P2, ["hc_closr", "closr_knn"], range(3)),
}

if __name__ == "__main__":
    print("\n".join(GRIDS[sys.argv[1]]))
