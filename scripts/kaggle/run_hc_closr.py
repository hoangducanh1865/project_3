"""Kernel Kaggle (2x T4): chạy HC-CLOSR, mỗi GPU một dãy lần chạy. Đẩy bằng: kaggle kernels push -p scripts/kaggle
Kết quả ở /kaggle/working/out, lấy về bằng: kaggle kernels output <user>/project3-hc-closr -p <thư mục>
"""
import glob
import os
import subprocess

COMMIT = "main"
JOBS = {0: ["protocol=p0", "protocol=p1 protocol.heldout=slowloris"],
        1: ["protocol=p1 protocol.heldout=ssh", "protocol=p1 protocol.heldout=bot"]}


def sh(cmd, **kw):
    print("$", cmd, flush=True)
    return subprocess.run(cmd, shell=True, check=True, **kw)


W = "/kaggle/working"
sh(f"git clone -q https://github.com/hoangducanh1865/project_3 {W}/project_3 && git -C {W}/project_3 checkout -q {COMMIT}")
os.chdir(f"{W}/project_3")
sh("pip install -q hydra-core tabulate")
sh("git clone -q https://github.com/jackwilkie/CLOSR third_party/CLOSR")
csv = glob.glob("/kaggle/input/**/lycos.csv", recursive=True)[0]
procs = []
for gpu, runs in JOBS.items():
    os.makedirs(f"{W}/cache{gpu}", exist_ok=True)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), LYCOS_CSV=csv, CACHE_DIR=f"{W}/cache{gpu}",
               OUT_ROOT=f"{W}/out", CLOSR_DIR=f"{W}/project_3/third_party/CLOSR")
    cmd = " && ".join(f"python -m src.run {r} model=hc_closr" for r in runs)
    procs.append(subprocess.Popen(cmd, shell=True, env=env, stdout=open(f"{W}/gpu{gpu}.log", "w"),
                                  stderr=subprocess.STDOUT))
codes = [p.wait() for p in procs]
sh(f"rm -rf {W}/cache* {W}/project_3")
for gpu in JOBS:
    print(open(f"{W}/gpu{gpu}.log").read()[-3000:])
print("mã thoát:", codes)
