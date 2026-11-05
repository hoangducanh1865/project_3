"""In danh sách lần chạy của bài báo, mỗi dòng một bộ tham số cho src.run.

Dùng: python scripts/grid.py [model ...] > runs.txt && python scripts/run_queue.py runs.txt 12 $OUT_ROOT
"""
import sys

FAMILIES = {
    "lycos": ["slowloris", "ssh", "bot", "portscan"],
    "nf_ton": ["ddos", "dos_attack", "xss", "injection", "password", "scanning", "backdoor", "mitm", "ransomware"],
    "nf_cic": ["bot", "hoic", "loic-http", "goldeneye", "hulk", "slowhttptest", "dos_attacks-slowloris", "ftp",
               "infilteration", "ssh"],
}
CROSS = [("lycos", "lycos18"), ("lycos18", "lycos"), ("nf_ton", "nf_cic"), ("nf_cic", "nf_ton")]
MODELS = ["xgboost", "iforest", "raw_knn", "closr", "closr_knn", "hc_closr"]
EXTRA = {"tabpfn": " eval_cap=5000"}    # TabPFN suy luận chậm nên đo trên ít mẫu hơn


def seeds(dataset, family=None):
    return (3, 4, 5) if dataset == "nf_cic" or family in ("mitm", "ransomware") else (2, 3, 4)


def lines(models):
    for m in models:
        for d, fams in FAMILIES.items():
            for f in fams:
                for s in seeds(d, f):
                    yield f"dataset={d} protocol.heldout={f} model={m} seed={s}{EXTRA.get(m, '')}"
        for d, t in CROSS:
            for s in seeds(d):
                yield f"dataset={d} protocol=cross protocol.target={t} model={m} seed={s}{EXTRA.get(m, '')}"


if __name__ == "__main__":
    print("\n".join(lines(sys.argv[1:] or MODELS)))
