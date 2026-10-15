"""律师认证 / 免责确认 API。"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.auth import get_current_user, require_admin
from app.core.config import PROJECT_ROOT
from app.core.errors import AppError
from app.repositories import lawyers as lawyer_repo
from app.schemas.lawyer import (
    DisclaimerAckOut,
    DisclaimerStatusOut,
    LawyerApplyRequest,
    LawyerProfileOut,
    LawyerReviewRequest,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api", tags=["lawyer"])

CERT_DIR = PROJECT_ROOT / "data" / "lawyer_certs"


def _to_out(user_id: int, profile: dict | None, *, is_admin: bool = False) -> LawyerProfileOut:
    if is_admin:
        return LawyerProfileOut(
            user_id=user_id,
            license_no=((profile or {}).get("license_no") or "ADMIN"),
            region=((profile or {}).get("region") or "全域"),
            specialties=list((profile or {}).get("specialties") or ["全部场景"]),
            license_files=list((profile or {}).get("license_files") or []),
            status="approved",
            reject_reason="",
            access="approved",
        )
    if not profile:
        return LawyerProfileOut(user_id=user_id, status="none", access="none")
    return LawyerProfileOut(
        user_id=user_id,
        license_no=profile.get("license_no") or "",
        region=profile.get("region") or "",
        specialties=list(profile.get("specialties") or []),
        license_files=list(profile.get("license_files") or []),
        status=profile.get("status") or "none",
        reject_reason=profile.get("reject_reason") or "",
        access=lawyer_repo.lawyer_mode_access(user_id),
    )


@router.get("/lawyer/status", response_model=LawyerProfileOut)
def lawyer_status(user: dict = Depends(get_current_user)) -> LawyerProfileOut:
    return _to_out(
        user["id"],
        lawyer_repo.get_profile(user["id"]),
        is_admin=user.get("role") == "admin",
    )


@router.post("/lawyer/apply", response_model=LawyerProfileOut)
async def lawyer_apply(
    license_no: str = Form(...),
    region: str = Form(...),
    specialties: str = Form("[]"),
    files: list[UploadFile] = File(default=[]),
    user: dict = Depends(get_current_user),
) -> LawyerProfileOut:
    """提交执业证材料（multipart）。specialties 为 JSON 数组字符串。"""
    import json

    try:
        specs = json.loads(specialties) if specialties else []
        if not isinstance(specs, list):
            specs = []
    except json.JSONDecodeError:
        specs = [s.strip() for s in specialties.split(",") if s.strip()]

    if not license_no.strip() or not region.strip():
        raise AppError("执业证号与地区不能为空", 400)

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for f in files or []:
        if not f.filename:
            continue
        suffix = Path(f.filename).suffix.lower() or ".bin"
        if suffix not in {".jpg", ".jpeg", ".png", ".pdf", ".webp"}:
            raise AppError(f"不支持的文件类型: {suffix}", 400)
        name = f"{user['id']}_{uuid.uuid4().hex[:10]}{suffix}"
        dest = CERT_DIR / name
        content = await f.read()
        if len(content) > 8 * 1024 * 1024:
            raise AppError("单个文件不能超过 8MB", 400)
        dest.write_bytes(content)
        saved.append(name)

    try:
        profile = lawyer_repo.upsert_application(
            user["id"],
            license_no=license_no,
            region=region,
            specialties=[str(x) for x in specs][:12],
            license_files=saved,
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc

    log_action(user["id"], user["username"], "lawyer_apply", license_no)
    return _to_out(user["id"], profile)


@router.post("/lawyer/apply/json", response_model=LawyerProfileOut)
def lawyer_apply_json(
    req: LawyerApplyRequest,
    user: dict = Depends(get_current_user),
) -> LawyerProfileOut:
    """无文件演示用 JSON 申请（仍进入 pending）。"""
    try:
        profile = lawyer_repo.upsert_application(
            user["id"],
            license_no=req.license_no,
            region=req.region,
            specialties=req.specialties[:12],
            license_files=[],
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(user["id"], user["username"], "lawyer_apply_json", req.license_no)
    return _to_out(user["id"], profile)


@router.get("/admin/lawyer/pending")
def admin_pending(_: dict = Depends(require_admin)) -> dict:
    return {"items": lawyer_repo.list_pending()}


@router.post("/admin/lawyer/{user_id}/review", response_model=LawyerProfileOut)
def admin_review(
    user_id: int,
    req: LawyerReviewRequest,
    admin: dict = Depends(require_admin),
) -> LawyerProfileOut:
    profile = lawyer_repo.review(
        user_id, approve=req.approve, reviewer_id=admin["id"], reason=req.reason
    )
    if not profile:
        raise AppError("未找到该律师申请", 404)
    log_action(
        admin["id"],
        admin["username"],
        "lawyer_review",
        f"user={user_id} approve={req.approve}",
    )
    return _to_out(user_id, profile)


@router.get("/disclaimer/status", response_model=DisclaimerStatusOut)
def disclaimer_status(user: dict = Depends(get_current_user)) -> DisclaimerStatusOut:
    return DisclaimerStatusOut(acked=lawyer_repo.has_disclaimer_ack(user["id"]))


@router.post("/disclaimer/ack", response_model=DisclaimerAckOut)
def disclaimer_ack(user: dict = Depends(get_current_user)) -> DisclaimerAckOut:
    lawyer_repo.ack_disclaimer(user["id"])
    return DisclaimerAckOut(ok=True)
