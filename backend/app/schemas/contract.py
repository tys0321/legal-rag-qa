"""合同审查（P2 占位）请求/响应。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ContractReviewStatus(BaseModel):
    available: bool = False
    status: str = "coming_soon"
    message: str = "合同审查为 P2 规划能力，当前仅导航占位与接口预留，尚未开放。"
    planned_features: list[str] = Field(default_factory=list)


class ContractReviewRequest(BaseModel):
    title: str = Field("", max_length=200, description="合同标题（预留）")
    text: str = Field(..., min_length=1, max_length=20000, description="合同正文摘录（预留）")
    focus: str = Field("", max_length=500, description="关注点，如违约金/解除（预留）")


class ContractReviewOut(BaseModel):
    available: bool = False
    status: str = "coming_soon"
    message: str = ""
    title: str = ""
    focus: str = ""
    findings: list[str] = Field(default_factory=list)
