"""案源广场请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LeadCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    summary: str = Field(..., min_length=4, max_length=4000)
    scene: str = Field(..., min_length=2, max_length=64)
    region: str = Field(..., min_length=2, max_length=64)
    contact: str = Field(..., min_length=5, max_length=64, description="联系方式，服务端脱敏存储")
    allow_push: bool = True
    firm_visible: bool = False
    publish: bool = Field(True, description="True→open；False→draft")


class LeadStatusRequest(BaseModel):
    status: str = Field(..., description="目标状态：open/claimed/in_contact/closed/cancelled")


class LeadContactRequest(BaseModel):
    channel: str = Field("inbox", description="inbox|virtual_number")
    message: str = Field("", max_length=2000)


class LeadEventOut(BaseModel):
    id: int
    lead_id: int
    actor_id: int | None = None
    event_type: str
    detail: str = ""
    created_at: str = ""


class LeadOut(BaseModel):
    id: int
    user_id: int
    scene: str
    region: str
    title: str
    summary: str
    status: str
    claimed_by: int | None = None
    firm_visible: bool = False
    contact_masked: str = ""
    allow_push: bool = True
    match_score: float = 0.0
    virtual_number: str = ""
    created_at: str = ""
    updated_at: str = ""
    events: list[LeadEventOut] = Field(default_factory=list)


class LeadListOut(BaseModel):
    items: list[LeadOut]
