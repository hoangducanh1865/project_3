"""Gom cảnh báo từng flow thành sự cố cho luồng giả lập 24/7.

Mô hình báo nhầm khoảng 5% flow bình thường (ngưỡng phân vị 95), nên báo từng flow sẽ gây nhiễu. Sự cố chỉ mở khi một
cặp nguồn và đích có đủ nhiều cảnh báo và tỉ lệ cảnh báo cao hơn hẳn mức nhiễu đó trong WINDOW phút gần nhất.
Các ngưỡng dưới đây là quy tắc thiết kế, cần đối chiếu chuyên gia.
"""
import statistics
from collections import Counter

from .response import respond

WINDOW = 5          # phút
MIN_ALERTS = 5      # số cảnh báo tối thiểu trong cửa sổ
MIN_RATE = 0.3      # tỉ lệ cảnh báo tối thiểu trên số flow của cặp
CLOSE_AFTER = 10    # phút không còn cảnh báo thì đóng sự cố
KEEP_INCIDENTS, KEEP_SERIES, KEEP_CAMPAIGNS = 300, 1440, 200
NOTIFY_LEVELS = ("M3", "M4")    # chỉ báo ra ngoài web từ mức này


KEEP_EVIDENCE = 6   # số flow cảnh báo giữ lại làm bằng chứng cho mỗi sự cố
EV_KEYS = ("sport", "dport", "proto", "t0", "t1", "file", "feat", "top", "score")


def empty_pair():
    return {"flows": 0, "alerts": 0, "L": 0, "tier": {}, "tactic": {}, "family": {}, "truth": {}, "campaign": None,
            "ev": []}


def add(counter, key, n=1):
    counter[key] = counter.get(key, 0) + n


def pair_stats(flows, results):
    """Thống kê một phút theo từng cặp nguồn và đích."""
    pairs = {}
    for f, r in zip(flows, results):
        p = pairs.setdefault(f"{f['src']}>{f['dst']}", empty_pair())
        p["flows"] += 1
        if f["truth"]:
            add(p["truth"], f["truth"])
            p["campaign"] = f["campaign"]
        if r["status"] == "alert":
            p["alerts"] += 1
            p["L"] += r["L"]
            add(p["tier"], str(r["tier"]))
            add(p["tactic"], r["tactic"])
            add(p["family"], r["family"])
            if len(p["ev"]) < KEEP_EVIDENCE and "feat" in f:
                p["ev"].append({k: f[k] for k in EV_KEYS if k in f})
    return pairs


def merge(recent):
    total = {}
    for rec in recent:
        for key, p in rec["pairs"].items():
            t = total.setdefault(key, empty_pair())
            for k in ("flows", "alerts", "L"):
                t[k] += p[k]
            for k in ("tier", "tactic", "family", "truth"):
                for name, n in p[k].items():
                    add(t[k], name, n)
            t["campaign"] = p["campaign"] or t["campaign"]
            t["ev"] = (t["ev"] + p.get("ev", []))[-KEEP_EVIDENCE:]
    return total


def assess(p, impact):
    """Mức ứng phó của cả sự cố. L gồm điểm OOD và tần suất cảnh báo (slide tuần 2, mục 4.1)."""
    tier = int(max(p["tier"], key=lambda t: (p["tier"][t], -int(t))))
    tactics = {t: n for t, n in p["tactic"].items() if t != "unknown"} or {"unknown": 1}
    tactic = max(tactics, key=tactics.get)
    L = min(5, round(p["L"] / p["alerts"]) + (p["alerts"] >= 20) + (p["alerts"] >= 100))
    return respond(tier, tactic, L, impact)


