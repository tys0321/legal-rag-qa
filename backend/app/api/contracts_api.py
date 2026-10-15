"""合同审查 API（P2 占位：导航 + 预留接口，本期不实现审查逻辑）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.schemas.contract import ContractReviewOut, ContractReviewRequest, ContractReviewStatus
from app.services.audit import log_action

router = APIRouter(prefix="/api", tags=["contracts"])

_PLANNED = [
    "条款风险点标注（违约金、解除、管辖等）",
    "与知识库法规条款对照提示",
    "生成审查备忘录草稿（须律师审核）",
]

_MSG = "合同审查为 P2 规划能力，当前仅导航占位与接口预留，尚未开放。"


@router.get("/contracts/review/status", response_model=ContractReviewStatus)
def contract_review_status(_user: dict = Depends(get_current_user)) -> ContractReviewStatus:
    return ContractReviewStatus(
        available=False,
        status="coming_soon",
        message=_MSG,
        planned_features=_PLANNED,
    )


@router.post("/contracts/review", response_model=ContractReviewOut)
def contract_review(
    req: ContractReviewRequest,
    user: dict = Depends(get_current_user),
) -> ContractReviewOut:
    log_action(
        user["id"],
        user["username"],
        "contract_review_blocked",
        f"title={req.title[:40]} len={len(req.text)}",
    )
    # 明确未实现：便于联调区分「占位」与「可用」
    raise AppError(_MSG, 501)
