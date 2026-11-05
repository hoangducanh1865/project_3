"""Trung tâm giám sát của demo khép kín: phát hiện tại cổng, Telegram, quyết định có thời hạn, chặn tại cổng.

Mọi truy cập vào web đi qua cổng 8080. Tầng phát hiện của demo là luật theo hành vi, không phải HC-CLOSR: mô hình học từ
testbed cho điểm gần như nhau giữa lưu lượng localhost bình thường và tấn công, cần dữ liệu của mạng đích mới dùng được.
Chiến thuật, rủi ro và biện pháp D3FEND dùng src/response.py của đề tài. Hành động luôn nằm trong ACTIONS và có thời hạn.
"""
import collections
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from src.response import respond  # noqa: E402


def load_env():
    env = dict(os.environ)
    path = os.path.join(HERE, "..", ".env")
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r"\s*([A-Z0-9_]+)=(.*)", line)
            if m:
                env.setdefault(m[1], m[2].strip().strip('"\''))
    return env


ENV = load_env()
TARGET = ("127.0.0.1", int(ENV.get("TARGET_PORT", 5001)))
GATE_PORT, DASH_PORT = int(ENV.get("GATE_PORT", 8080)), int(ENV.get("DASH_PORT", 9000))
DECOYS = [2222, 2323, 3306, 3389, 5432, 5900, 6379, 8888]     # cổng mồi: không có dịch vụ thật, ai chạm vào là đang dò quét
TIMEOUT = int(ENV.get("DECISION_TIMEOUT", 180))               # giây chờ quản trị viên trước khi Gemini quyết định
LLM_URL = ENV.get("LLM_URL", "http://localhost:20128/v1/chat/completions")
LLM_MODEL = ENV.get("LLM_MODEL", "ag/gemini-3.8-flash-high")
BOT, CHAT = ENV.get("TELEGRAM_BOT_TOKEN", ""), ENV.get("TELEGRAM_CHAT_ID", "")
IMPACT = {"impact": 4, "credential_access": 4, "initial_access": 5, "command_and_control": 5, "discovery": 2, "unknown": 4}
ACTIONS = {"block": ("Chặn nguồn 10 phút", 600), "limit": ("Giới hạn 2 kết nối mỗi giây trong 10 phút", 600),
           "ignore": ("Bỏ qua, chỉ theo dõi", 0)}
# hành vi: (tên, chiến thuật, ngưỡng trong 10 giây, L)
RULES = {"scan": ("Quét cổng", "discovery", 4, 4), "login": ("Dò mật khẩu", "credential_access", 15, 4),
         "request": ("Làm ngập HTTP", "impact", 150, 4), "held": ("Giữ kết nối kiểu Slowloris", "impact", 40, 4)}
TACTIC = {"impact": "Impact", "credential_access": "Credential Access", "discovery": "Discovery"}

lock = threading.RLock()
incidents, log = [], collections.deque(maxlen=40)
blocked, limited, conn_times = {}, {}, collections.defaultdict(collections.deque)
events = collections.defaultdict(lambda: collections.defaultdict(collections.deque))
open_conns = collections.Counter()
stats = {"requests": 0, "refused": 0, "started": time.time()}
series = collections.deque(maxlen=120)


def note(text):
    with lock:
        log.appendleft({"t": time.strftime("%H:%M:%S"), "text": text})
    print(time.strftime("%H:%M:%S"), text, flush=True)


def hit(src, kind):
    with lock:
        events[src][kind].append(time.time())


def refused(ip):
    now = time.time()
    with lock:
        if blocked.get(ip, 0) > now:
            return True
        if limited.get(ip, 0) > now:
            q = conn_times[ip]
            q.append(now)
            while q and now - q[0] > 1:
                q.popleft()
            return len(q) > 2
    return False


