"""管理后台 API（仅 admin 可访问）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import require_admin
from app.core.errors import AppError
from app.repositories import database as db
from app.repositories import users as user_repo
from app.repositories.vector_store import get_store
from app.schemas.admin import (
    AdminUserItem,
    AdminUserListResponse,
    SystemStatusResponse,
    UserStatsResponse,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=AdminUserListResponse)
def admin_users(_: dict = Depends(require_admin)) -> AdminUserListResponse:
    """用户列表（含会话数、消息数）。"""
    rows = db.query(
        """
        SELECT u.id, u.username, u.role, u.created_at,
               (SELECT COUNT(*) FROM sessions s WHERE s.user_id = u.id) AS session_count,
               (SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.id
                 WHERE s.user_id = u.id) AS message_count
        FROM users u
        ORDER BY u.id
        """
    )
    return AdminUserListResponse(users=[AdminUserItem(**dict(r)) for r in rows])


@router.get("/stats", response_model=UserStatsResponse)
def admin_stats(_: dict = Depends(require_admin)) -> UserStatsResponse:
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
def system_status(_: dict = Depends(require_admin)) -> SystemStatusResponse:
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
def set_user_role(user_id: int, role: str, admin: dict = Depends(require_admin)) -> dict:
    """设置用户角色（admin/user）。"""
    if str(admin["id"]) == str(user_id):
        raise AppError("不能修改自己的角色", 400)
    if role not in ("admin", "user"):
        raise AppError("角色只能是 admin 或 user", 400)
    target = db.query_one("SELECT username FROM users WHERE id = ?", (user_id,))
    if not target:
        raise AppError("用户不存在", 404)
    cur = db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    if cur.rowcount == 0:
        raise AppError("用户不存在", 404)
    log_action(admin["id"], admin["username"], "set_role",
               f"将用户「{target['username']}」角色设为 {role}")
    return {"ok": True}


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, admin: dict = Depends(require_admin)) -> dict:
    """删除用户（连带会话/消息/token）。"""
    if str(admin["id"]) == str(user_id):
        raise AppError("不能删除自己", 400)
    row = db.query_one("SELECT id, username FROM users WHERE id = ?", (user_id,))
    if not row:
        raise AppError("用户不存在", 404)
    db.execute("DELETE FROM tokens WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    log_action(admin["id"], admin["username"], "delete_user",
               f"删除用户「{row['username']}」(id={user_id})")
    return {"ok": True}


# ---------- 版本快照 ----------
@router.post("/backup/create")
def backup_create(description: str = "", admin: dict = Depends(require_admin)):
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
def backup_list(_: dict = Depends(require_admin)):
    """列出全部快照。"""
    from app.services.backup import list_snapshots

    return {"snapshots": list_snapshots()}


@router.post("/backup/{name}/restore")
def backup_restore(name: str, admin: dict = Depends(require_admin)):
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
def backup_delete(name: str, admin: dict = Depends(require_admin)):
    """删除快照。"""
    from app.services.backup import delete_snapshot

    ok = delete_snapshot(name)
    if not ok:
        raise AppError("快照不存在", 404)
    log_action(admin["id"], admin["username"], "backup_delete", f"删除快照 {name}")
    return {"ok": True}


# ---------- 操作日志 ----------
@router.get("/logs")
def admin_logs(limit: int = 100, _: dict = Depends(require_admin)):
    """操作日志。"""
    from app.services.audit import list_logs

    return {"logs": list_logs(min(max(limit, 1), 500))}
