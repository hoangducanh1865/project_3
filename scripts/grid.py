"""In danh sách lần chạy, mỗi dòng một bộ tham số cho src.run.

Dùng: python scripts/grid.py [model ...] > runs.txt && python scripts/run_queue.py runs.txt 12 $OUT_ROOT
DataSense: GRID=datasense SEEDS=0,1 python scripts/grid.py > runs.txt
"""
import os
import sys

FAMILIES = {
    "lycos": ["slowloris", "ssh", "bot", "portscan"],
    "nf_ton": ["ddos", "dos_attack", "xss", "injection", "password", "scanning", "backdoor", "mitm", "ransomware"],
    "nf_cic": ["bot", "hoic", "loic-http", "goldeneye", "hulk", "slowhttptest", "dos_attacks-slowloris", "ftp",
               "infilteration", "ssh"],
}
# DataSense (CIC IIoT 2025): 19 họ tự gom ở src/datasense.py; họ nào không có trong dữ liệu đã trích thì bỏ qua.
DATASENSE = ["host_discovery", "port_scan", "os_scan", "vuln_scan", "ssh_bruteforce", "telnet_bruteforce", "web_attack",
             "arp_spoofing", "impersonation", "ip_spoofing", "mirai", "syn_flood", "land_flood", "tcp_flood",
             "udp_flood", "icmp_flood", "http_flood", "mqtt_flood", "slowloris"]
CROSS = [("lycos", "lycos18"), ("lycos18", "lycos"), ("nf_ton", "nf_cic"), ("nf_cic", "nf_ton")]
MODELS = ["xgboost", "iforest", "raw_knn", "closr", "closr_knn", "hc_closr"]
if os.environ.get("GRID") == "datasense":
    MODELS = ["xgboost", "iforest", "raw_knn", "closr", "hc_closr"]
EXTRA = {"tabpfn": " eval_cap=5000"}    # TabPFN suy luận chậm nên đo trên ít mẫu hơn


def seeds(dataset, family=None):
    return (3, 4, 5) if dataset == "nf_cic" or family in ("mitm", "ransomware") else (2, 3, 4)


def lines(models):
    if os.environ.get("GRID") == "datasense":
        fams = os.environ.get("FAMS", ",".join(DATASENSE)).split(",")
        for s in map(int, os.environ.get("SEEDS", "0,1").split(",")):
            for m in models:
                for f in fams:
                    yield f"dataset=datasense protocol.heldout={f} model={m} seed={s}{EXTRA.get(m, '')}"
        return
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
