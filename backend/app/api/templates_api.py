"""文书模板 API：列表 / 详情 / 填充。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.schemas.template import (
    TemplateDetail,
    TemplateFillOut,
    TemplateFillRequest,
    TemplateListOut,
    TemplateSummary,
)
from app.services.audit import log_action
from app.services import templates as tpl

router = APIRouter(prefix="/api", tags=["templates"])


@router.get("/templates", response_model=TemplateListOut)
def list_document_templates(_user: dict = Depends(get_current_user)) -> TemplateListOut:
    data = tpl.list_templates()
    return TemplateListOut(
        version=data["version"],
        total=data["total"],
        watermark=data["watermark"],
        items=[TemplateSummary(**x) for x in data["items"]],
    )


@router.get("/templates/{template_id}", response_model=TemplateDetail)
def get_document_template(
    template_id: str,
    _user: dict = Depends(get_current_user),
) -> TemplateDetail:
    data = tpl.get_template_detail(template_id)
    return TemplateDetail(**data)


@router.post("/templates/{template_id}", response_model=TemplateFillOut)
def fill_document_template(
    template_id: str,
    req: TemplateFillRequest,
    user: dict = Depends(get_current_user),
) -> TemplateFillOut:
    result = tpl.fill_template(template_id, req.fields)
    log_action(
        user["id"],
        user["username"],
        "template_fill",
        f"id={template_id} missing={len(result['missing_required'])}",
    )
    return TemplateFillOut(**result)
