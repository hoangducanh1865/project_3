"""Kernel Kaggle (2×T4): các giao thức khó (P1T, P2, P3, PS, PF, PV), embedding số, TabPFN và đối chứng CLOSR + KNN.
Sửa PART rồi đẩy bằng: kaggle kernels push -p scripts/kaggle/hard
Lấy kết quả: kaggle kernels output <user>/project3-hard -p <thư mục> --file-pattern '.*(log|result[.]json)$'
"""
import glob
import os
import subprocess
import threading

COMMIT = "exp/hard-benchmarks"
PART = "key"   # smoke | screen | key | hc | uwf | floor | pe | pe_nn | nf | ablation
LYCOS18_ID = "12dQPcqRDJFeJGmqqshzdYN8M5t5tMXbQ"

HELD = ["slowloris", "ssh", "bot", "portscan"]
TACTIC = ["impact", "credential_access", "initial_access"]
P2 = ["protocol=p2", "dataset=lycos18 protocol=p2 protocol.target=lycos protocol.heldout=to17"]
P2_MODELS = ["xgboost", "mlp_knn", "closr_knn", "hc_closr"]
DROP = "'+protocol.drop_like=[hdr_len,tcp_init_win]'"
NF_HELD = ["ddos", "dos_attack", "xss", "injection", "password", "scanning", "backdoor"]
NF_DROP = "'protocol.drop_like=[TTL,TCP_WIN]'"
NF_P2 = ["dataset=nf_ton protocol=p2 protocol.target=nf_cic protocol.heldout=to_cic",
         "dataset=nf_cic protocol=p2 protocol.target=nf_ton protocol.heldout=to_ton"]


def hard(model, protos=("pv", "pf"), extra=""):
    """Mọi kịch bản khó trên dữ liệu 2017 cho một mô hình."""
    runs = [f"protocol=p3 model={model} {extra}"]
    runs += [f"protocol=p1t protocol.heldout={t} model={model} {extra}" for t in TACTIC]
    runs += [f"protocol={p} protocol.heldout={h} model={model} {extra}" for p in protos for h in HELD]
    return runs


def p1(model):
    """P0 và P1 (PV gồm cả P1) cho một mô hình."""
    return [f"protocol=p0 model={model}"] + [f"protocol=pv protocol.heldout={h} model={model}" for h in HELD]


def uwf(models):
    runs = [f"dataset=uwf protocol=p2 protocol.target=uwf25 protocol.heldout=to25"]
    runs += [f"dataset=uwf protocol=p1 protocol.heldout={t}" for t in ("t1018", "t1592", "t1595")]
    runs += [f"dataset=uwf protocol=p1t protocol.heldout={t}" for t in ("discovery", "reconnaissance")]
    return [f"{r} model={m}" for m in models for r in runs]


def nf(models, base=True, cross=True, pe=False):
    """NF-ToN-IoT-v3: mọi họ có từ 10.000 flow, chéo mạng với NF-CICIDS2018-v3, và bản bỏ TTL, cửa sổ TCP."""
    runs = [f"dataset=nf_ton protocol=p1 protocol.heldout={h}" for h in NF_HELD] if base else []
    runs += NF_P2 if cross else []
    runs += [f"dataset=nf_ton protocol=pe protocol.heldout={h} {NF_DROP}" for h in NF_HELD] if pe else []
    return [f"{r} model={m}" for m in models for r in runs]


FAST = {"xgboost": "model.n_estimators=5", "tabpfn": "model.max_train=300 model.n_estimators=1 eval_cap=500"}
TINY = "model.epochs=1 model.steps_per_epoch=5 eval_cap=2000"

