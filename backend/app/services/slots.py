"""多轮槽位引导：识别 MVP 场景并追问缺失要素。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from app.repositories import database as db

_SCENES_PATH = PROJECT_ROOT / "configs" / "scenes.json"
_SCENES: list[dict] | None = None


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


def try_fill_from_message(scene_id: str, message: str, filled: dict) -> dict:
    """启发式：把用户本轮回复填入第一个缺失槽位。"""
    scene = get_scene(scene_id)
    if not scene:
        return filled
    out = dict(filled)
    for slot in scene.get("slots") or []:
        key = slot["key"]
        if not out.get(key):
            out[key] = message.strip()
            break
    return out


def build_slot_question(scene_id: str, missing: list[dict]) -> str:
    if not missing:
        return ""
    first = missing[0]
    rest = len(missing) - 1
    tip = f"（本场景「{scene_id}」还需补充 {rest} 项）" if rest > 0 else f"（场景：{scene_id}）"
    return f"为更准确分析，请先补充一点信息{tip}：\n\n**{first['prompt']}**"


def slots_context_text(scene_id: str, filled: dict) -> str:
    if not scene_id:
        return ""
    lines = [f"已识别场景：{scene_id}"]
    for k, v in filled.items():
        if v:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines)
