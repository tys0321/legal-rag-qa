"""罪名构成要件 API。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories import matters as matters_repo
from app.schemas.elements import (
    ChargeOut,
    ChargeSummary,
    ElementItem,
    ElementsCheckOut,
    ElementsCheckRequest,
)
from app.services import elements as svc

router = APIRouter(prefix="/api", tags=["elements"])


def _charge_out(info: dict, key: str = "") -> ChargeOut:
    elements = info.get("elements") or []
    items = []
    for e in elements:
        items.append(
            ElementItem(
                id=str(e.get("id") or ""),
                label=str(e.get("label") or ""),
                desc=str(e.get("desc") or ""),
                group=str(e.get("group") or "构成要件"),
                evidence=str(e.get("evidence") or ""),
            )
        )
    result = svc.check_elements(key or info.get("charge") or "", [])
    return ChargeOut(
        charge=info.get("charge") or key,
        article_hint=info.get("article_hint") or "",
        category=info.get("category") or "",
        compare=list(info.get("compare") or []),
        elements=items,
        groups=result.get("groups") or [],
    )


@router.get("/elements/charges")
def list_charges(_user: dict = Depends(get_current_user)) -> dict:
    items = [ChargeSummary(**c) for c in svc.list_charges()]
    cats = sorted({c.category for c in items if c.category})
    return {"items": [c.model_dump() for c in items], "categories": cats, "total": len(items)}


@router.get("/elements/{charge}", response_model=ChargeOut)
def get_charge(charge: str, _user: dict = Depends(get_current_user)) -> ChargeOut:
    info = svc.get_charge(charge)
    if not info:
        raise AppError("未收录该罪名要件", 404)
    return _charge_out(info, charge)


@router.post("/elements/check", response_model=ElementsCheckOut)
def check_elements(
    body: ElementsCheckRequest,
    user: dict = Depends(get_current_user),
) -> ElementsCheckOut:
    result = svc.check_elements(body.charge, body.checked_ids, body.notes)
    artifact_id = None
    if body.matter_id:
        art = matters_repo.add_artifact(
            int(user["id"]),
            body.matter_id,
            kind="elements",
            title=f"要件勾选·{result.get('charge')}",
            payload=result,
        )
        if art:
            artifact_id = int(art["id"])
    return ElementsCheckOut(
        charge=result.get("charge") or body.charge,
        article_hint=result.get("article_hint") or "",
        category=result.get("category") or "",
        compare=result.get("compare") or [],
        found=bool(result.get("found")),
        elements=result.get("elements") or [],
        groups=result.get("groups") or [],
        missing=result.get("missing") or [],
        checked_ids=result.get("checked_ids") or [],
        supplement_text=result.get("supplement_text") or "",
        artifact_id=artifact_id,
    )
