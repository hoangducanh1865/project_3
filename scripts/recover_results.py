"""Khôi phục result.json từ log của src.run (dòng INFO cuối mỗi lần chạy) khi thư mục kết quả bị ghi đè.
Dùng: python scripts/recover_results.py <log> <thư mục đích>
"""
import ast
import json
import os
import re
import sys

log, dst = sys.argv[1], sys.argv[2]
for line in open(log, encoding="utf-8"):
    m = re.search(r"INFO\] - (\{'protocol'.*\})\s*$", line)
    if not m:
        continue
    r = ast.literal_eval(re.sub(r"np\.str_\('([^']*)'\)", r"'\1'", m.group(1)))
    d = os.path.join(dst, f"{r['protocol']}_{r['heldout']}_{r['model']}")
    os.makedirs(d, exist_ok=True)
    json.dump(dict(r, recovered_from=os.path.basename(log)), open(os.path.join(d, "result.json"), "w"),
              ensure_ascii=False, indent=2, default=str)
    print(d)
