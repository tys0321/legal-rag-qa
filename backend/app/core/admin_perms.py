"""管理员权限：tys 为根管理员，可把他人设为管理员并分配后台板块。"""
from __future__ import annotations

import json
from collections.abc import Callable

from fastapi import Depends

from app.core.auth import require_admin
from app.core.config import settings
from app.core.errors import AppError

# 可分配给次级管理员的后台板块（授予管理员本身不在此列，仅 tys 可做）
PERM_CATALOG: list[tuple[str, str]] = [
    ("users", "用户管理"),
    ("kb", "知识库"),
    ("lawyers", "律师审核"),
    ("feedbacks", "消息反馈"),
    ("stats", "系统统计"),
    ("status", "系统状态"),
    ("backups", "数据备份"),
    ("logs", "操作日志"),
]
PERM_KEYS = {k for k, _ in PERM_CATALOG}


def is_root_admin(user: dict | None) -> bool:
    if not user or user.get("role") != "admin":
        return False
    return (user.get("username") or "") == settings.sole_admin_username


def parse_perms(raw: object) -> list[str]:
    if not raw:
        return []
    data = raw
    if isinstance(raw, (bytes, str)):
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return []
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        key = str(item)
        if key in PERM_KEYS and key not in out:
            out.append(key)
    return out


def effective_perms(user: dict | None) -> list[str]:
    if not user or user.get("role") != "admin":
        return []
    if is_root_admin(user):
        return [k for k, _ in PERM_CATALOG]
    return parse_perms(user.get("admin_perms"))


def has_perm(user: dict | None, perm: str) -> bool:
    return perm in effective_perms(user)


def require_perm(perm: str) -> Callable:
    """次级管理员必须拥有对应板块；tys 始终通过。"""

    def _dep(user: dict = Depends(require_admin)) -> dict:
        if not has_perm(user, perm):
            raise AppError("没有该管理权限", 403)
        return user

    return _dep


def normalize_grant(permissions: list[str]) -> list[str]:
    unknown = [p for p in permissions if p not in PERM_KEYS]
    if unknown:
        raise AppError(f"未知权限：{', '.join(unknown)}", 400)
    picked = [k for k, _ in PERM_CATALOG if k in permissions]
    if not picked:
        raise AppError("请至少选择一项权限", 400)
    return picked