# ---------------------------------------------------------------- Cổng vào web
def relay_up(c, up, ip):
    first = True
    try:
        while True:
            data = c.recv(65536)
            if not data:
                break
            if first:
                first = False
                stats["requests"] += 1
                hit(ip, "request")
                if data.startswith(b"POST /auth/login"):
                    hit(ip, "login")
            up.sendall(data)
    except OSError:
        pass
    finally:
        with lock:
            open_conns[ip] -= 1
        for s in (c, up):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def relay_down(up, c):
    try:
        while True:
            data = up.recv(65536)
            if not data:
                break
            c.sendall(data)
    except OSError:
        pass
    for s in (c, up):
        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def gateway():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", GATE_PORT))
    srv.listen(512)
    while True:
        c, addr = srv.accept()
        ip = addr[0]
        if refused(ip):
            stats["refused"] += 1
            c.close()
            continue
        try:
            up = socket.create_connection(TARGET, timeout=5)
        except OSError:
            c.close()
            continue
        with lock:
            open_conns[ip] += 1
        threading.Thread(target=relay_up, args=(c, up, ip), daemon=True).start()
        threading.Thread(target=relay_down, args=(up, c), daemon=True).start()


def decoy(port):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("0.0.0.0", port))
    except OSError:
        return
    srv.listen(64)
    while True:
        c, addr = srv.accept()
        hit(addr[0], "scan")
        c.close()


# ---------------------------------------------------------------- Phát hiện
def detector():
    while True:
        time.sleep(1)
        now = time.time()
        with lock:
            series.append({"t": time.strftime("%H:%M:%S"), "req": sum(1 for s in events.values() for x in s["request"] if now - x < 1)})
            for src, kinds in list(events.items()):
                for q in kinds.values():
                    while q and now - q[0] > 10:
                        q.popleft()
                counts = {k: len(kinds[k]) for k in ("scan", "login", "request")}
                counts["held"] = open_conns[src]
                for kind, (name, tactic, limit, L) in RULES.items():
                    if counts[kind] >= limit:
                        open_incident(src, name, tactic, L, counts[kind])


def open_incident(src, name, tactic, L, count):
    now = time.time()
    if blocked.get(src, 0) > now or limited.get(src, 0) > now:
        return
    if any(i["src"] == src and i["name"] == name and (i["status"] == "chờ quyết định" or now - i["opened"] < 30) for i in incidents):
        return
    r = respond(1, tactic, L, IMPACT)
    inc = {"id": f"S{len(incidents) + 1:03d}", "src": src, "name": name, "tactic": tactic, "count": count, "opened": now,
           "time": time.strftime("%H:%M:%S"), "L": r["L"], "I": r["I"], "R": r["R"], "level": r["level"], "suggest": r["action"],
           "d3fend": r["d3fend_now"], "status": "chờ quyết định", "decision": None, "by": None, "reason": None}
    incidents.append(inc)
    note(f"{inc['id']}: {name} từ {src}, {count} sự kiện trong 10 giây, mức {inc['level']}")
    threading.Thread(target=alert_admin, args=(inc,), daemon=True).start()


# ---------------------------------------------------------------- Quyết định
def decide(inc, action, by, reason=""):
    with lock:
        if inc["status"] != "chờ quyết định" or action not in ACTIONS:
            return False
        inc.update(status="đã xử lý", decision=action, by=by, reason=reason)
        until = time.time() + ACTIONS[action][1]
        if action == "block":
            blocked[inc["src"]] = until
        elif action == "limit":
            limited[inc["src"]] = until
    note(f"{inc['id']}: {ACTIONS[action][0]} ({by})")
    send(f"✅ {inc['id']}: {ACTIONS[action][0]}\nQuyết định bởi: {by}" + (f"\nLý do: {reason}" if reason else ""))
    return True


