"""操作日志：记录管理后台的关键操作（登录、删用户、改角色、快照等）。"""
from __future__ import annotations

from app.repositories import database as db


def log_action(actor_id: int | None, actor_name: str, action: str, detail: str = "") -> None:
    """记录一条操作日志。"""
    db.execute(
        "INSERT INTO admin_logs (actor_id, actor_name, action, detail) VALUES (?, ?, ?, ?)",
        (actor_id, actor_name, action, detail),
    )


def list_logs(limit: int = 100) -> list[dict]:
    rows = db.query(
        "SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in rows]
