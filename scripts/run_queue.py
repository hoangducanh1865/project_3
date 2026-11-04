"""Chạy song song các lần chạy src.run trên một GPU lớn. Mỗi dòng của file là một bộ tham số Hydra.

Mỗi lần chạy có thư mục riêng theo mã băm của dòng, nên chạy lại file sẽ bỏ qua các lần đã có result.json.
Dùng: python scripts/run_queue.py <file> <số tiến trình> <thư mục kết quả>
"""
import hashlib
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

done = 0
lock = Lock()


def run(line, out, total):
    global done
    job = hashlib.sha1(line.encode()).hexdigest()[:12]
    path = f"{out}/jobs/{job}"
    os.makedirs(path, exist_ok=True)
    code, t0 = 0, time.time()
    if not os.path.exists(f"{path}/result.json"):
        env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
        with open(f"{path}/job.log", "w") as log:
            code = subprocess.run(f"python -m src.run {line} hydra.run.dir={path}", shell=True, env=env,
                                  stdout=log, stderr=log).returncode
    with lock:
        done += 1
        print(f"[{done}/{total}] mã {code} {time.time() - t0:.0f}s {line}", flush=True)


def main(file, workers, out):
    lines = [s.strip() for s in open(file) if s.strip() and not s.startswith("#")]
    with ThreadPoolExecutor(int(workers)) as pool:
        list(pool.map(lambda s: run(s, out, len(lines)), lines))


if __name__ == "__main__":
    main(*sys.argv[1:])
