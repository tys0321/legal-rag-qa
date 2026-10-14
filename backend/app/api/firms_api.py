"""轻量律所 API：创建 / 查看 / 邀请成员。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories import firms as firm_repo
from app.repositories import lawyers as lawyer_repo
from app.schemas.firm import (
    FirmCreateRequest,
    FirmInviteOut,
    FirmInviteRequest,
    FirmMemberOut,
    FirmOut,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api", tags=["firms"])


def _to_out(firm_id: int) -> FirmOut:
    detail = firm_repo.firm_detail(firm_id)
    if not detail:
        raise AppError("律所不存在", 404)
    members = [
        FirmMemberOut(
            firm_id=m["firm_id"],
            user_id=m["user_id"],
            username=m.get("username") or "",
            role=m.get("role") or "member",
            joined_at=str(m.get("joined_at") or ""),
        )
        for m in detail.get("members") or []
    ]
    return FirmOut(
        id=detail["id"],
        name=detail["name"],
        owner_user_id=detail["owner_user_id"],
        created_at=str(detail.get("created_at") or ""),
        members=members,
    )


@router.post("/firms", response_model=FirmOut)
def create_firm(req: FirmCreateRequest, user: dict = Depends(get_current_user)) -> FirmOut:
    """已认证律师可创建律所（MVP 轻量：一人一所）。"""
    if not lawyer_repo.can_use_lawyer_write(user["id"]):
        raise AppError("仅已认证律师可创建律所", 403)
    try:
        firm = firm_repo.create_firm(user["id"], req.name)
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(user["id"], user["username"], "firm_create", f"id={firm['id']} name={req.name}")
    return _to_out(firm["id"])


@router.get("/firms/me", response_model=FirmOut)
def my_firm(user: dict = Depends(get_current_user)) -> FirmOut:
    membership = firm_repo.get_membership(user["id"])
    if not membership:
        raise AppError("尚未加入律所", 404)
    return _to_out(int(membership["firm_id"]))


@router.get("/firms/{firm_id}", response_model=FirmOut)
def get_firm(firm_id: int, user: dict = Depends(get_current_user)) -> FirmOut:
    membership = firm_repo.get_membership(user["id"])
    if user.get("role") != "admin":
        if not membership or int(membership["firm_id"]) != firm_id:
            raise AppError("无权查看该律所", 403)
    return _to_out(firm_id)


@router.post("/firms/{firm_id}/members", response_model=FirmInviteOut)
def invite_member(
    firm_id: int,
    req: FirmInviteRequest,
    user: dict = Depends(get_current_user),
) -> FirmInviteOut:
    try:
        invited = firm_repo.invite_member(firm_id, user["id"], req.username)
    except LookupError as exc:
        raise AppError(str(exc), 404) from exc
    except PermissionError as exc:
        raise AppError(str(exc), 403) from exc
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(
        user["id"],
        user["username"],
        "firm_invite",
        f"firm={firm_id} user={invited['username']}",
    )
    return FirmInviteOut(**invited)
