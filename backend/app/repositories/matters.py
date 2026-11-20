"""案件工作区数据访问。"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from app.repositories import database as db

ARTIFACT_KINDS = {
    "note",
    "timeline",
    "evidence",
    "opinion",
    "contract",
    "extract",
    "elements",
    "template",
    "calculator",
}


def _json_load(raw: Any, default=None):
    if default is None:
        default = {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else default
        except json.JSONDecodeError:
            return default
    return default


def _meta(row: dict) -> dict:
    row = dict(row)
    row["meta"] = _json_load(row.pop("meta_json", None), {})
    return row


def create_matter(
    user_id: int,
    *,
    title: str,
    case_no: str = "",
    cause: str = "",
    role_mode: str = "lawyer",
    status: str = "open",
    meta: dict | None = None,
) -> dict:
    cur = db.execute(
        """
        INSERT INTO matters (user_id, title, case_no, cause, role_mode, status, meta_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            title[:200],
            (case_no or "")[:64],
            (cause or "")[:64],
            (role_mode or "lawyer")[:32],
            (status or "open")[:32],
            json.dumps(meta or {}, ensure_ascii=False),
        ),
    )
    return get_matter(user_id, int(cur.lastrowid))  # type: ignore[return-value]


def list_matters(user_id: int, role_mode: str | None = None) -> list[dict]:
    where = "m.user_id = ?"
    params: list[Any] = [user_id]
    if role_mode:
        where += " AND m.role_mode = ?"
        params.append(role_mode)
    rows = db.query(
        f"""
        SELECT m.*,
               (SELECT COUNT(*) FROM matter_artifacts a WHERE a.matter_id = m.id) AS artifact_count,
               (SELECT COUNT(*) FROM matter_deadlines d WHERE d.matter_id = m.id) AS deadline_count,
               (SELECT COUNT(*) FROM matter_deadlines d
                WHERE d.matter_id = m.id AND d.done = 0
                  AND d.due_date IS NOT NULL AND d.due_date < CURDATE()) AS overdue_count
        FROM matters m
        WHERE {where}
        ORDER BY m.updated_at DESC, m.id DESC
        """,
        tuple(params),
    )
    return [_meta(r) for r in rows]


def get_matter(user_id: int, matter_id: int) -> dict | None:
    row = db.query_one(
        """
        SELECT m.*,
               (SELECT COUNT(*) FROM matter_artifacts a WHERE a.matter_id = m.id) AS artifact_count,
               (SELECT COUNT(*) FROM matter_deadlines d WHERE d.matter_id = m.id) AS deadline_count,
               (SELECT COUNT(*) FROM matter_deadlines d
                WHERE d.matter_id = m.id AND d.done = 0
                  AND d.due_date IS NOT NULL AND d.due_date < CURDATE()) AS overdue_count
        FROM matters m
        WHERE m.id = ? AND m.user_id = ?
        """,
        (matter_id, user_id),
    )
    return _meta(row) if row else None


def update_matter(user_id: int, matter_id: int, fields: dict) -> dict | None:
    allowed = {"title", "case_no", "cause", "role_mode", "status", "meta"}
    sets: list[str] = []
    params: list[Any] = []
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        if k == "meta":
            sets.append("meta_json = ?")
            params.append(json.dumps(v if isinstance(v, dict) else {}, ensure_ascii=False))
        else:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        return get_matter(user_id, matter_id)
    params.extend([matter_id, user_id])
    db.execute(
        f"UPDATE matters SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
        tuple(params),
    )
    return get_matter(user_id, matter_id)


def delete_matter(user_id: int, matter_id: int) -> bool:
    cur = db.execute(
        "DELETE FROM matters WHERE id = ? AND user_id = ?",
        (matter_id, user_id),
    )
    return bool(cur.rowcount)


def list_artifacts(user_id: int, matter_id: int) -> list[dict]:
    if not get_matter(user_id, matter_id):
        return []
    rows = db.query(
        """
        SELECT id, matter_id, kind, title, ref_record_id, payload_json, created_at
        FROM matter_artifacts
        WHERE matter_id = ?
        ORDER BY id DESC
        """,
        (matter_id,),
    )
    out = []
    for r in rows:
        item = dict(r)
        item["payload"] = _json_load(item.pop("payload_json", None), {})
        out.append(item)
    return out


