"""合同审查：检索对照 + 备忘录草稿。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.schemas.contract import ContractReviewOut, ContractReviewRequest, ContractReviewStatus
from app.services.audit import log_action
from app.services.contract_review import review_contract
from app.services.matters import link_record
from app.services.user_records import save_record

router = APIRouter(prefix="/api", tags=["contracts"])

_FEATURES = [
    "条款级风险批注（条款 / 风险 / 建议 / 等级）",
    "与知识库法规条款对照提示",
    "生成审查备忘录草稿（须律师审核）",
    "可关联案件工作区",
]


@router.get("/contracts/review/status", response_model=ContractReviewStatus)
def contract_review_status(_user: dict = Depends(get_current_user)) -> ContractReviewStatus:
    return ContractReviewStatus(
        available=True,
        status="active",
        message="可粘贴合同摘录并生成审查备忘录草稿。结论须律师审核，不构成正式法律意见。",
        planned_features=_FEATURES,
    )


@router.post("/contracts/review", response_model=ContractReviewOut)
def contract_review(
    req: ContractReviewRequest,
    user: dict = Depends(get_current_user),
) -> ContractReviewOut:
    result = review_contract(title=req.title, text=req.text, focus=req.focus)
    log_action(
        user["id"],
        user["username"],
        "contract_review",
        f"title={req.title[:40]} len={len(req.text)} findings={len(result.get('findings') or [])}",
    )
    rid = save_record(
        int(user["id"]),
        "contract",
        (req.title or "合同审查")[:200],
        f"{len(result.get('findings') or [])} 条风险点",
        result,
    )
    result["record_id"] = rid
    if req.matter_id and rid and not result.get("blocked"):
        link_record(
            int(user["id"]),
            req.matter_id,
            rid,
            kind="contract",
            title=(req.title or "合同审查")[:200],
        )
    return ContractReviewOut(**result)
