"""RAG cho trợ lý AI: với mỗi họ, truy xuất tài liệu nhãn (knowledge/labels) rồi cho LLM viết nhận định và đề xuất.

Ràng buộc (conf/policy.yaml): AI chỉ đề xuất; mỗi ý phải dẫn mã tài liệu hoặc mã D3FEND có trong ngữ cảnh đã truy xuất.
Kết quả được kiểm tra lại: trích dẫn không có trong ngữ cảnh và biện pháp không có trong tài liệu bị loại.
Chạy trên máy có proxy LLM (mặc định localhost:20128, khoá GEMINI_API_KEY):
    python scripts/ai_notes.py --out knowledge/ai_notes.json
"""
import argparse
import json
import os
import re
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
LLM_URL = os.environ.get("LLM_URL", "http://localhost:20128/v1/chat/completions")
MODEL = os.environ.get("LLM_MODEL", "ag/gemini-3.8-flash-high")
PROMPT = """Bạn là trợ lý phân tích cho trung tâm giám sát an ninh mạng IIoT. Bạn KHÔNG được thực hiện hành động; bạn chỉ đề xuất.
Mô hình phát hiện báo một nhóm flow có hành vi gần với họ "{name}" ({fid}). Chỉ dựa vào TÀI LIỆU dưới đây, trả về JSON:
{{"summary": "2 câu: hành vi này là gì và dấu hiệu trên flow", "check": ["2 việc chuyên viên nên kiểm tra để xác nhận"],
"recommend": [{{"d3fend": "mã D3-... có trong tài liệu", "why": "1 câu"}}] (tối đa 3, ưu tiên Isolate và Detect),
"cites": ["mã tài liệu đã dùng, ví dụ label:{fid}"]}}
Viết tiếng Việt, ngắn gọn, không bịa mã không có trong tài liệu. Chỉ in JSON.

TÀI LIỆU:
{docs}"""


def retrieve(fid, catalog, docs_dir):
    """Tài liệu của chính họ đó cộng các họ cùng nhóm chiến thuật có chung kỹ thuật ATT&CK (tối đa 2)."""
    fam = catalog["families"][fid]
    same = [k for k, v in catalog["families"].items() if k != fid and v["tactic"] == fam["tactic"]
            and set(v["techniques"]) & set(fam["techniques"])][:2]
    return {f"label:{k}": open(os.path.join(docs_dir, f"{k}.md"), encoding="utf-8").read() for k in [fid] + same}


def ask(text):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": text}], "temperature": 0.2, "stream": False}).encode()
    req = urllib.request.Request(LLM_URL, body, {"content-type": "application/json",
                                                 "authorization": f"Bearer {os.environ.get('GEMINI_API_KEY', '')}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", out, re.S).group(0))


def guard(note, ctx):
    """Bỏ trích dẫn không có trong ngữ cảnh và mã D3FEND không xuất hiện trong tài liệu đã truy xuất."""
    text = "\n".join(ctx.values())
    note["cites"] = [c for c in note.get("cites", []) if c in ctx]
    kept = [r for r in note.get("recommend", []) if r.get("d3fend") and f"({r['d3fend']})" in text]
    note["dropped"] = len(note.get("recommend", [])) - len(kept)
    note["recommend"] = kept
    return note


def main(a):
    docs_dir = os.path.join(ROOT, "knowledge/labels")
    catalog = json.load(open(os.path.join(docs_dir, "catalog.json"), encoding="utf-8"))
    out = json.load(open(a.out, encoding="utf-8")) if os.path.exists(a.out) else {}
    for fid, fam in catalog["families"].items():
        if fid == "benign" or fid in out:
            continue
        ctx = retrieve(fid, catalog, docs_dir)
        docs = "\n\n".join(f"[{k}]\n{v}" for k, v in ctx.items())
        try:
            note = guard(ask(PROMPT.format(name=fam["name"], fid=fid, docs=docs)), ctx)
        except Exception as e:
            print(fid, "lỗi:", e)
            continue
        note.update(model=MODEL, retrieved=list(ctx), attack_version=catalog["attack_version"])
        out[fid] = note
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(fid, len(note["recommend"]), "đề xuất,", note["dropped"], "bị loại")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "knowledge/ai_notes.json"))
    main(ap.parse_args())
