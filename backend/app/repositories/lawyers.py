"""律师认证仓储。"""
from __future__ import annotations

import json
from typing import Any

from app.repositories import database as db

VALID_STATUS = {"none", "pending", "approved", "rejected"}
# 职业认证类型：审核通过后写入 users.role
PROFESSIONS = {"lawyer", "judge", "prosecutor"}
PROFESSION_LABELS = {
    "lawyer": "律师",
    "judge": "法官",
    "prosecutor": "检察官",
}
CERTIFIED_ROLES = PROFESSIONS  # users.role 可能值


def normalize_profession(raw: str | None) -> str:
    p = (raw or "lawyer").strip().lower()
    return p if p in PROFESSIONS else "lawyer"


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
    profession: str = "lawyer",
) -> dict:
    profession = normalize_profession(profession)
    files_json = json.dumps(license_files, ensure_ascii=False)
    specs_json = json.dumps(specialties, ensure_ascii=False)
    existing = get_profile(user_id)
    if existing and existing.get("status") == "approved":
        raise ValueError("已通过认证，无需重复申请")
    if existing:
        db.execute(
            """
            UPDATE lawyer_profiles
            SET profession = ?, license_no = ?, region = ?, specialties_json = ?,
                license_files_json = ?, status = 'pending', reject_reason = '',
                reviewed_by = NULL, reviewed_at = NULL
            WHERE user_id = ?
            """,
            (profession, license_no.strip(), region.strip(), specs_json, files_json, user_id),
        )
    else:
        db.execute(
            """
            INSERT INTO lawyer_profiles
            (user_id, profession, license_no, region, specialties_json, license_files_json, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (user_id, profession, license_no.strip(), region.strip(), specs_json, files_json),
        )
    return get_profile(user_id)  # type: ignore[return-value]


def review(user_id: int, *, approve: bool, reviewer_id: int, reason: str = "") -> dict | None:
    status = "approved" if approve else "rejected"
    profile = get_profile(user_id)
    if not profile:
        return None
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
    # 通过后按职业写入 users.role；驳回/撤销则降回 user（admin 不变）
    user = db.query_one("SELECT role FROM users WHERE id = ?", (user_id,))
    if user and user.get("role") != "admin":
        if approve:
            role = normalize_profession(profile.get("profession"))
            db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        elif user.get("role") in CERTIFIED_ROLES:
            db.execute("UPDATE users SET role = 'user' WHERE id = ?", (user_id,))
    return get_profile(user_id)


def _rows_to_profiles(rows: list) -> list[dict]:
    out = []
    for r in rows:
        d = dict(r)
        d["license_files"] = _parse_json(d.pop("license_files_json", None), [])
        d["specialties"] = _parse_json(d.pop("specialties_json", None), [])
        reviewed = d.get("reviewed_at")
        if reviewed is not None and not isinstance(reviewed, str):
            d["reviewed_at"] = str(reviewed)
        out.append(d)
    return out


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
    return _rows_to_profiles(rows)


def list_by_status(status: str) -> list[dict]:
    if status not in VALID_STATUS or status == "none":
        return []
    rows = db.query(
        """
        SELECT p.*, u.username
        FROM lawyer_profiles p
        JOIN users u ON u.id = p.user_id
        WHERE p.status = ?
        ORDER BY COALESCE(p.reviewed_at, p.updated_at) DESC
        """,
        (status,),
    )
    return _rows_to_profiles(rows)


def revoke_approval(user_id: int, *, reviewer_id: int, reason: str = "") -> dict | None:
    """撤销已通过的律师认证，降回普通用户。"""
    profile = get_profile(user_id)
    if not profile or profile.get("status") != "approved":
        return None
    return review(
        user_id,
        approve=False,
        reviewer_id=reviewer_id,
        reason=reason.strip() or "管理员撤销认证",
    )


def is_admin_user(user_id: int) -> bool:
    row = db.query_one("SELECT role FROM users WHERE id = ?", (user_id,))
    return bool(row and row.get("role") == "admin")


def can_use_lawyer_write(user_id: int) -> bool:
    """案源认领等写操作：仅管理员或已认证律师（法官/检察官不可接单）。"""
    if is_admin_user(user_id):
        return True
    p = get_profile(user_id)
    return bool(
        p
        and p.get("status") == "approved"
        and normalize_profession(p.get("profession")) == "lawyer"
    )


def lawyer_mode_access(user_id: int) -> str:
    """none | pending_readonly | approved | rejected。管理员直接 approved。"""
    if is_admin_user(user_id):
        return "approved"
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
    if is_admin_user(user_id):
        return True
    row = db.query_one("SELECT user_id FROM disclaimer_acks WHERE user_id = ?", (user_id,))
    return bool(row)


def ack_disclaimer(user_id: int) -> None:
    if has_disclaimer_ack(user_id):
        return
    db.execute("INSERT INTO disclaimer_acks (user_id) VALUES (?)", (user_id,))
