"""Tạo secret "project3" trên Modal từ .env, sinh MODAL_API_KEY nếu chưa có. Không in giá trị của key."""
import secrets
from pathlib import Path

import modal

ENV = Path(__file__).resolve().parents[1] / ".env"
vals = {}
for line in ENV.read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip().strip("\"'")
if not vals.get("MODAL_API_KEY"):
    vals["MODAL_API_KEY"] = secrets.token_urlsafe(32)
    with ENV.open("a") as f:
        f.write(f"\n\n### Khoá nội bộ giữa web và API Modal\nMODAL_API_KEY=\"{vals['MODAL_API_KEY']}\"\n")
modal.Secret.objects.create("project3", {"HF_TOKEN": vals["HF_TOKEN"], "API_KEY": vals["MODAL_API_KEY"]},
                            allow_existing=True)
print("đã tạo secret project3")
if vals.get("TELEGRAM_BOT_TOKEN") and vals.get("TELEGRAM_CHAT_ID"):
    modal.Secret.objects.create("project3-telegram", {k: vals[k] for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")},
                                allow_existing=True)
    print("đã tạo secret project3-telegram")
