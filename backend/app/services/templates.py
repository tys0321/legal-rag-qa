"""文书模板：配置化加载 + 槽位填充 → Markdown。"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.core.errors import AppError

_CATALOG_PATH = PROJECT_ROOT / "configs" / "document_templates.json"
_CACHE: dict | None = None

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

DEFAULT_WATERMARK = "AI 生成草稿，须律师审核"
DEFAULT_DISCLAIMER = (
    "本文件由 AI 根据用户填写内容套用模板生成，仅供一般性参考，"
    "不构成正式法律文书或律师意见。使用前请咨询执业律师并根据个案修改。"
)


def load_catalog() -> dict:
    global _CACHE
    if _CACHE is None:
        path = Path(_CATALOG_PATH)
        if not path.exists():
            raise AppError("文书模板配置缺失", 503)
        _CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE


def reload_catalog() -> dict:
    global _CACHE
    _CACHE = None
    return load_catalog()


def _templates() -> list[dict]:
    return list(load_catalog().get("templates") or [])


def watermark() -> str:
    return str(load_catalog().get("watermark") or DEFAULT_WATERMARK)


def disclaimer() -> str:
    return str(load_catalog().get("disclaimer") or DEFAULT_DISCLAIMER)


def list_templates() -> dict:
    items = []
    for t in _templates():
        fields = t.get("fields") or []
        items.append(
            {
                "id": t["id"],
                "name": t.get("name") or t["id"],
                "category": t.get("category") or "",
                "description": t.get("description") or "",
                "field_count": len(fields),
            }
        )
    return {
        "version": int(load_catalog().get("version") or 1),
        "total": len(items),
        "watermark": watermark(),
        "items": items,
    }


def get_template(template_id: str) -> dict:
    for t in _templates():
        if t.get("id") == template_id:
            return t
    raise AppError(f"未找到文书模板: {template_id}", 404)


def get_template_detail(template_id: str) -> dict:
    t = get_template(template_id)
    fields = []
    for f in t.get("fields") or []:
        fields.append(
            {
                "key": f.get("key") or "",
                "label": f.get("label") or f.get("key") or "",
                "type": f.get("type") or "text",
                "required": bool(f.get("required")),
                "placeholder": f.get("placeholder") or "",
            }
        )
    return {
        "id": t["id"],
        "name": t.get("name") or t["id"],
        "category": t.get("category") or "",
        "description": t.get("description") or "",
        "fields": fields,
        "watermark": watermark(),
        "disclaimer": disclaimer(),
    }


def _render(body: str, values: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        val = values.get(key)
        if val is None or str(val).strip() == "":
            return "【待填写】"
        return str(val).strip()

    return _PLACEHOLDER_RE.sub(repl, body)


def fill_template(template_id: str, field_values: dict[str, str] | None = None) -> dict:
    t = get_template(template_id)
    values = {k: (v if v is not None else "") for k, v in (field_values or {}).items()}
    values["watermark"] = watermark()
    values["disclaimer"] = disclaimer()

    missing: list[str] = []
    for f in t.get("fields") or []:
        key = f.get("key") or ""
        if not key:
            continue
        if f.get("required") and not str(values.get(key) or "").strip():
            missing.append(key)

    body = t.get("body") or ""
    markdown = _render(body, values).strip() + "\n"

    return {
        "id": t["id"],
        "name": t.get("name") or t["id"],
        "category": t.get("category") or "",
        "markdown": markdown,
        "watermark": watermark(),
        "disclaimer": disclaimer(),
        "missing_required": missing,
    }
