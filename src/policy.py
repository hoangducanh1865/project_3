"""Phân quyền ứng phó theo conf/policy.yaml: ai thực hiện, ai duyệt, AI được làm đến đâu.

Dùng ở luồng giả lập (scripts/precompute_live.py) và mọi nơi có AI ra quyết định (demo/soc.py): trước khi thực hiện
một hành động, gọi authorize(); AI chỉ được thực hiện khi authorize trả về True.
"""
import os
from functools import lru_cache

import yaml

PATH = os.path.join(os.path.dirname(__file__), "..", "conf", "policy.yaml")


@lru_cache(maxsize=1)
def load():
    with open(PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def plan(level, target_role=None):
    """Kế hoạch thực hiện cho một mức ứng phó, có tính tới vai trò của máy đích (hạ tầng được bảo vệ)."""
    p = load()
    lv = p["levels"][level]
    act = p["actions"][lv["action"]]
    ai = lv["ai"]
    protected = target_role in p["ai"]["protected_roles"]
    if lv["action"] in p["ai"]["forbidden_actions"] or protected:
        ai = "suggest"
    ai_text = {"suggest": "chỉ đề xuất",
               "act_on_timeout": f"được tự thực hiện nếu sau {p['ai']['timeout_min']} phút chưa ai duyệt"}[ai]
    if protected and lv["ai"] != "suggest":
        ai_text += " (máy đích là hạ tầng nên AI chỉ đề xuất)"
    return {"action": lv["action"], "action_name": act["name"], "action_desc": act["desc"], "ttl_min": lv["ttl"],
            "reversible": act["reversible"], "executor": p["roles"][lv["executor"]]["name"],
            "approver": p["roles"][lv["approver"]]["name"] if lv["approver"] else None, "ai": ai, "ai_text": ai_text}


def authorize(actor, level, target_role=None, waited_min=0.0, approved=False):
    """-> (được phép, lý do). actor: system | ai | analyst | lead."""
    p = load()
    lv = p["levels"][level]
    rank = {"system": 0, "ai": 0, "analyst": 1, "lead": 2}
    if actor == "ai":
        pl = plan(level, target_role)
        if pl["ai"] != "act_on_timeout":
            return False, f"AI chỉ được đề xuất ở mức {level}"
        if approved:
            return False, "đã có người quyết định"
        if waited_min < p["ai"]["timeout_min"]:
            return False, f"chưa hết {p['ai']['timeout_min']} phút chờ người duyệt"
        return True, f"hết thời gian chờ, hành động {pl['action_name']} có thời hạn {lv['ttl']} phút"
    if actor == "system":
        return (lv["executor"] == "system"), ("luật tự động" if lv["executor"] == "system" else "cần người duyệt")
    need = lv["approver"] or lv["executor"]
    ok = rank[actor] >= rank[need]
    return ok, ("đủ quyền" if ok else f"cần {p['roles'][need]['name']}")
