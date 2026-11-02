"""用户工作记录：文书、计算器、合同审查、意见书草稿可回看。"""
from __future__ import annotations

import json
import logging

from app.repositories import database as db

logger = logging.getLogger("app")

KINDS = {"template", "calculator", "contract", "opinion"}


def save_record(user_id: int, kind: str, title: str, summary: str, payload: dict) -> int | None:
    if kind not in KINDS:
        return None
    try:
        cur = db.execute(
            "INSERT INTO user_records (user_id, kind, title, summary, payload_json) VALUES (?, ?, ?, ?, ?)",
            (user_id, kind, title[:200], summary[:500], json.dumps(payload, ensure_ascii=False)),
        )
        return int(cur.lastrowid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("保存用户记录失败: %s", exc)
        return None


def _payload(raw) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def list_records(
    user_id: int,
    kind: str,
    *,
    page: int = 1,
    page_size: int = 10,
    q: str = "",
) -> dict:
    """分页列出个人记录；支持标题/摘要关键词搜索。"""
    page = max(1, int(page or 1))
    page_size = max(5, min(int(page_size or 10), 50))
    keyword = (q or "").strip()

    where = "user_id = ? AND kind = ?"
    params: list = [user_id, kind]
    if keyword:
        where += " AND (title LIKE ? OR summary LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like])

    total_row = db.query_one(
        f"SELECT COUNT(*) AS c FROM user_records WHERE {where}",
        tuple(params),
    )
    total = int((total_row or {}).get("c") or 0)
    offset = (page - 1) * page_size
    rows = db.query(
        f"""
        SELECT id, kind, title, summary, created_at
        FROM user_records
        WHERE {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, page_size, offset),
    )
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "page_count": max(1, (total + page_size - 1) // page_size) if total else 1,
    }


def delete_records_by_kind(user_id: int, kind: str) -> int:
    """清空某一类个人记录。"""
    if kind not in KINDS:
        return 0
    cur = db.execute(
        "DELETE FROM user_records WHERE user_id = ? AND kind = ?",
        (user_id, kind),
    )
    return int(cur.rowcount or 0)


def get_record(user_id: int, record_id: int) -> dict | None:
    row = db.query_one(
        """
        SELECT id, kind, title, summary, payload_json, created_at
        FROM user_records
        WHERE id = ? AND user_id = ?
        """,
        (record_id, user_id),
    )
    if not row:
        return None
    row["payload"] = _payload(row.pop("payload_json", None))
    return row


def delete_record(user_id: int, record_id: int) -> bool:
    cur = db.execute(
        "DELETE FROM user_records WHERE id = ? AND user_id = ?",
        (record_id, user_id),
    )
    return bool(cur.rowcount)
