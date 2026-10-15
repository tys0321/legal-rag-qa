"""52 一级场景分类目录（前台信息架构 + MVP 激活）。"""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import PROJECT_ROOT

_CATALOG_PATH = PROJECT_ROOT / "configs" / "scenes_catalog.json"
_CACHE: dict | None = None


def load_catalog() -> dict:
    global _CACHE
    if _CACHE is None:
        if _CATALOG_PATH.exists():
            _CACHE = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        else:
            _CACHE = {"version": 0, "mvp_ids": [], "catalog": []}
    return _CACHE


def reload_catalog() -> dict:
    global _CACHE
    _CACHE = None
    return load_catalog()


def list_catalog(*, status: str | None = None) -> list[dict]:
    items = list(load_catalog().get("catalog") or [])
    if status:
        items = [x for x in items if x.get("status") == status]
    return items


def mvp_ids() -> list[str]:
    return list(load_catalog().get("mvp_ids") or [])


def is_active(scene_id: str) -> bool:
    for item in list_catalog():
        if item.get("id") == scene_id:
            return item.get("status") == "active"
    return False


def catalog_summary() -> dict:
    items = list_catalog()
    active = [x for x in items if x.get("status") == "active"]
    coming = [x for x in items if x.get("status") == "coming_soon"]
    groups: dict[str, int] = {}
    for x in items:
        g = x.get("group") or "其他"
        groups[g] = groups.get(g, 0) + 1
    return {
        "version": load_catalog().get("version", 1),
        "total": len(items),
        "active_count": len(active),
        "coming_soon_count": len(coming),
        "mvp_ids": mvp_ids(),
        "groups": groups,
        "items": items,
    }
