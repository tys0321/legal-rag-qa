"""鉴权依赖：从 Authorization header 解析当前用户。"""
from __future__ import annotations

from fastapi import Depends, Header

from app.core.errors import AppError
from app.repositories.users import get_user_by_token


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """解析 Bearer Token → 当前用户；无效则 401。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("未登录或登录已过期", 401)
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError("未登录或登录已过期", 401)
    user = get_user_by_token(token)
    if not user:
        raise AppError("登录已过期，请重新登录", 401)
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """管理员权限依赖：非 admin 返回 403。"""
    if user.get("role") != "admin":
        raise AppError("无权限访问管理后台", 403)
    return user


def optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    """可选鉴权：无 token 时返回 None（用于兼容非登录场景）。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return get_user_by_token(token) if token else None
