# -*- coding: utf-8 -*-
"""Lấy mẫu nhỏ từ các bộ dataset NIDS mà không tải cả file.

Với mỗi file CSV: đọc dòng header + vài đoạn ngẫu nhiên (HTTP Range), bỏ dòng cắt dở,
rồi chọn ngẫu nhiên tối đa ROWS dòng. Với file zip (bản sửa lỗi CIC-IDS2017/2018):
đọc zip từ xa qua Range và lấy các dòng đầu của từng file CSV bên trong.

Chạy: python3 fetch_samples.py      (chỉ dùng thư viện chuẩn)
"""
import csv, io, os, random, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
HF = "https://huggingface.co/datasets/{repo}/resolve/main/{path}"
DISTRINET = "https://intrusion-detection.distrinet-research.be/CNS2022/Datasets/"
ROWS = 300          # số dòng mẫu tối đa mỗi file
CHUNKS = 6          # số đoạn ngẫu nhiên đọc từ mỗi file
CHUNK = 256 * 1024  # kích thước mỗi đoạn (byte)
random.seed(42)


def get(url, start=None, end=None):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    if start is not None:
        req.add_header("Range", f"bytes={start}-{end}")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def size_of(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers["Content-Length"])


def sample_csv(url, out_path, rows=ROWS):
    size = size_of(url)
    head = get(url, 0, min(size, CHUNK) - 1).decode("utf-8", "replace").splitlines()
    header, lines = head[0], head[1:-1]
    for _ in range(CHUNKS):
        if size <= CHUNK:
            break
        off = random.randint(0, size - CHUNK)
        part = get(url, off, off + CHUNK - 1).decode("utf-8", "replace").splitlines()
        lines += [l for l in part[1:-1] if l and l != header]
    ncol = len(next(csv.reader([header])))
    lines = [l for l in lines if len(next(csv.reader([l]))) == ncol]
    if "label" in [c.strip().lower() for c in next(csv.reader([header]))]:
        pick, _ = stratified(header, lines, total=rows)
    else:
        pick = random.sample(lines, min(rows, len(lines)))
    write(out_path, header, pick)
    return len(pick), size


class HttpFile(io.RawIOBase):
    """File-like đọc theo HTTP Range, cho zipfile đọc zip từ xa."""
    def __init__(self, url):
        self.url, self.pos, self.size = url, 0, size_of(url)
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos
    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        data = get(self.url, self.pos, self.pos + n - 1)
        self.pos += len(data)
        return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


def stratified(header, line_iter, per_label=60, benign_max=100, total=ROWS):
    """Lấy mẫu phân tầng theo nhãn (reservoir sampling cho từng nhãn)."""
    h = [c.strip().lower() for c in next(csv.reader([header]))]
    li = len(h) - 1 - h[::-1].index("label")
    pools, seen = {}, {}
    for line in line_iter:
        try:
            lab = next(csv.reader([line]))[li]
        except (StopIteration, IndexError):
            continue
        k = seen[lab] = seen.get(lab, 0) + 1
        pool = pools.setdefault(lab, [])
        if len(pool) < per_label:
            pool.append(line)
        else:
            j = random.randrange(k)
            if j < per_label:
                pool[j] = line
    out = []
    for lab, pool in pools.items():
        out += pool[:benign_max] if lab.lower() == "benign" else pool
    random.shuffle(out)
    return out[:total], seen


def sample_zip(url, out_dir, members=None, max_bytes=None):
    """Giải nén tuần tự từng file trong zip từ xa, lấy mẫu phân tầng theo nhãn.
    max_bytes: giới hạn số byte giải nén mỗi file (zip lớn)."""
    zf = zipfile.ZipFile(io.BufferedReader(HttpFile(url), buffer_size=8 * 1024 * 1024))
    res = []
    for info in zf.infolist():
        name = os.path.basename(info.filename)
        if not name.lower().endswith(".csv") or (members and name not in members):
            continue
        with zf.open(info) as raw:
            f = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
            header = f.readline().rstrip("\n")
            def lines():
                n = 0
                for l in f:
                    n += len(l)
                    if max_bytes and n > max_bytes:
                        return
                    yield l.rstrip("\n")
            pick, seen = stratified(header, lines())
        write(os.path.join(out_dir, "sample_" + name), header, pick)
        res.append((name, len(pick), info.file_size, seen))
    return res


