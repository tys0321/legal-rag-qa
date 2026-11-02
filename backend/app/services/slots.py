"""多轮槽位引导：识别 MVP 场景并追问缺失要素（ABCD 选项）。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from app.repositories import database as db

_SCENES_PATH = PROJECT_ROOT / "configs" / "scenes.json"
_SCENES: list[dict] | None = None

_OPTION_KEYS = ("A", "B", "C", "D")
_OTHER_LABEL = "其他情况"


def load_scenes() -> list[dict]:
    global _SCENES
    if _SCENES is None:
        if _SCENES_PATH.exists():
            data = json.loads(_SCENES_PATH.read_text(encoding="utf-8"))
            _SCENES = list(data.get("scenes") or [])
        else:
            _SCENES = []
    return _SCENES


def detect_scene(question: str) -> str | None:
    """仅在 MVP 已激活且配置了关键词的场景中识别。"""
    from app.services.scenes_catalog import is_active

    q = question or ""
    best_id = None
    best_hits = 0
    for scene in load_scenes():
        sid = scene.get("id") or ""
        if sid and not is_active(sid):
            continue
        hits = sum(1 for kw in scene.get("keywords") or [] if kw in q)
        if hits > best_hits:
            best_hits = hits
            best_id = sid
    return best_id if best_hits > 0 else None


def get_scene(scene_id: str) -> dict | None:
    for s in load_scenes():
        if s["id"] == scene_id:
            return s
    return None


def _parse_slots(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw) or {}
        except json.JSONDecodeError:
            return {}
    return {}


def get_session_slots(session_id: str) -> dict:
    row = db.query_one("SELECT scene, slots_json FROM session_slots WHERE session_id = ?", (session_id,))
    if not row:
        return {"scene": "", "slots": {}}
    return {"scene": row.get("scene") or "", "slots": _parse_slots(row.get("slots_json"))}


def save_session_slots(session_id: str, scene: str, slots: dict) -> None:
    existing = db.query_one("SELECT session_id FROM session_slots WHERE session_id = ?", (session_id,))
    payload = json.dumps(slots, ensure_ascii=False)
    if existing:
        db.execute(
            "UPDATE session_slots SET scene = ?, slots_json = ? WHERE session_id = ?",
            (scene, payload, session_id),
        )
    else:
        db.execute(
            "INSERT INTO session_slots (session_id, scene, slots_json) VALUES (?, ?, ?)",
            (session_id, scene, payload),
        )


def missing_slots(scene_id: str, filled: dict) -> list[dict]:
    scene = get_scene(scene_id)
    if not scene:
        return []
    miss = []
    for slot in scene.get("slots") or []:
        key = slot["key"]
        val = (filled.get(key) or "").strip() if isinstance(filled.get(key), str) else filled.get(key)
        if slot.get("required", True) and not val:
            miss.append(slot)
    return miss


def build_slot_options(slot: dict) -> list[dict]:
    """返回 A/B/C（来自配置）+ 固定 D=其他情况。"""
    raw = list(slot.get("options") or [])
    out: list[dict] = []
    for i, label in enumerate(raw[:3]):
        text = str(label).strip()
        if not text:
            continue
        out.append({"key": _OPTION_KEYS[i], "label": text})
    # 不足 3 个时用占位，保证至少有可选
    while len(out) < 3:
        fallback = ["是", "否", "不确定"][len(out)]
        out.append({"key": _OPTION_KEYS[len(out)], "label": fallback})
    out.append({"key": "D", "label": _OTHER_LABEL})
    return out


def _resolve_choice(message: str, slot: dict) -> str | None:
    """把用户回复解析为槽位取值；无法识别时返回 None（整句填入）。"""
    text = (message or "").strip()
    if not text:
        return None
    options = build_slot_options(slot)

    # A. / A、 / 选A / 选项A
    m = re.match(r"^(?:选(?:项)?|选项)?\s*([A-Da-d])(?:[.、．:：\s]+)(.*)$", text)
    if m:
        key = m.group(1).upper()
        rest = (m.group(2) or "").strip()
        if key == "D":
            return rest if rest and rest != _OTHER_LABEL else None
        for opt in options:
            if opt["key"] == key:
                return rest if rest else opt["label"]
        return rest or None

    if re.fullmatch(r"[A-Da-d]", text):
        key = text.upper()
        if key == "D":
            return None
        for opt in options:
            if opt["key"] == key:
                return opt["label"]

    for opt in options:
        if opt["key"] == "D":
            continue
        if text == opt["label"] or opt["label"] in text:
            return opt["label"]

    if text in (_OTHER_LABEL, "其他", "别的情况"):
        return None

    return text


def try_fill_from_message(scene_id: str, message: str, filled: dict) -> dict:
    """启发式：把用户本轮回复填入第一个缺失槽位（支持 ABCD）。"""
    scene = get_scene(scene_id)
    if not scene:
        return filled
    out = dict(filled)
    for slot in scene.get("slots") or []:
        key = slot["key"]
        if not out.get(key):
            resolved = _resolve_choice(message, slot)
            if resolved:
                out[key] = resolved
            else:
                # D 或其他自由描述：整句写入
                out[key] = message.strip()
            break
    return out


def build_slot_question(scene_id: str, missing: list[dict]) -> str:
    """气泡里只写问题；ABCD 由前端选项条展示，避免再让用户打字。"""
    if not missing:
        return ""
    first = missing[0]
    rest = len(missing) - 1
    tip = f"（「{scene_id}」还需补充 {rest} 项）" if rest > 0 else f"（场景：{scene_id}）"
    return f"为更准确分析，请点选下方选项补充信息{tip}：\n\n**{first['prompt']}**"


def slots_context_text(scene_id: str, filled: dict) -> str:
    if not scene_id:
        return ""
    lines = [f"已识别场景：{scene_id}"]
    for k, v in filled.items():
        if v:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def need_slots_payload(missing: list[dict]) -> list[dict]:
    return [
        {
            "key": m["key"],
            "prompt": m["prompt"],
            "options": build_slot_options(m),
        }
        for m in missing
    ]
