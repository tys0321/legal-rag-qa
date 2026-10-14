"""案源广场 API：发布 → 匹配列表 → 认领 → 模拟中间号/站内信。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories import lawyers as lawyer_repo
from app.repositories import leads as lead_repo
from app.schemas.lead import (
    LeadContactRequest,
    LeadCreateRequest,
    LeadEventOut,
    LeadListOut,
    LeadOut,
    LeadStatusRequest,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api", tags=["leads"])


def _to_out(lead: dict, *, with_events: bool = False) -> LeadOut:
    events: list[LeadEventOut] = []
    if with_events:
        for e in lead_repo.list_events(lead["id"]):
            events.append(
                LeadEventOut(
                    id=e["id"],
                    lead_id=e["lead_id"],
                    actor_id=e.get("actor_id"),
                    event_type=e.get("event_type") or "",
                    detail=e.get("detail") or "",
                    created_at=str(e.get("created_at") or ""),
                )
            )
    return LeadOut(
        id=lead["id"],
        user_id=lead["user_id"],
        scene=lead.get("scene") or "",
        region=lead.get("region") or "",
        title=lead.get("title") or "",
        summary=lead.get("summary") or "",
        status=lead.get("status") or "",
        claimed_by=lead.get("claimed_by"),
        firm_visible=bool(lead.get("firm_visible")),
        contact_masked=lead.get("contact_masked") or "",
        allow_push=bool(lead.get("allow_push", True)),
        match_score=float(lead.get("match_score") or 0),
        virtual_number=lead.get("virtual_number") or "",
        created_at=str(lead.get("created_at") or ""),
        updated_at=str(lead.get("updated_at") or ""),
        events=events,
    )


@router.post("/leads", response_model=LeadOut)
def create_lead(req: LeadCreateRequest, user: dict = Depends(get_current_user)) -> LeadOut:
    try:
        lead = lead_repo.create_lead(
            user["id"],
            title=req.title,
            summary=req.summary,
            scene=req.scene,
            region=req.region,
            contact=req.contact,
            allow_push=req.allow_push,
            firm_visible=req.firm_visible,
            publish=req.publish,
        )
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(user["id"], user["username"], "lead_create", f"id={lead['id']} scene={req.scene}")
    return _to_out(lead, with_events=True)


@router.get("/leads", response_model=LeadListOut)
def list_leads(
    scope: str = Query("auto", description="auto|mine|plaza"),
    scene: str | None = Query(None),
    region: str | None = Query(None),
    user: dict = Depends(get_current_user),
) -> LeadListOut:
    """
    - mine：我发布的
    - plaza：广场开放案源（律师匹配排序；pending 只读）
    - auto：律师端默认 plaza，用户端默认 mine
    """
    access = lawyer_repo.lawyer_mode_access(user["id"])
    if scope == "auto":
        scope = "plaza" if access in {"approved", "pending_readonly"} else "mine"

    if scope == "mine":
        items = lead_repo.list_for_user(user["id"])
    elif scope == "plaza":
        if access == "approved":
            items = lead_repo.list_for_lawyer(user["id"], scene=scene, region=region)
        elif access == "pending_readonly":
            profile = lawyer_repo.get_profile(user["id"]) or {}
            items = lead_repo.list_open_plaza(
                scene=scene,
                region=region,
                viewer_specialties=list(profile.get("specialties") or []),
                viewer_region=profile.get("region") or "",
            )
        else:
            # 普通用户也可浏览广场（只读开放案源，无匹配分）
            items = lead_repo.list_open_plaza(scene=scene, region=region)
    else:
        raise AppError("scope 须为 auto|mine|plaza", 400)

    return LeadListOut(items=[_to_out(x) for x in items])


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, user: dict = Depends(get_current_user)) -> LeadOut:
    lead = lead_repo.get_lead(lead_id)
    if not lead:
        raise AppError("案源不存在", 404)
    if not lead_repo.can_view_lead(user, lead):
        raise AppError("无权查看该案源", 403)
    # 补充匹配分（律师视角）
    profile = lawyer_repo.get_profile(user["id"])
    if profile and profile.get("status") in {"approved", "pending"}:
        lead["match_score"] = lead_repo.match_score(
            lead, list(profile.get("specialties") or []), profile.get("region") or ""
        )
    return _to_out(lead, with_events=True)


@router.post("/leads/{lead_id}/claim", response_model=LeadOut)
def claim_lead(lead_id: int, user: dict = Depends(get_current_user)) -> LeadOut:
    try:
        lead = lead_repo.claim_lead(lead_id, user["id"])
    except LookupError as exc:
        raise AppError(str(exc), 404) from exc
    except PermissionError as exc:
        raise AppError(str(exc), 403) from exc
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(user["id"], user["username"], "lead_claim", f"id={lead_id}")
    return _to_out(lead, with_events=True)


@router.post("/leads/{lead_id}/contact", response_model=LeadOut)
def contact_lead(
    lead_id: int,
    req: LeadContactRequest,
    user: dict = Depends(get_current_user),
) -> LeadOut:
    try:
        lead = lead_repo.contact_lead(
            lead_id, user["id"], channel=req.channel, message=req.message
        )
    except LookupError as exc:
        raise AppError(str(exc), 404) from exc
    except PermissionError as exc:
        raise AppError(str(exc), 403) from exc
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(
        user["id"],
        user["username"],
        "lead_contact",
        f"id={lead_id} channel={req.channel}",
    )
    return _to_out(lead, with_events=True)


@router.post("/leads/{lead_id}/status", response_model=LeadOut)
def update_status(
    lead_id: int,
    req: LeadStatusRequest,
    user: dict = Depends(get_current_user),
) -> LeadOut:
    as_admin = user.get("role") == "admin"
    try:
        lead = lead_repo.set_status(lead_id, user["id"], req.status, as_admin=as_admin)
    except LookupError as exc:
        raise AppError(str(exc), 404) from exc
    except PermissionError as exc:
        raise AppError(str(exc), 403) from exc
    except ValueError as exc:
        raise AppError(str(exc), 400) from exc
    log_action(
        user["id"],
        user["username"],
        "lead_status",
        f"id={lead_id} -> {req.status}",
    )
    return _to_out(lead, with_events=True)
