"""认证 API：注册 / 登录 / 登出 / 当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories import firms as firm_repo
from app.repositories import lawyers as lawyer_repo
from app.repositories import users as user_repo
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest) -> AuthResponse:
    try:
        user = user_repo.create_user(req.username, req.password)
    except user_repo.UserError as exc:
        raise AppError(exc.message, 400) from exc
    if not user:
        raise AppError("用户名已存在", 409)
    token = user_repo.issue_token(user["id"])
    return AuthResponse(
        token=token,
        username=user["username"],
        user_id=user["id"],
        role=user.get("role", "user"),
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest) -> AuthResponse:
    user = user_repo.get_user_by_username(req.username)
    if not user or not user_repo.verify_password(user, req.password):
        raise AppError("用户名或密码错误", 401)
    token = user_repo.issue_token(user["id"])
    return AuthResponse(
        token=token,
        username=user["username"],
        user_id=user["id"],
        role=user.get("role", "user"),
    )


@router.post("/logout", response_model=dict)
def logout(authorization: str | None = None):
    if authorization and authorization.lower().startswith("bearer "):
        user_repo.revoke_token(authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)) -> UserOut:
    profile = lawyer_repo.get_profile(user["id"])
    membership = firm_repo.get_membership(user["id"])
    return UserOut(
        id=user["id"],
        username=user["username"],
        created_at=user["created_at"],
        role=user.get("role", "user"),
        lawyer_access=lawyer_repo.lawyer_mode_access(user["id"]),
        lawyer_status=(profile or {}).get("status") or "none",
        disclaimer_acked=lawyer_repo.has_disclaimer_ack(user["id"]),
        firm_id=int(membership["firm_id"]) if membership else None,
        firm_name=(membership.get("firm_name") or "") if membership else "",
        firm_role=(membership.get("role") or "") if membership else "",
    )
