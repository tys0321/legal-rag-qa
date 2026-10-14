"""律师认证仓储。"""
from __future__ import annotations

import json
from typing import Any

from app.repositories import database as db

VALID_STATUS = {"none", "pending", "approved", "rejected"}


def _parse_json(raw: Any, default):
    if raw is None:
        return default
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def get_profile(user_id: int) -> dict | None:
    row = db.query_one("SELECT * FROM lawyer_profiles WHERE user_id = ?", (user_id,))
    if not row:
        return None
    d = dict(row)
    d["license_files"] = _parse_json(d.pop("license_files_json", None), [])
    d["specialties"] = _parse_json(d.pop("specialties_json", None), [])
    return d


def upsert_application(
    user_id: int,
    *,
    license_no: str,
    region: str,
    specialties: list[str],
    license_files: list[str],
) -> dict:
    files_json = json.dumps(license_files, ensure_ascii=False)
    specs_json = json.dumps(specialties, ensure_ascii=False)
    existing = get_profile(user_id)
    if existing and existing.get("status") == "approved":
        raise ValueError("已通过认证，无需重复申请")
    if existing:
        db.execute(
            """
            UPDATE lawyer_profiles
            SET license_no = ?, region = ?, specialties_json = ?, license_files_json = ?,
                status = 'pending', reject_reason = '', reviewed_by = NULL, reviewed_at = NULL
            WHERE user_id = ?
            """,
            (license_no.strip(), region.strip(), specs_json, files_json, user_id),
        )
    else:
        db.execute(
            """
            INSERT INTO lawyer_profiles
            (user_id, license_no, region, specialties_json, license_files_json, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (user_id, license_no.strip(), region.strip(), specs_json, files_json),
        )
    return get_profile(user_id)  # type: ignore[return-value]


def review(user_id: int, *, approve: bool, reviewer_id: int, reason: str = "") -> dict | None:
    status = "approved" if approve else "rejected"
    cur = db.execute(
        """
        UPDATE lawyer_profiles
        SET status = ?, reject_reason = ?, reviewed_by = ?, reviewed_at = NOW()
        WHERE user_id = ?
        """,
        (status, reason.strip(), reviewer_id, user_id),
    )
    if cur.rowcount == 0:
        return None
    # 通过后把 users.role 标为 lawyer（admin 不变）
    if approve:
        user = db.query_one("SELECT role FROM users WHERE id = ?", (user_id,))
        if user and user.get("role") != "admin":
            db.execute("UPDATE users SET role = 'lawyer' WHERE id = ?", (user_id,))
    else:
        user = db.query_one("SELECT role FROM users WHERE id = ?", (user_id,))
        if user and user.get("role") == "lawyer":
            db.execute("UPDATE users SET role = 'user' WHERE id = ?", (user_id,))
    return get_profile(user_id)


def list_pending() -> list[dict]:
    rows = db.query(
        """
        SELECT p.*, u.username
        FROM lawyer_profiles p
        JOIN users u ON u.id = p.user_id
        WHERE p.status = 'pending'
        ORDER BY p.updated_at DESC
        """
    )
    out = []
    for r in rows:
        d = dict(r)
        d["license_files"] = _parse_json(d.pop("license_files_json", None), [])
        d["specialties"] = _parse_json(d.pop("specialties_json", None), [])
        out.append(d)
    return out


def can_use_lawyer_write(user_id: int) -> bool:
    """认领/联系等写操作：仅 approved。"""
    p = get_profile(user_id)
    return bool(p and p.get("status") == "approved")


def lawyer_mode_access(user_id: int) -> str:
    """none | pending_readonly | approved | rejected。"""
    p = get_profile(user_id)
    if not p:
        return "none"
    return {
        "pending": "pending_readonly",
        "approved": "approved",
        "rejected": "rejected",
        "none": "none",
    }.get(p.get("status") or "none", "none")


def has_disclaimer_ack(user_id: int) -> bool:
    row = db.query_one("SELECT user_id FROM disclaimer_acks WHERE user_id = ?", (user_id,))
    return bool(row)


def ack_disclaimer(user_id: int) -> None:
    if has_disclaimer_ack(user_id):
        return
    db.execute("INSERT INTO disclaimer_acks (user_id) VALUES (?)", (user_id,))
