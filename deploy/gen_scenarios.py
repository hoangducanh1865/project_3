"""Soạn thư viện kịch bản tấn công bằng Gemini, chạy một lần trên máy (endpoint localhost, cloud không gọi được).

Gemini chỉ soạn trình tự tấn công. Đặc trưng flow lấy từ flow thật của LYCOS-IDS2017, xem src/simulator.py.
Chạy từ thư mục gốc repo: python deploy/gen_scenarios.py
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "http://localhost:20128/v1/chat/completions"
MODEL = "ag/gemini-3.8-flash-high"
FAMILIES = {
    "portscan": 150, "bot": 60, "ddos": 150, "dos_hulk": 150, "dos_goldeneye": 120, "dos_slowhttptest": 80,
    "dos_slowloris": 80, "ftp_patator": 120, "ssh_patator": 120, "webattack_bruteforce": 60, "webattack_xss": 40,
    "webattack_sql_injection": 4, "heartbleed": 4,
}   # họ tấn công -> số flow tối đa mỗi phút; hai họ cuối chỉ có 11-12 flow trong dữ liệu

PROMPT = f"""You are a network security analyst writing attack scenarios for a network intrusion detection simulator.
Write 16 varied, realistic multi-phase attack campaigns against a small enterprise network with a web server,
an FTP server, an SSH bastion and office workstations. Follow plausible attacker behaviour: reconnaissance first
when it makes sense, then credential attacks or web exploitation, then impact or command and control. Include some
short single-phase noisy attacks, some slow stealthy ones, and some long multi-stage intrusions.

Use only these attack families, with the maximum flows per minute in brackets:
{json.dumps(FAMILIES)}

Return only a JSON array. Each item must have:
- "id": short snake_case identifier
- "name": short Vietnamese name
- "narrative": one Vietnamese sentence describing the attacker's goal
- "phases": 1 to 6 items, each with "family", "minutes" (integer 1 to 15), "flows_per_min" (integer, 3 or more)
Total minutes per campaign must be at most 40."""


def validate(items):
    """Chỉ giữ kịch bản đúng khuôn. Gemini không được tự thêm họ tấn công hay vượt giới hạn."""
    good = []
    for it in items:
        phases = it.get("phases", [])
        ok = (isinstance(it.get("id"), str) and it.get("name") and it.get("narrative") and 1 <= len(phases) <= 6
              and sum(p.get("minutes", 99) for p in phases) <= 40)
        ok = ok and all(p.get("family") in FAMILIES and 1 <= p.get("minutes", 0) <= 15
                        and 1 <= p.get("flows_per_min", 0) <= FAMILIES[p["family"]] for p in phases)
        if ok:
            good.append({k: it[k] for k in ("id", "name", "narrative", "phases")})
        else:
            print("bỏ kịch bản không hợp lệ:", it.get("id"))
    return good


def reply_text(raw):
    """Endpoint có thể trả JSON thường hoặc luồng SSE (các dòng "data: ...")."""
    if not raw.lstrip().startswith("data:"):
        return json.loads(raw)["choices"][0]["message"]["content"]
    chunks = [json.loads(l[5:]) for l in raw.splitlines() if l.startswith("data:") and l[5:].strip() != "[DONE]"]
    return "".join(c["choices"][0]["delta"].get("content") or "" for c in chunks if c.get("choices"))


def main():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("\"'")
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": PROMPT}], "temperature": 0.8,
                       "stream": False}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, headers={
        "content-type": "application/json", "authorization": f"Bearer {env['GEMINI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        text = reply_text(r.read().decode())
    items = validate(json.loads(re.search(r"\[.*\]", text, re.S).group(0)))
    (ROOT / "deploy" / "scenarios.json").write_text(json.dumps(items, ensure_ascii=False, indent=1))
    print(f"đã lưu {len(items)} kịch bản")


if __name__ == "__main__":
    main()
