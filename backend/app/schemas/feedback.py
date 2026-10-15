"""管理端反馈列表。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class FeedbackAdminItem(BaseModel):
    id: int
    message_id: int
    user_id: int
    username: str = ""
    rating: str
    comment: str = ""
    created_at: str = ""
    message_preview: str = ""
    session_id: str = ""


class FeedbackAdminList(BaseModel):
    total: int = 0
    useful: int = 0
    useless: int = 0
    items: list[FeedbackAdminItem] = Field(default_factory=list)
