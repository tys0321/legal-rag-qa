"""轻量律所：创建、成员邀请、所内可见查询。"""
from __future__ import annotations

from app.repositories import database as db

MEMBER_ROLES = {"owner", "member"}


def get_firm(firm_id: int) -> dict | None:
    row = db.query_one("SELECT * FROM firms WHERE id = ?", (firm_id,))
    return dict(row) if row else None


def get_membership(user_id: int) -> dict | None:
    row = db.query_one(
        """
        SELECT fm.firm_id, fm.user_id, fm.role, fm.joined_at, f.name AS firm_name, f.owner_user_id
        FROM firm_members fm
        JOIN firms f ON f.id = fm.firm_id
        WHERE fm.user_id = ?
        """,
        (user_id,),
    )
    return dict(row) if row else None


def list_members(firm_id: int) -> list[dict]:
    rows = db.query(
        """
        SELECT fm.firm_id, fm.user_id, fm.role, fm.joined_at, u.username
        FROM firm_members fm
        JOIN users u ON u.id = fm.user_id
        WHERE fm.firm_id = ?
        ORDER BY FIELD(fm.role, 'owner', 'member'), fm.joined_at ASC
        """,
        (firm_id,),
    )
    return [dict(r) for r in rows]


def create_firm(owner_user_id: int, name: str) -> dict:
    name = (name or "").strip()
    if len(name) < 2:
        raise ValueError("律所名称至少 2 个字符")
    existing = get_membership(owner_user_id)
    if existing:
        raise ValueError("您已加入律所，无法重复创建")

    cur = db.execute(
        "INSERT INTO firms (name, owner_user_id) VALUES (?, ?)",
        (name, owner_user_id),
    )
    firm_id = int(cur.lastrowid)
    db.execute(
        "INSERT INTO firm_members (firm_id, user_id, role) VALUES (?, ?, 'owner')",
        (firm_id, owner_user_id),
    )
    db.execute("UPDATE users SET firm_id = ? WHERE id = ?", (firm_id, owner_user_id))
    firm = get_firm(firm_id)
    assert firm is not None
    return firm


def invite_member(firm_id: int, actor_id: int, username: str) -> dict:
    firm = get_firm(firm_id)
    if not firm:
        raise LookupError("律所不存在")
    actor = db.query_one(
        "SELECT role FROM firm_members WHERE firm_id = ? AND user_id = ?",
        (firm_id, actor_id),
    )
    if not actor or actor.get("role") != "owner":
        raise PermissionError("仅律所负责人可邀请成员")

    username = (username or "").strip()
    user = db.query_one("SELECT id, username, firm_id FROM users WHERE username = ?", (username,))
    if not user:
        raise LookupError("用户不存在")
    invitee_id = int(user["id"])
    if invitee_id == actor_id:
        raise ValueError("不能邀请自己")

    if get_membership(invitee_id):
        raise ValueError("该用户已加入其他律所")

    db.execute(
        "INSERT INTO firm_members (firm_id, user_id, role) VALUES (?, ?, 'member')",
        (firm_id, invitee_id),
    )
    db.execute("UPDATE users SET firm_id = ? WHERE id = ?", (firm_id, invitee_id))
    return {
        "firm_id": firm_id,
        "user_id": invitee_id,
        "username": user["username"],
        "role": "member",
    }


def same_firm(user_a: int, user_b: int) -> bool:
    if user_a == user_b:
        return True
    ma = get_membership(user_a)
    mb = get_membership(user_b)
    if not ma or not mb:
        return False
    return int(ma["firm_id"]) == int(mb["firm_id"])


def firm_detail(firm_id: int) -> dict | None:
    firm = get_firm(firm_id)
    if not firm:
        return None
    return {
        **firm,
        "members": list_members(firm_id),
    }
