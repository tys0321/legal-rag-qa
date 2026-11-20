"""罪名构成要件勾选与补侦要点。"""
from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "crime_elements.json"

GROUP_ORDER = ("构成要件", "证据要点", "程序审查")


def _load() -> dict:
    if not DATA_PATH.exists():
        return {}
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def list_charges() -> list[dict]:
    """返回罪名摘要列表（含分类，便于前端筛选）。"""
    out = []
    for name, info in _load().items():
        out.append(
            {
                "charge": info.get("charge") or name,
                "key": name,
                "category": info.get("category") or "其他",
                "article_hint": info.get("article_hint") or "",
                "element_count": len(info.get("elements") or []),
            }
        )
    # 按分类、罪名排序
    out.sort(key=lambda x: (x["category"], x["charge"]))
    return out


def list_charge_names() -> list[str]:
    return [c["key"] for c in list_charges()]


def get_charge(charge: str) -> dict | None:
    data = _load()
    if charge in data:
        return data[charge]
    for k, v in data.items():
        title = v.get("charge") or k
        if k in charge or charge in k or charge in title or title in charge:
            return v
    return None


def _grouped(elements: list[dict]) -> list[dict]:
    buckets: dict[str, list] = {g: [] for g in GROUP_ORDER}
    other: list = []
    for e in elements:
        g = e.get("group") or "构成要件"
        if g in buckets:
            buckets[g].append(e)
        else:
            other.append(e)
    rows = []
    for g in GROUP_ORDER:
        if buckets[g]:
            rows.append({"group": g, "items": buckets[g]})
    if other:
        rows.append({"group": "其他", "items": other})
    return rows


def check_elements(
    charge: str,
    checked_ids: list[str],
    notes: dict[str, str] | None = None,
) -> dict:
    info = get_charge(charge)
    if not info:
        return {
            "charge": charge,
            "found": False,
            "category": "",
            "compare": [],
            "elements": [],
            "groups": [],
            "missing": [],
            "supplement_text": f"未收录罪名「{charge}」的要件库，请人工对照构成要件整理补侦提纲。",
            "checked_ids": checked_ids,
        }
    notes = notes or {}
    checked = set(checked_ids or [])
    elements = info.get("elements") or []
    missing = [e for e in elements if e.get("id") not in checked]
    compare = info.get("compare") or []

    lines = [
        f"【罪名】{info.get('charge')}（{info.get('article_hint') or '须核对条文'}）",
        f"【类型】{info.get('category') or '未分类'}",
    ]
    if compare:
        lines.append(f"【此罪彼罪注意】{' / '.join(compare)}")

    lines.append("【勾选总览】")
    for g in GROUP_ORDER:
        group_items = [e for e in elements if (e.get("group") or "构成要件") == g]
        if not group_items:
            continue
        lines.append(f"— {g} —")
        for e in group_items:
            mark = "✓" if e.get("id") in checked else "✗"
            note = (notes.get(e["id"]) or "").strip()
            extra = f"；备注：{note}" if note else ""
            lines.append(f"- [{mark}] {e.get('label')} — {e.get('desc')}{extra}")

    lines.append("【补侦/补查要点】")
    if not missing:
        lines.append(
            "- 所列审查项均已勾选。请仍复核：证明力、合法性、印证完整性；"
            + (f"并注意与「{'、'.join(compare)}」界分。" if compare else "并注意此罪彼罪界分。")
        )
    else:
        # 按组输出缺失项
        for g in GROUP_ORDER:
            miss_g = [e for e in missing if (e.get("group") or "构成要件") == g]
            if not miss_g:
                continue
            lines.append(f"— 待补·{g} —")
            for e in miss_g:
                ev = (e.get("evidence") or "").strip()
                tip = f"建议调取：{ev}" if ev else "列明待调取书证/鉴定/证人及证明对象。"
                note = (notes.get(e["id"]) or "").strip()
                note_s = f"；承办备注：{note}" if note else ""
                lines.append(f"- 「{e.get('label')}」：{e.get('desc')}；{tip}{note_s}")

    return {
        "charge": info.get("charge") or charge,
        "article_hint": info.get("article_hint") or "",
        "category": info.get("category") or "",
        "compare": compare,
        "found": True,
        "elements": elements,
        "groups": _grouped(elements),
        "missing": missing,
        "checked_ids": list(checked),
        "supplement_text": "\n".join(lines),
    }
