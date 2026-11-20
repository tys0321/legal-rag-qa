"""法律意见书请求/响应。"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.chat import SourceOut


class OpinionRequest(BaseModel):
    fact_summary: str = Field(..., min_length=4, max_length=12000, description="案情摘要")
    scene: str = Field("", max_length=64, description="可选场景标签")
    question: str = Field("", max_length=1000, description="用户核心诉求，可空")
    slot_answers: dict[str, str] = Field(default_factory=dict)
    mode: str = Field(
        "lawyer",
        max_length=32,
        description="lawyer=意见书 / judge=裁判说理 / prosecutor=审查报告",
    )
    matter_id: int | None = Field(None, description="可选：关联案件工作区")


class OpinionOut(BaseModel):
    scene: str = ""
    risk_level: str = "L3"
    blocked: bool = False
    title: str = "法律意见书（AI 草稿）"
    mode: str = "lawyer"
    sections: dict[str, str] = Field(
        default_factory=dict,
        description="按 mode 解析的各节内容",
    )
    markdown: str = ""
    sources: list[SourceOut] = Field(default_factory=list)
    confidence: str = "medium"
    watermark: str = "AI 生成草稿，须律师审核，不构成正式法律意见"
    disclaimer: str = ""
    record_id: int | None = None
