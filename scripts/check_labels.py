"""Đối chiếu danh mục nhãn (conf/labels/datasense.yaml) với ATT&CK, D3FEND bản mới nhất và sinh tài liệu cho RAG.

Chạy định kỳ (mỗi khi ATT&CK ra phiên bản mới, khoảng 6 tháng một lần) để nhãn bám chuẩn hiện hành:
    python scripts/check_labels.py [--data datasense_flows.parquet] [--out knowledge/labels]
Kết quả:
    knowledge/labels/<họ>.md      mô tả nhãn, kỹ thuật ATT&CK, biện pháp D3FEND, số đo flow (tài liệu cho RAG)
    knowledge/labels/catalog.json danh mục cho web, kèm phiên bản ATT&CK và ngày kiểm tra
    knowledge/labels/report.md    chỗ lệch: kỹ thuật bị thu hồi, đổi tên, chiến thuật ATT&CK khác nhóm của mô hình
"""
import argparse
import json
import os
import time
import urllib.request

import yaml

ROOT = os.path.join(os.path.dirname(__file__), "..")
STIX = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
D3F = "https://d3fend.mitre.org/api/offensive-technique/attack/{}.json"
TACTIC_OF_GROUP = {"discovery": {"discovery", "reconnaissance"}, "credential_access": {"credential-access", "collection"},
                   "initial_access": {"initial-access"}, "impact": {"impact"}, "benign": set()}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "project3-label-check"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def attack_index():
    """{mã kỹ thuật: thông tin} và phiên bản ATT&CK từ bộ STIX chính thức."""
    bundle = get_json(STIX)
    version, idx = None, {}
    for o in bundle["objects"]:
        if o["type"] == "x-mitre-collection":
            version = o.get("x_mitre_version")
        if o["type"] != "attack-pattern":
            continue
        ref = next((r for r in o.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)
        if not ref:
            continue
        idx[ref["external_id"]] = {
            "name": o["name"], "url": ref.get("url"), "revoked": o.get("revoked", False),
            "deprecated": o.get("x_mitre_deprecated", False), "modified": o.get("modified", "")[:10],
            "tactics": sorted(p["phase_name"] for p in o.get("kill_chain_phases", [])),
        }
    return version, idx


def d3fend(tid):
    """{nhóm phòng thủ D3FEND: [(mã, tên)]} cho một kỹ thuật ATT&CK."""
    try:
        rows = get_json(D3F.format(tid))["off_to_def"]["results"]["bindings"]
    except Exception as e:  # mạng lỗi không làm hỏng cả lượt kiểm tra
        return {"_error": str(e)}
    out = {}
    for b in rows:
        if "def_tech_label" in b:
            out.setdefault(b["def_tactic_label"]["value"], set()).add((b["def_tech_id"]["value"], b["def_tech_label"]["value"]))
    return {k: sorted(v) for k, v in out.items()}


def flow_stats(path):
    """Số đo trung vị của từng họ trên dữ liệu đã gán nhãn lại."""
    import pandas as pd
    cols = ["label", "file", "dst_port", "protocol", "bidirectional_packets", "bidirectional_bytes", "bidirectional_duration_ms"]
    df = pd.read_parquet(path, columns=cols)
    out = {}
    for lab, g in df.groupby("label"):
        out[lab] = {"flows": int(len(g)), "files": int(g.file.nunique()),
                    "median_packets": float(g.bidirectional_packets.median()),
                    "median_bytes": float(g.bidirectional_bytes.median()),
                    "median_duration_ms": float(g.bidirectional_duration_ms.median()),
                    "top_dst_ports": [int(p) for p in g.dst_port.value_counts().index[:3]],
                    "protocols": {int(k): round(float(v), 3) for k, v in g.protocol.value_counts(normalize=True).items()}}
    return out


def markdown(fid, f, tech, d3, stats, version, today):
    lines = [f"# {f['name']} (`{fid}`)", "",
             f"Nhóm chiến thuật của mô hình: `{f['tactic']}`. Kiểm tra với ATT&CK v{version} ngày {today}.", "",
             "## Hành vi", f["behavior"], "", "## Cách gán nhãn", f["labeling"], "",
             "## Biến thể gốc trong bộ dữ liệu", ", ".join(f["variants"]), ""]
    if f.get("note"):
        lines += ["## Ghi chú", f["note"], ""]
    for t in f["techniques"]:
        x = tech.get(t)
        lines += [f"## ATT&CK {t}: {x['name'] if x else 'KHÔNG TÌM THẤY'}"]
        if x:
            lines += [f"Chiến thuật: {', '.join(x['tactics'])}. Cập nhật {x['modified']}. {x['url']}"]
        for grp, items in d3.get(t, {}).items():
            if grp != "_error":
                lines += [f"- D3FEND {grp}: " + "; ".join(f"{n} ({i})" for i, n in items)]
        lines += [""]
    if stats:
        s = stats
        lines += ["## Số đo trên dữ liệu (trung vị)",
                  f"{s['flows']} flow từ {s['files']} tệp PCAP; {s['median_packets']:g} gói, {s['median_bytes']:g} byte, "
                  f"{s['median_duration_ms']:g} ms mỗi flow; cổng đích hay gặp {s['top_dst_ports']}; giao thức {s['protocols']}.", ""]
    return "\n".join(lines)


def main(a):
    cat = yaml.safe_load(open(os.path.join(ROOT, "conf/labels/datasense.yaml")))
    version, tech = attack_index()
    today = time.strftime("%Y-%m-%d")
    stats = flow_stats(a.data) if a.data else {}
    os.makedirs(a.out, exist_ok=True)
    issues, catalog = [], {"attack_version": version, "checked": today, "dataset": cat["dataset"], "families": {}}
    for fid, f in cat["families"].items():
        d3 = {t: d3fend(t) for t in f["techniques"]}
        for t in f["techniques"]:
            x = tech.get(t)
            if x is None:
                issues.append(f"`{fid}`: không tìm thấy {t} trong ATT&CK v{version}")
                continue
            if x["revoked"] or x["deprecated"]:
                issues.append(f"`{fid}`: {t} đã bị {'thu hồi' if x['revoked'] else 'bỏ'} ở v{version}")
            if not set(x["tactics"]) & TACTIC_OF_GROUP.get(f["tactic"], set()):
                issues.append(f"`{fid}`: mô hình xếp nhóm `{f['tactic']}` nhưng {t} thuộc {', '.join(x['tactics'])}")
        with open(f"{a.out}/{fid}.md", "w") as fh:
            fh.write(markdown(fid, f, tech, d3, stats.get(fid), version, today))
        catalog["families"][fid] = {**f, "attack": [{"id": t, **(tech.get(t) or {})} for t in f["techniques"]],
                                    "d3fend": d3, "stats": stats.get(fid)}
    json.dump(catalog, open(f"{a.out}/catalog.json", "w"), ensure_ascii=False, indent=1)
    with open(f"{a.out}/report.md", "w") as fh:
        fh.write(f"# Kiểm tra danh mục nhãn với ATT&CK v{version} ({today})\n\n")
        fh.write("\n".join(f"- {i}" for i in issues) if issues else "Không có chỗ lệch.")
        fh.write("\n")
    print(f"ATT&CK v{version}, {len(issues)} chỗ lệch")
    print("\n".join(issues))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data")
    ap.add_argument("--out", default=os.path.join(ROOT, "knowledge/labels"))
    main(ap.parse_args())
