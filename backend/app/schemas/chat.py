"""对话相关请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户提问")
    session_id: str | None = Field(None, description="会话 ID，缺省则新建会话")
    scene: str | None = Field(None, description="可选场景标签")
    skip_slots: bool = Field(False, description="跳过槽位追问，直接回答")


class SourceOut(BaseModel):
    id: str
    doc_id: str
    title: str
    category: str
    article: str = ""
    page: int = 0
    text: str
    score: float
    match: str | None = None
    effective_status: str = ""
    effective_detail: str = ""


class CaseOut(BaseModel):
    id: str
    doc_id: str
    title: str
    category: str
    text: str
    score: float


class SlotNeedOut(BaseModel):
    key: str
    prompt: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    mode: str  # fast | slow | slot | risk_block
    sources: list[SourceOut] = []
    disclaimer: str
    routed_reason: str
    related_cases: list[CaseOut] = []
    confidence: str = "medium"  # high | medium | low
    critic_issues: list[str] = []
    risk_level: str = "L3"
    risk_banner: str = ""
    force_lawyer_cta: bool = False
    scene: str = ""
    need_slots: list[SlotNeedOut] = []
    waiting_for_slot: bool = False


class ClearSessionRequest(BaseModel):
    session_id: str


class ClearSessionResponse(BaseModel):
    ok: bool = True