def ask_gemini(inc):
    prompt = ("Bạn là trợ lý trực ban an ninh mạng. Quản trị viên chưa phản hồi. Chọn một hành động cho sự cố sau. "
              'Chỉ trả về JSON dạng {"action": "block|limit|ignore", "reason": "một câu tiếng Việt"}.\n'
              + json.dumps({k: inc[k] for k in ("src", "name", "tactic", "count", "level", "R", "suggest", "d3fend")}, ensure_ascii=False))
    body = json.dumps({"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "stream": False}).encode()
    req = urllib.request.Request(LLM_URL, body, {"Content-Type": "application/json", "Authorization": f"Bearer {ENV.get('GEMINI_API_KEY', '')}"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    if raw.lstrip().startswith("data:"):        # proxy có thể trả về dạng luồng
        text = "".join(json.loads(x[5:])["choices"][0]["delta"].get("content") or "" for x in raw.splitlines()
                       if x.startswith("data:") and "[DONE]" not in x and json.loads(x[5:]).get("choices"))
    else:
        text = json.loads(raw)["choices"][0]["message"]["content"]
    out = json.loads(re.search(r"\{.*\}", text, re.S)[0])
    return out["action"], str(out.get("reason", ""))[:200]


def alert_admin(inc):
    text = (f"🚨 Sự cố {inc['id']} - mức {inc['level']}\nHành vi: {inc['name']}\nNguồn: {inc['src']}\n"
            f"Chiến thuật: {TACTIC.get(inc['tactic'], inc['tactic'])}\nRủi ro R = {inc['L']} × {inc['I']} = {inc['R']}\n"
            f"Đề xuất: {inc['suggest']}\nD3FEND: {', '.join(inc['d3fend'])}\n\nSau {TIMEOUT} giây không phản hồi, Gemini sẽ quyết định.")
    send(text, {"inline_keyboard": [[{"text": ACTIONS[a][0], "callback_data": f"{a}:{inc['id']}"}] for a in ACTIONS]})
    while time.time() < inc["opened"] + TIMEOUT:
        if inc["status"] != "chờ quyết định":
            return
        time.sleep(1)
    try:
        action, reason = ask_gemini(inc)
        if action not in ACTIONS:
            raise ValueError(action)
        decide(inc, action, "Gemini, quản trị viên không phản hồi", reason)
    except Exception as e:      # không gọi được Gemini: dùng phương án nhẹ, có thời hạn
        decide(inc, "limit", "quy tắc dự phòng", f"không gọi được Gemini: {e}")


def telegram(method, params):
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT}/{method}", json.dumps(params).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=40))


def send(text, keyboard=None):
    if not BOT:
        return
    try:
        telegram("sendMessage", {"chat_id": CHAT, "text": text, **({"reply_markup": keyboard} if keyboard else {})})
    except Exception as e:
        note(f"không gửi được Telegram: {e}")


def telegram_poll():
    offset = 0
    while BOT:
        try:
            for u in telegram("getUpdates", {"timeout": 25, "offset": offset, "allowed_updates": ["callback_query"]}).get("result", []):
                offset = u["update_id"] + 1
                q = u.get("callback_query")
                if not q or str(q["message"]["chat"]["id"]) != str(CHAT):
                    continue
                action, iid = q["data"].split(":")
                inc = next((i for i in incidents if i["id"] == iid), None)
                ok = bool(inc) and decide(inc, action, "quản trị viên qua Telegram")
                telegram("answerCallbackQuery", {"callback_query_id": q["id"], "text": "Đã ghi nhận" if ok else "Sự cố đã được xử lý"})
        except Exception:
            time.sleep(3)


# ---------------------------------------------------------------- Bảng điều khiển
class Dash(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, body, kind="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            now = time.time()
            with lock:
                inc = [{**i, "left": max(0, int(i["opened"] + TIMEOUT - now))} for i in incidents[::-1]]
                state = {"stats": stats, "incidents": inc, "log": list(log), "series": list(series)[-60:], "timeout": TIMEOUT,
                         "blocked": {k: int(v - now) for k, v in blocked.items() if v > now},
                         "limited": {k: int(v - now) for k, v in limited.items() if v > now},
                         "actions": {k: v[0] for k, v in ACTIONS.items()}, "tactics": TACTIC}
            self.reply(json.dumps(state, ensure_ascii=False).encode())
        else:
            self.reply(open(os.path.join(HERE, "dashboard.html"), "rb").read(), "text/html")

    def do_POST(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if self.path.startswith("/api/decide"):
            inc = next((i for i in incidents if i["id"] == q["id"][0]), None)
            ok = bool(inc) and decide(inc, q["action"][0], "quản trị viên qua web")
        else:                       # /api/release: gỡ chặn để demo lại
            with lock:
                blocked.pop(q["src"][0], None)
                limited.pop(q["src"][0], None)
                events.pop(q["src"][0], None)
            note(f"gỡ chặn {q['src'][0]}")
            ok = True
        self.reply(json.dumps({"ok": ok}).encode())


if __name__ == "__main__":
    for fn in (gateway, detector, telegram_poll):
        threading.Thread(target=fn, daemon=True).start()
    for p in DECOYS:
        threading.Thread(target=decoy, args=(p,), daemon=True).start()
    note(f"web qua cổng :{GATE_PORT}, bảng điều khiển http://localhost:{DASH_PORT}, chờ quyết định {TIMEOUT} giây")
    ThreadingHTTPServer(("127.0.0.1", DASH_PORT), Dash).serve_forever()