def update_incidents(incidents, recent, tick_pairs, minute, impact):
    """Mở hoặc nâng mức sự cố, đóng sự cố đã im. Trả về danh sách sự cố mới mở."""
    opened = []
    for key, p in merge(recent).items():
        if p["alerts"] < MIN_ALERTS or p["alerts"] / p["flows"] < MIN_RATE:
            continue
        view = assess(p, impact)
        tick = tick_pairs.get(key, empty_pair())
        inc = next((i for i in incidents if i["key"] == key and i["status"] == "open"), None)
        if inc is None:
            src, dst = key.split(">")
            inc = {"id": f"{minute}-{len(incidents)}", "key": key, "src": src, "dst": dst, "opened": minute * 60,
                   "last": minute * 60, "flows": p["flows"], "alerts": p["alerts"], "status": "open", "truth": {},
                   "campaign": p["campaign"], **view}
            incidents.append(inc)
            opened.append(inc)
        else:
            inc["flows"] += tick["flows"]
            inc["alerts"] += tick["alerts"]
            if tick["alerts"]:
                inc["last"] = minute * 60
            if view["R"] > inc["R"]:    # chỉ nâng mức, không tự hạ khi sự cố còn mở
                inc.update(view)
        inc["family"] = max(p["family"], key=p["family"].get)
        if p["ev"]:
            inc["evidence"] = p["ev"]
            inc["files"] = sorted({e["file"] for e in p["ev"]} | set(inc.get("files", [])))[:5]
        inc["truth"] = {**inc["truth"], **p["truth"]}
        inc["campaign"] = p["campaign"] or inc["campaign"]
    for inc in incidents:
        if inc["status"] == "open" and minute * 60 - inc["last"] > CLOSE_AFTER * 60:
            inc["status"] = "closed"
    return opened


def to_notify(incidents):
    """Sự cố đang mở từ mức M3 chưa báo ra ngoài. Xét cả sự cố mở ở mức thấp rồi được nâng mức sau đó."""
    return [i for i in incidents if i["status"] == "open" and i["level"] in NOTIFY_LEVELS and not i.get("notified")]


def message(inc, tier_names, tactic_names, url):
    """Nội dung tin báo của một sự cố."""
    return (f"Phát hiện xâm nhập, mức {inc['level']} (dữ liệu mô phỏng)\n"
            f"{inc['src']} → {inc['dst']}\n"
            f"{tactic_names.get(inc['tactic'], inc['tactic'])}, tầng {inc['tier']}: {tier_names[inc['tier']]}\n"
            f"Đề xuất: {inc['action']}\n"
            f"Thực hiện: {inc['mode']}\n"
            f"{url}")


def summary(series, incidents, campaigns, minute):
    last_hour = series[-60:]
    day = [i for i in incidents if i["opened"] >= (minute - 1440) * 60]
    done = [c for c in campaigns if c.get("end")]
    found = [c for c in done if c.get("detected") is not None]
    return {
        "flows_60m": sum(s["flows"] for s in last_hour), "alerts_60m": sum(s["alerts"] for s in last_hour),
        "open": sum(i["status"] == "open" for i in incidents), "incidents_24h": len(day),
        "false_24h": sum(not i["truth"] for i in day), "campaigns_done": len(done), "campaigns_found": len(found),
        "ttd_median": statistics.median(c["detected"] - c["start"] for c in found) if found else None,
    }


def step(state, flows, results, minute, impact, ended):
    """Cập nhật trạng thái sau một phút. state: series, incidents, recent, campaigns."""
    pairs = pair_stats(flows, results)
    state["recent"] = [r for r in state["recent"] if r["m"] > minute - WINDOW] + [{"m": minute, "pairs": pairs}]
    alerts = sum(p["alerts"] for p in pairs.values())
    state["series"] = (state["series"] + [{"t": minute * 60, "flows": len(flows), "alerts": alerts}])[-KEEP_SERIES:]
    opened = update_incidents(state["incidents"], state["recent"], pairs, minute, impact)
    state["incidents"] = state["incidents"][-KEEP_INCIDENTS:]
    for inc in opened:
        c = next((c for c in state["campaigns"] if c["id"] == inc["campaign"]), None)
        if c and c.get("detected") is None:
            c["detected"] = minute
    if ended:
        c = next((c for c in state["campaigns"] if c["id"] == ended["id"]), None)
        if c:
            c["end"] = minute
    state["campaigns"] = state["campaigns"][-KEEP_CAMPAIGNS:]
    state["summary"] = summary(state["series"], state["incidents"], state["campaigns"], minute)
    state["updated"] = minute * 60
    return opened
