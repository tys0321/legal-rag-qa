"""管理后台 API（仅 admin 可访问）。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.core.admin_perms import (
    PERM_CATALOG,
    effective_perms,
    is_root_admin,
    normalize_grant,
    parse_perms,
    require_perm,
)
from app.core.auth import require_admin
from app.core.config import settings
from app.core.errors import AppError
from app.repositories import database as db
from app.repositories import feedbacks as feedback_repo
from app.repositories.vector_store import get_store
from app.schemas.admin import (
    AdminAccessResponse,
    AdminPermItem,
    AdminUserItem,
    AdminUserListResponse,
    SetRoleRequest,
    SystemStatusResponse,
    UserStatsResponse,
)
from app.schemas.feedback import FeedbackAdminItem, FeedbackAdminList
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _user_item(row: dict) -> AdminUserItem:
    perms = parse_perms(row.get("admin_perms"))
    return AdminUserItem(
        id=int(row["id"]),
        username=row["username"],
        role=row["role"],
        created_at=str(row["created_at"]),
        session_count=int(row.get("session_count") or 0),
        message_count=int(row.get("message_count") or 0),
        permissions=effective_perms({"username": row["username"], "role": row["role"], "admin_perms": perms})
        if row["role"] == "admin"
        else [],
        is_root=row["username"] == settings.sole_admin_username and row["role"] == "admin",
    )


@router.get("/access", response_model=AdminAccessResponse)
def admin_access(admin: dict = Depends(require_admin)) -> AdminAccessResponse:
    """当前管理员可见板块。tys 为根管理员，拥有全部板块且可授权。"""
    return AdminAccessResponse(
        is_root=is_root_admin(admin),
        permissions=effective_perms(admin),
        catalog=[AdminPermItem(key=k, label=label) for k, label in PERM_CATALOG],
    )


@router.get("/users", response_model=AdminUserListResponse)
def admin_users(_: dict = Depends(require_perm("users"))) -> AdminUserListResponse:
    """用户列表（含会话数、消息数）。"""
    rows = db.query(
        """
        SELECT u.id, u.username, u.role, u.created_at, u.admin_perms,
               (SELECT COUNT(*) FROM sessions s WHERE s.user_id = u.id) AS session_count,
               (SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id
                 WHERE s.user_id = u.id) AS message_count
        FROM users u
        ORDER BY u.id
        """
    )
    return AdminUserListResponse(users=[_user_item(dict(r)) for r in rows])


@router.get("/stats", response_model=UserStatsResponse)
def admin_stats(_: dict = Depends(require_perm("stats"))) -> UserStatsResponse:
    """系统统计：用户/会话/消息/知识库。"""
    users = db.query_one("SELECT COUNT(*) AS c FROM users")
    sessions = db.query_one("SELECT COUNT(*) AS c FROM sessions")
    messages = db.query_one("SELECT COUNT(*) AS c FROM messages")
    kb = get_store().stats()
    return UserStatsResponse(
        user_count=users["c"],
        session_count=sessions["c"],
        message_count=messages["c"],
        doc_count=kb["doc_count"],
        chunk_count=kb["chunk_count"],
    )


@router.get("/status", response_model=SystemStatusResponse)
def system_status(_: dict = Depends(require_perm("status"))) -> SystemStatusResponse:
    """系统状态：模型、OCR、向量库路径、LLM 配置。"""
    from app.core.config import settings
    from app.services.embeddings import embedding_dim

    dim = 0
    try:
        dim = embedding_dim()
    except Exception:  # noqa: BLE001
        dim = 0

    return SystemStatusResponse(
        chat_model=settings.deepseek_chat_model,
        embedding_model=settings.embedding_model,
        embedding_dim=dim,
        ocr_enabled=settings.ocr_enabled,
        effective_status_enabled=settings.effective_status_enabled,
        vector_store=str(settings.vector_store_dir),
        kb_source=str(settings.kb_source_dir),
    )


@router.post("/users/{user_id}/set-role")
def set_user_role(
    user_id: int,
    role: str,
    body: SetRoleRequest | None = None,
    admin: dict = Depends(require_perm("users")),
) -> dict:
    """设置角色。把他人设为管理员并分配板块仅根管理员 tys 可以。"""
    if str(admin["id"]) == str(user_id):
        raise AppError("不能修改自己的角色", 400)
    if role not in ("admin", "user", "lawyer"):
        raise AppError("角色只能是 admin、user 或 lawyer", 400)
    target = db.query_one("SELECT username, role FROM users WHERE id = ?", (user_id,))
    if not target:
        raise AppError("用户不存在", 404)
    sole = settings.sole_admin_username
    if target["username"] == sole:
        raise AppError(f"不能修改根管理员「{sole}」的角色", 400)
    if target["role"] == "admin" and not is_root_admin(admin):
        raise AppError("只有根管理员可以调整其他管理员", 403)
    perms: list[str] = []
    if role == "admin":
        if not is_root_admin(admin):
            raise AppError("只有根管理员 tys 可以授予管理员", 403)
        perms = normalize_grant((body.permissions if body else []) or [])
        db.execute(
            "UPDATE users SET role = ?, admin_perms = ? WHERE id = ?",
            ("admin", json.dumps(perms, ensure_ascii=False), user_id),
        )
        detail = f"将用户「{target['username']}」设为管理员，权限：{', '.join(perms)}"
    else:
        db.execute(
            "UPDATE users SET role = ?, admin_perms = NULL WHERE id = ?",
            (role, user_id),
        )
        if target["role"] == "admin":
            db.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
            detail = f"撤销用户「{target['username']}」的管理员身份"
        else:
            detail = f"将用户「{target['username']}」角色设为 {role}"
    log_action(admin["id"], admin["username"], "set_role", detail)
    return {"ok": True, "permissions": perms}


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, admin: dict = Depends(require_perm("users"))) -> dict:
    """删除用户（连带会话/消息/token）。"""
    if str(admin["id"]) == str(user_id):
        raise AppError("不能删除自己", 400)
    row = db.query_one("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    if not row:
        raise AppError("用户不存在", 404)
    if row["username"] == settings.sole_admin_username:
        raise AppError(f"不能删除根管理员「{settings.sole_admin_username}」", 400)
    if row["role"] == "admin" and not is_root_admin(admin):
        raise AppError("只有根管理员可以删除其他管理员", 403)
    db.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    log_action(admin["id"], admin["username"], "delete_user",
               f"删除用户「{row['username']}」(id={user_id})")
    return {"ok": True}


# ---------- 版本快照 ----------
@router.post("/backup/create")
def backup_create(description: str = "", admin: dict = Depends(require_perm("backups"))):
    """创建版本快照。"""
    from app.services.backup import create_snapshot

    try:
        result = create_snapshot(description)
        log_action(admin["id"], admin["username"], "backup_create",
                   f"创建快照 {result['name']} ({result['size_mb']} MB)")
        return result
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"创建快照失败: {exc}", 500) from exc


@router.get("/backup/list")
def backup_list(_: dict = Depends(require_perm("backups"))):
    """列出全部快照。"""
    from app.services.backup import list_snapshots

    return {"snapshots": list_snapshots()}


@router.post("/backup/{name}/restore")
def backup_restore(name: str, admin: dict = Depends(require_perm("backups"))):
    """恢复快照。"""
    from app.services.backup import restore_snapshot

    try:
        result = restore_snapshot(name)
        log_action(admin["id"], admin["username"], "backup_restore",
                   f"恢复快照 {name}（{result['count']} 个文件）")
        return result
    except FileNotFoundError as exc:
        raise AppError(str(exc), 404) from exc
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"恢复失败: {exc}", 500) from exc


@router.delete("/backup/{name}")
def backup_delete(name: str, admin: dict = Depends(require_perm("backups"))):
    """删除快照。"""
    from app.services.backup import delete_snapshot

    ok = delete_snapshot(name)
    if not ok:
        raise AppError("快照不存在", 404)
    log_action(admin["id"], admin["username"], "backup_delete", f"删除快照 {name}")
    return {"ok": True}


# ---------- 操作日志 ----------
@router.get("/logs")
def admin_logs(limit: int = 100, _: dict = Depends(require_perm("logs"))):
    """操作日志。"""
    from app.services.audit import list_logs

    return {"logs": list_logs(min(max(limit, 1), 500))}


# ---------- 消息反馈 ----------
@router.get("/feedbacks", response_model=FeedbackAdminList)
def admin_feedbacks(
    limit: int = 100,
    rating: str | None = None,
    _: dict = Depends(require_perm("feedbacks")),
) -> FeedbackAdminList:
    """用户对助手回复的有用/无用反馈。"""
    stats = feedback_repo.feedback_stats()
    items = feedback_repo.list_feedbacks(limit=limit, rating=rating or None)
    return FeedbackAdminList(
        total=stats["total"],
        useful=stats["useful"],
        useless=stats["useless"],
        items=[FeedbackAdminItem(**x) for x in items],
    )
