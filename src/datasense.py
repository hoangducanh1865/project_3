"""DataSense (CIC IIoT 2025): tải PCAP gốc, tự trích flow bằng NFStream và gán nhãn lại theo từng flow.

Bản gốc gán nhãn theo cả tệp PCAP (tên tệp là tên tấn công), nên lưu lượng bình thường của cảm biến trong lúc bị
tấn công cũng mang nhãn tấn công. Ở đây mỗi flow được gán nhãn theo ba nguồn sự thật công bố kèm bộ dữ liệu:
`devices.csv` (IP, MAC, vai trò của 45 thiết bị, gồm 6 máy tấn công) và `attacks.csv` (thời điểm bắt đầu, kết thúc
và mục tiêu của từng lần tấn công). Quy tắc nằm ở `label_flows`, mỗi flow ghi lại quy tắc đã dùng ở cột `rule`.

Chạy trên Colab (cần mạng, khoảng 100 GB đĩa tạm):
    python -m src.datasense --out $DATA/datasense --cats bruteforce web recon mitm malware benign dos ddos
Cần biến CIC_FORM (JSON các trường của form tải trên cicresearch.ca), đặt trong /root/.secrets, không đưa vào repo.
"""
import argparse
import io
import json
import os
import subprocess
import tarfile
import tempfile
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

import numpy as np
import pandas as pd

BASE = "https://cicresearch.ca/IOTDataset/Datasense"
CATS = ["bruteforce", "web", "recon", "mitm", "malware", "dos", "ddos", "benign"]
SLACK_MS = 2000            # dung sai đồng hồ khi so thời điểm flow với cửa sổ tấn công
MAX_PACKETS = 3_000_000    # tệp ngập lụt có tới 8 triệu gói trong 60 giây: chỉ đọc phần đầu
CAP_ATTACK, CAP_BENIGN = 3000, 1500   # số flow giữ lại mỗi tệp tấn công, lấy ngẫu nhiên

# Họ tấn công: gom các biến thể cùng cơ chế (khác cổng, DoS hay DDoS) thành một họ. Thứ tự quan trọng: khớp mục đầu.
FAMILIES = [
    ("synonymousip-flood", "land_flood"), ("syn-flood", "syn_flood"),
    ("mirai", "mirai"), ("http-flood", "http_flood"), ("mqtt-publish-flood", "mqtt_flood"),
    ("slowloris", "slowloris"), ("udp", "udp_flood"), ("icmp", "icmp_flood"),
    ("ack-frag", "tcp_flood"), ("push-ack", "tcp_flood"), ("rst-fin", "tcp_flood"), ("tcp-flood", "tcp_flood"),
    ("connect-flood", "tcp_flood"),
    ("host-disc-arp-ping", None),   # chỉ có gói ARP, không tạo flow IP nên bỏ
    ("host-disc", "host_discovery"), ("ping-sweep", "host_discovery"),
    ("port-scan", "port_scan"), ("os-scan", "os_scan"), ("vuln-scan", "vuln_scan"),
    ("dictionary-ssh", "ssh_bruteforce"), ("dictionary-telnet", "telnet_bruteforce"),
    ("arp-spoofing", "arp_spoofing"), ("impersonation", "impersonation"), ("ip-spoofing", "ip_spoofing"),
    ("sql-injection", "web_attack"), ("xss", "web_attack"), ("command-injection", "web_attack"),
    ("backdoor-upload", "web_attack"),
]
SPOOFED = ("land_flood", "ip_spoofing")       # IP nguồn bị giả: nhận theo đích là mục tiêu
WIDE = ("host_discovery", "port_scan", "os_scan", "vuln_scan", "mirai")   # quét hoặc lây lan ra nhiều máy
ID_COLS = ["src_ip", "dst_ip", "src_mac", "dst_mac", "src_port", "dst_port", "protocol",
           "bidirectional_first_seen_ms", "bidirectional_last_seen_ms"]


def family_of(attack_name):
    for key, fam in FAMILIES:
        if key in attack_name:
            return fam
    raise ValueError(f"chưa xếp họ cho {attack_name}")


class Session:
    """Tải bằng curl với cookie của form CIC (biến CIC_FORM). Thư viện requests bị server ngắt kết nối giữa chừng."""

    def __init__(self, jar):
        self.jar = jar
        subprocess.run(["curl", "-s", "-c", jar, "-b", jar, f"{BASE}/", "-o", os.devnull], check=True)
        form = sum((["-F", f"{k}={v}"] for k, v in json.loads(os.environ["CIC_FORM"]).items()), [])
        r = json.loads(subprocess.run(["curl", "-s", "-c", jar, "-b", jar, "-X", "POST", f"{BASE}/insert.php", *form],
                                      check=True, capture_output=True).stdout)
        if not r.get("ok"):
            raise RuntimeError(r)

    def url(self, path):
        return f"{BASE}/download.php?file=" + path.replace("/", "%2F")

    def get(self, path):
        return subprocess.run(["curl", "-s", "-b", self.jar, self.url(path)], check=True, capture_output=True).stdout

    def stream(self, path):
        return subprocess.Popen(["curl", "-s", "-b", self.jar, self.url(path)], stdout=subprocess.PIPE)