# Mỗi luồng: (GPU, danh sách lần chạy). Cần P2 thì luồng đó tải LycoS-Unicas-IDS2018 trước.
PARTS = {
    "smoke": {
        "a": (0, [f"protocol=p3 model=xgboost {FAST['xgboost']}",
                  f"protocol=p1t protocol.heldout=impact model=mlp_ple_knn model.epochs=1 eval_cap=2000",
                  f"protocol=ps protocol.heldout=slowloris model=tabpfn {FAST['tabpfn']}",
                  f"protocol=ps protocol.heldout=slowloris model=hc_closr_ple {TINY}",
                  f"protocol=pf protocol.heldout=slowloris model=hc_closr_plr {TINY}"]),
        "b": (1, [f"protocol=pv protocol.heldout=slowloris model=closr_knn {TINY}",
                  f"protocol=pv protocol.heldout=slowloris model=hc_closr {TINY}",
                  f"protocol=pv protocol.heldout=slowloris model=xgboost {FAST['xgboost']}",
                  f"protocol=p3 model=closr {TINY}",
                  f"protocol=p1t protocol.heldout=initial_access model=hc_closr {TINY}"]),
        "p2": (0, [f"protocol=p2 model=xgboost {FAST['xgboost']}", f"{P2[0]} model=hc_closr {TINY}",
                   f"{P2[1]} model=xgboost {FAST['xgboost']}"]),
    },
    # Sàng lọc nhanh: XGBoost và MLP + KNN trên mọi kịch bản, TabPFN ở nơi có ít nhãn
    "screen": {
        "a": (0, hard("xgboost", ("pv", "pf", "ps")) + ["protocol=p3 model=tabpfn eval_cap=5000"]
              + [f"protocol=ps protocol.heldout={h} model=tabpfn eval_cap=5000" for h in HELD]),
        "b": (1, hard("mlp_knn", ("pv", "pf", "ps"))),
        "p2": (0, [f"{p} model={m}" for m in P2_MODELS[:2] for p in P2]),
    },
    # Hai kịch bản làm XGBoost tụt mạnh ở lượt sàng lọc: ít nhãn (PS) và chéo mạng (P2)
    "key": {
        "a": (0, [f"protocol=ps protocol.heldout={h} model={m}" for m in ("hc_closr", "closr_knn") for h in HELD]),
        "b": (1, [f"protocol=ps protocol.heldout={h} model={m}" for m in ("closr", "hc_closr_ple") for h in HELD]),
        "p2": (1, [f"{p} model={m}" for m in P2_MODELS[2:] + ["closr", "tabpfn eval_cap=5000"] for p in P2]),
    },
    # Mô hình đề xuất và CLOSR trên các kịch bản còn lại
    "hc": {
        "a": (0, hard("hc_closr")),
        "b": (1, hard("closr")),
        "uwf": (0, uwf(["hc_closr"])),
    },
    # UWF-ZeekData: giấu kỹ thuật, giấu chiến thuật, huấn luyện 2021-2024 và kiểm thử 2025
    "uwf": {
        "uwf": (0, uwf(["xgboost", "mlp_knn"])),
        "uwf2": (1, uwf(["closr_knn", "hc_closr"])),
    },
    # Mức sàn một đặc trưng cho mọi kịch bản, và XGBoost ở nơi đo được chiến thuật suy từ họ dự đoán. Chạy được trên CPU
    "floor": {
        "a": (0, ["protocol=p0 model=stump"] + hard("stump", ("p1", "ps", "pf"))
              + [f"protocol=p1 protocol.heldout={h} model=xgboost" for h in ("slowloris", "ssh")]),
        "p2": (0, [f"{p} model=stump" for p in P2]),
        "uwf": (0, uwf(["stump"]) + [f"dataset=uwf protocol=p1 protocol.heldout={t} model=xgboost" for t in ("t1018", "t1592", "t1595")]),
    },
    # PE: bỏ dấu vết ngăn xếp TCP (đặc trưng mạnh nhất khi dùng một mình), trên P1 và P2. Chạy được trên CPU
    "pe": {
        "a": (0, [f"protocol=pe protocol.heldout={h} model={m}" for m in ("stump", "xgboost") for h in HELD]),
        "p2": (0, [f"{p} {DROP} model={m}" for m in ("stump", "xgboost") for p in P2]),
    },
    "pe_nn": {
        "a": (0, [f"protocol=pe protocol.heldout={h} model={m}" for m in ("hc_closr", "closr_knn") for h in HELD]),
        "p2": (1, [f"{p} {DROP} model={m}" for m in ("hc_closr", "closr_knn", "mlp_knn") for p in P2]),
    },
    # NetFlow v3: benign và tấn công thu xen kẽ, XGBoost tụt mạnh ở lượt sàng lọc khi giấu một họ
    "nf": {
        "nf": (0, nf(["stump", "xgboost", "mlp_knn"], pe=True) + nf(["hc_closr"])),
        "nf2": (1, nf(["closr_knn", "closr"]) + nf(["hc_closr"], base=False, cross=False, pe=True)),
    },
    # Đối chứng không có đầu chiến thuật, và embedding số ở P0, P1
    "ablation": {
        "a": (0, p1("closr_knn") + p1("mlp_ple_knn")),
        "b": (1, p1("hc_closr_ple") + p1("hc_closr_plr")),
    },
}

W, T = "/kaggle/working", "/kaggle/temp"


def sh(cmd):
    print("$", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)


PREP = {"uwf": f"python -m src.uwf {T}/uwf", "nf": f"python -m src.netflow /kaggle/input {T}/nf"}
os.makedirs(T, exist_ok=True)
sh(f"git clone -q -b {COMMIT} https://github.com/hoangducanh1865/project_3 {T}/project_3")
os.chdir(f"{T}/project_3")
sh("pip install -q hydra-core tabulate gdown rtdl_num_embeddings tabpfn")
sh("git clone -q https://github.com/jackwilkie/CLOSR third_party/CLOSR")
csv = glob.glob("/kaggle/input/**/lycos.csv", recursive=True)[0]
csv18 = f"{T}/lycos18.csv"


ready = threading.Event()


def stream(name, gpu, runs):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), LYCOS_CSV=csv, LYCOS18_CSV=csv18,
               UWF_DIR=f"{T}/uwf", NF_DIR=f"{T}/nf", CACHE_DIR=f"{T}/cache_{name}", OUT_ROOT=f"{W}/out", CLOSR_DIR=f"{T}/project_3/third_party/CLOSR",
               HYDRA_FULL_ERROR="1")
    os.makedirs(env["CACHE_DIR"], exist_ok=True)
    with open(f"{W}/{name}.log", "w") as log:
        if name == "p2" and not os.path.exists(csv18):
            subprocess.run(f"gdown {LYCOS18_ID} -O {csv18} && head -c 1500 {csv18}", shell=True, stdout=log, stderr=log)
        if name in PREP:
            subprocess.run(PREP[name], shell=True, stdout=log, stderr=log)
            ready.set()
        elif name in ("uwf2", "nf2"):
            ready.wait()
        for r in runs:
            log.write(f"\n===== {r}\n"); log.flush()
            code = subprocess.run(f"python -m src.run {r}", shell=True, env=env, stdout=log, stderr=log).returncode
            log.write(f"===== mã thoát {code}: {r}\n"); log.flush()


threads = [threading.Thread(target=stream, args=(n, g, r)) for n, (g, r) in PARTS[PART].items()]
[t.start() for t in threads]
[t.join() for t in threads]
for n in PARTS[PART]:
    text = open(f"{W}/{n}.log").read()
    print(f"######## {n}\n", "\n".join(l for l in text.splitlines() if l.startswith("=====")), "\n", text[-1500:])
