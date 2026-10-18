"""用户工作记录：文书、计算器、合同审查可回看。"""
from __future__ import annotations

import json
import logging

from app.repositories import database as db

logger = logging.getLogger("app")

KINDS = {"template", "calculator", "contract"}


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


def list_records(user_id: int, kind: str, limit: int = 20) -> list[dict]:
    rows = db.query(
        """
        SELECT id, kind, title, summary, created_at
        FROM user_records
        WHERE user_id = ? AND kind = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, kind, limit),
    )
    return rows


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