def inventory(sess):
    """devices.csv và attacks.csv trong thư mục docs chính thức của bộ dữ liệu."""
    get = lambda name: pd.read_csv(io.BytesIO(sess.get(f"docs/site/{name}")))
    devices, attacks = get("devices.csv"), get("attacks.csv")
    devices["mac"] = devices["mac"].str.lower()
    # Một tệp có thể có nhiều dòng (mỗi máy tấn công một dòng): gộp thành cửa sổ rộng nhất.
    attacks = (attacks.groupby("filename", as_index=False)
               .agg(category=("category", "first"), attack_name=("attack_name", "first"),
                    attack_target=("attack_target", "first"), start_timestamp=("start_timestamp", "min"),
                    end_timestamp=("end_timestamp", "max"), doc_count=("doc_count", "sum")))
    return devices, attacks


def extract(pcap):
    """Flow hai chiều từ một PCAP. Trả về DataFrame gồm cột định danh (ID_COLS) và đặc trưng thống kê."""
    from nfstream import NFStreamer
    cut = pcap + ".head.pcap"
    subprocess.run(["tcpdump", "-r", pcap, "-w", cut, "-c", str(MAX_PACKETS)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    df = NFStreamer(source=cut, statistical_analysis=True, splt_analysis=0, n_dissections=0,
                    idle_timeout=120, active_timeout=1800, accounting_mode=1, n_meters=1).to_pandas()
    os.remove(cut)
    return df


def label_flows(df, meta, devices):
    """Gán nhãn từng flow của một tệp. meta là dòng của attacks.csv. Trả về (nhãn, quy tắc); nhãn None là bỏ.

    - Tệp benign: flow không chạm máy tấn công là benign; chạm máy tấn công là bỏ (không rõ).
    - Tệp tấn công, flow chạm IP hoặc MAC máy tấn công trong cửa sổ [start, end]: là họ tấn công, nếu đầu còn lại là
      mục tiêu hoặc họ thuộc loại quét rộng (WIDE). Chạm máy tấn công mà ngoài cửa sổ hoặc tới máy khác: bỏ.
    - Họ giả IP nguồn (SPOOFED): flow tới mục tiêu trong cửa sổ có IP nguồn không thuộc thiết bị đã biết, hoặc
      IP nguồn trùng IP đích, là tấn công.
    - Còn lại là benign: lưu lượng nền của các thiết bị trong lúc tấn công diễn ra.
    """
    att = devices[devices.role == "attacker"]
    a_ip, a_mac = set(att.ip), set(att.mac)
    known = set(devices.ip)
    touch = (df.src_ip.isin(a_ip) | df.dst_ip.isin(a_ip)
             | df.src_mac.str.lower().isin(a_mac) | df.dst_mac.str.lower().isin(a_mac)).to_numpy()
    if meta.category == "benign":
        return np.where(touch, None, "benign"), np.where(touch, "benign_file_touch_attacker", "benign_file")
    fam = family_of(meta.attack_name)
    t0, t1 = meta.start_timestamp - SLACK_MS, meta.end_timestamp + SLACK_MS
    inwin = ((df.bidirectional_last_seen_ms >= t0) & (df.bidirectional_first_seen_ms <= t1)).to_numpy()
    tgt = set(devices.loc[devices.device_name.isin(meta.attack_target.split("--")), "ip"])   # có thể hai mục tiêu
    peer_is_target = (df.src_ip.isin(tgt) | df.dst_ip.isin(tgt)).to_numpy()
    on_target = peer_is_target | (fam in WIDE) | (not tgt)
    label = np.full(len(df), "benign", dtype=object)
    rule = np.full(len(df), "background", dtype=object)
    hit = touch & inwin & on_target
    label[hit], rule[hit] = fam, "attacker_in_window"
    odd = touch & ~hit
    label[odd], rule[odd] = None, "attacker_outside_window_or_target"
    if fam in SPOOFED:
        spoof = inwin & df.dst_ip.isin(tgt).to_numpy() & (~df.src_ip.isin(known) | (df.src_ip == df.dst_ip)).to_numpy()
        label[spoof & ~touch], rule[spoof & ~touch] = fam, "spoofed_source_to_target"
    return label, rule


def process(job):
    pcap, meta, devices, seed = job
    df = extract(pcap)
    os.remove(pcap)
    if df.empty:
        return None
    label, rule = label_flows(df, meta, devices)
    df["label"], df["rule"] = label, rule
    df["file"], df["cic_label"] = meta.filename, meta.attack_name
    df["category"] = meta.category
    rng = np.random.default_rng(seed)
    parts = []
    for lab, g in df.groupby("label", dropna=False):
        cap = CAP_BENIGN if lab == "benign" and meta.category != "benign" else CAP_ATTACK
        if meta.category == "benign":
            cap = len(g)
        parts.append(g.iloc[rng.permutation(len(g))[:cap]])
    counts = df.groupby(["label", "rule"], dropna=False).size().rename("n").reset_index()
    counts["file"] = meta.filename
    return pd.concat(parts), counts


def members(sess, cat, minutes):
    """Lần lượt từng PCAP trong tệp nén của một nhóm, đọc thẳng từ mạng, không lưu tệp nén. Dừng sau `minutes` phút."""
    sub = "benign_data/benign" if cat == "benign" else f"attack_data/{cat}"
    proc = sess.stream(f"dataset/raw_files/{sub}.tar.xz")
    t_end = time.time() + 60 * minutes
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|xz") as tar:
            for m in tar:
                if m.isfile() and m.name.endswith(".pcap"):
                    yield os.path.basename(m.name)[:-5], tar.extractfile(m)
                    if time.time() > t_end:
                        print(cat, "hết thời gian, dừng đọc", flush=True)
                        return
    finally:
        proc.kill()


def run(out, cats, workers, minutes):
    os.makedirs(out, exist_ok=True)
    sess = Session(f"{out}/.cookies_{'_'.join(cats)}")   # server chỉ cho mỗi phiên tải một tệp một lúc
    devices, attacks = inventory(sess)
    devices.to_csv(f"{out}/devices.csv", index=False)
    attacks.to_csv(f"{out}/attacks.csv", index=False)
    meta = attacks.set_index("filename", drop=False)
    tmp = tempfile.mkdtemp(dir=os.environ.get("TMP_PCAP", "/content"))
    for cat in cats:
        if os.path.exists(f"{out}/flows_{cat}.parquet"):
            continue
        flows, counts, futs = [], [], set()
        with ProcessPoolExecutor(workers) as pool:
            for i, (name, fh) in enumerate(members(sess, cat, minutes)):
                if name not in meta.index:
                    print("không có trong attacks.csv:", name, flush=True)
                    continue
                path = f"{tmp}/{name}.pcap"
                with open(path, "wb") as f:
                    while chunk := fh.read(1 << 24):
                        f.write(chunk)
                futs.add(pool.submit(process, (path, meta.loc[name], devices, i)))
                if len(futs) >= 2 * workers:   # giới hạn số PCAP chờ trên đĩa
                    done, futs = wait(futs, return_when=FIRST_COMPLETED)
                    for f in done:
                        _collect(f, flows, counts)
            for f in futs:
                _collect(f, flows, counts)
        pd.concat(flows).to_parquet(f"{out}/flows_{cat}.parquet", index=False)
        pd.concat(counts).to_csv(f"{out}/relabel_{cat}.csv", index=False)
        print(cat, "xong", sum(len(f) for f in flows), "flow", flush=True)


def _collect(fut, flows, counts):
    try:
        res = fut.result()
    except Exception as e:  # một tệp hỏng không làm dừng cả nhóm
        print("lỗi:", e, flush=True)
        return
    if res is not None:
        flows.append(res[0])
        counts.append(res[1])


def build(out, benign_frac=1.0):
    """Gộp các nhóm thành một bảng huấn luyện: bỏ flow không rõ nhãn, giữ cột định danh để web truy nguồn."""
    parts = [pd.read_parquet(f"{out}/{f}") for f in sorted(os.listdir(out)) if f.startswith("flows_")]
    df = pd.concat(parts, ignore_index=True)
    df = df[df.label.notna()]
    df.to_parquet(f"{out}/datasense_flows.parquet", index=False)
    rel = pd.concat([pd.read_csv(f"{out}/{f}") for f in os.listdir(out) if f.startswith("relabel_")])
    rel.to_csv(f"{out}/relabel_all.csv", index=False)
    print(df.label.value_counts().to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cats", nargs="+", default=CATS)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--minutes", type=float, default=1e9, help="thời gian đọc tối đa mỗi nhóm")
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    if a.build:
        build(a.out)
    else:
        run(a.out, a.cats, a.workers, a.minutes)