def add_artifact(
    user_id: int,
    matter_id: int,
    *,
    kind: str,
    title: str = "",
    ref_record_id: int | None = None,
    payload: dict | None = None,
) -> dict | None:
    if not get_matter(user_id, matter_id):
        return None
    kind = (kind or "note")[:32]
    if kind not in ARTIFACT_KINDS:
        kind = "note"
    cur = db.execute(
        """
        INSERT INTO matter_artifacts (matter_id, kind, title, ref_record_id, payload_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            matter_id,
            kind,
            (title or "")[:200],
            ref_record_id,
            json.dumps(payload or {}, ensure_ascii=False),
        ),
    )
    db.execute(
        "UPDATE matters SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (matter_id,),
    )
    row = db.query_one(
        "SELECT id, matter_id, kind, title, ref_record_id, payload_json, created_at FROM matter_artifacts WHERE id = ?",
        (int(cur.lastrowid),),
    )
    if not row:
        return None
    row["payload"] = _json_load(row.pop("payload_json", None), {})
    return row


def delete_artifact(user_id: int, matter_id: int, artifact_id: int) -> bool:
    if not get_matter(user_id, matter_id):
        return False
    cur = db.execute(
        "DELETE FROM matter_artifacts WHERE id = ? AND matter_id = ?",
        (artifact_id, matter_id),
    )
    return bool(cur.rowcount)


def _deadline_row(r: dict) -> dict:
    item = dict(r)
    item["done"] = bool(item.get("done"))
    due = item.get("due_date")
    overdue = False
    if due and not item["done"]:
        try:
            if isinstance(due, str):
                d = date.fromisoformat(due[:10])
            elif isinstance(due, datetime):
                d = due.date()
            elif isinstance(due, date):
                d = due
            else:
                d = None
            if d and d < date.today():
                overdue = True
        except ValueError:
            overdue = False
    item["overdue"] = overdue
    if due is not None and not isinstance(due, str):
        item["due_date"] = due.isoformat() if hasattr(due, "isoformat") else str(due)
    return item


def list_deadlines(user_id: int, matter_id: int) -> list[dict]:
    if not get_matter(user_id, matter_id):
        return []
    rows = db.query(
        """
        SELECT id, matter_id, label, due_date, calc_key, done, created_at
        FROM matter_deadlines
        WHERE matter_id = ?
        ORDER BY (due_date IS NULL), due_date ASC, id DESC
        """,
        (matter_id,),
    )
    return [_deadline_row(r) for r in rows]


def add_deadline(
    user_id: int,
    matter_id: int,
    *,
    label: str,
    due_date: str | None = None,
    calc_key: str = "",
    done: bool = False,
) -> dict | None:
    if not get_matter(user_id, matter_id):
        return None
    cur = db.execute(
        """
        INSERT INTO matter_deadlines (matter_id, label, due_date, calc_key, done)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            matter_id,
            label[:200],
            due_date or None,
            (calc_key or "")[:64],
            1 if done else 0,
        ),
    )
    db.execute(
        "UPDATE matters SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (matter_id,),
    )
    row = db.query_one(
        "SELECT id, matter_id, label, due_date, calc_key, done, created_at FROM matter_deadlines WHERE id = ?",
        (int(cur.lastrowid),),
    )
    return _deadline_row(row) if row else None


def update_deadline(
    user_id: int,
    matter_id: int,
    deadline_id: int,
    fields: dict,
) -> dict | None:
    if not get_matter(user_id, matter_id):
        return None
    allowed = {"label", "due_date", "calc_key", "done"}
    sets: list[str] = []
    params: list[Any] = []
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        if k == "done":
            sets.append("done = ?")
            params.append(1 if v else 0)
        else:
            sets.append(f"{k} = ?")
            params.append(v)
    if not sets:
        row = db.query_one(
            "SELECT id, matter_id, label, due_date, calc_key, done, created_at FROM matter_deadlines WHERE id = ? AND matter_id = ?",
            (deadline_id, matter_id),
        )
        return _deadline_row(row) if row else None
    params.extend([deadline_id, matter_id])
    db.execute(
        f"UPDATE matter_deadlines SET {', '.join(sets)} WHERE id = ? AND matter_id = ?",
        tuple(params),
    )
    row = db.query_one(
        "SELECT id, matter_id, label, due_date, calc_key, done, created_at FROM matter_deadlines WHERE id = ? AND matter_id = ?",
        (deadline_id, matter_id),
    )
    return _deadline_row(row) if row else None


def delete_deadline(user_id: int, matter_id: int, deadline_id: int) -> bool:
    if not get_matter(user_id, matter_id):
        return False
    cur = db.execute(
        "DELETE FROM matter_deadlines WHERE id = ? AND matter_id = ?",
        (deadline_id, matter_id),
    )
    return bool(cur.rowcount)
