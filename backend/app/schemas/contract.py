"""合同审查请求/响应。"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chat import SourceOut


class ContractReviewStatus(BaseModel):
    available: bool = True
    status: str = "active"
    message: str = "可粘贴合同摘录并生成审查备忘录草稿。"
    planned_features: list[str] = Field(default_factory=list)


class ContractFinding(BaseModel):
    clause: str = ""
    risk: str = ""
    suggestion: str = ""
    severity: str = "中"


class ContractReviewRequest(BaseModel):
    title: str = Field("", max_length=200, description="合同标题")
    text: str = Field(..., min_length=1, max_length=20000, description="合同正文摘录")
    focus: str = Field("", max_length=500, description="关注点，如违约金/解除")
    matter_id: int | None = Field(None, description="可选：关联案件工作区")


class ContractReviewOut(BaseModel):
    available: bool = True
    status: str = "active"
    blocked: bool = False
    message: str = ""
    title: str = ""
    focus: str = ""
    findings: list[Any] = Field(default_factory=list)
    markdown: str = ""
    sources: list[SourceOut] = Field(default_factory=list)
    watermark: str = "AI 生成草稿，须律师审核，不构成正式法律意见"
    disclaimer: str = ""
    record_id: int | None = None
