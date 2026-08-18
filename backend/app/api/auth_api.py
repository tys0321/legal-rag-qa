"""认证 API：注册 / 登录 / 登出 / 当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
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
    return UserOut(
        id=user["id"],
        username=user["username"],
        created_at=user["created_at"],
        role=user.get("role", "user"),
    )