def label_from_filename(path):
    """CICIoMT2024: cột Label trong mirror là 'NeedManualLabel'; nhãn thật nằm ở tên file."""
    lab = os.path.basename(path).replace("sample_", "").split("_train")[0]
    rows = list(csv.reader(open(path, encoding="utf-8")))
    li = [c.strip() for c in rows[0]].index("Label")
    for r in rows[1:]:
        r[li] = lab
    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)


def write(path, header, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        for l in lines:
            f.write(l + "\n")


SOURCES = {
    # thư mục: (repo HF, [file])
    "CIC-IDS2017_original": ("c01dsnap/CIC-IDS2017", [
        "Tuesday-WorkingHours.pcap_ISCX.csv",
        "Wednesday-workingHours.pcap_ISCX.csv",
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"]),
    "CSE-CIC-IDS2018_original": ("pcy12345BSU/CSE-CIC-IDS-2018", [
        "data/Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv",
        "data/Thursday-15-02-2018_TrafficForML_CICFlowMeter.csv",
        "data/Friday-16-02-2018_TrafficForML_CICFlowMeter.csv",
        "data/Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv",
        "data/Friday-02-03-2018_TrafficForML_CICFlowMeter.csv"]),
    "NF-ToN-IoT-v2": ("Nora9029/NF-ToN-IoT-v2", ["NF-ToN-IoT-v2-test.csv"]),
    "CIC-IoT2023": ("bencorn/CIC-IoT-2023", ["CSV/MERGED_CSV/Merged01.csv"]),
    "CICIoMT2024": ("somnath0100/CICIoMT2024Small", [
        "CSVS/Benign_train.pcap_Flow.csv",
        "CSVS/ARP_Spoofing_train.pcap_Flow.csv",
        "CSVS/MQTT-DDoS-Publish_Flood_train.pcap_Flow.csv",
        "CSVS/Recon-Port_Scan_train.pcap_Flow.csv",
        "CSVS/TCP_IP-DDoS-UDP1_train.pcap_Flow.csv"]),
}

ZIPS = {
    # (url, chỉ lấy các file này, giới hạn byte giải nén mỗi file)
    "CIC-IDS2017_improved": (DISTRINET + "CICIDS2017_improved.zip", None, None),
    "CSE-CIC-IDS2018_improved": (DISTRINET + "CSECICIDS2018_improved.zip",
                                 {"Wednesday-14-02-2018.csv", "Thursday-15-02-2018.csv", "Friday-16-02-2018.csv"},
                                 1500 * 1024 * 1024),
}

if __name__ == "__main__":
    only = set(sys.argv[1:])
    for folder, (repo, files) in SOURCES.items():
        if only and folder not in only:
            continue
        for p in files:
            url = HF.format(repo=repo, path=p)
            out = os.path.join(HERE, folder, "sample_" + os.path.basename(p))
            try:
                n, size = sample_csv(url, out)
                if folder == "CICIoMT2024":
                    label_from_filename(out)
                print(f"{folder}/{os.path.basename(p)}: {n} dòng (file gốc {size/1e6:.0f} MB)", flush=True)
            except Exception as e:
                print(f"LỖI {folder}/{p}: {e}", flush=True)
    for folder, (url, members, max_bytes) in ZIPS.items():
        if only and folder not in only:
            continue
        try:
            for name, n, fsize, seen in sample_zip(url, os.path.join(HERE, folder), members, max_bytes):
                print(f"{folder}/{name}: {n} dòng (file gốc {fsize/1e6:.0f} MB), nhãn đã gặp: {seen}", flush=True)
        except Exception as e:
            print(f"LỖI {folder}: {e}", flush=True)
