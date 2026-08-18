"""会话管理请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SessionItem(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    msg_count: int = 0


class SessionListResponse(BaseModel):
    sessions: list[SessionItem]
    messages: list[dict] = []
    title: str = ""


class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=50)


class SessionRenameResponse(BaseModel):
    ok: bool = True


class SessionDeleteResponse(BaseModel):
    ok: bool = True


class SessionBatchDeleteRequest(BaseModel):
    session_ids: list[str] = Field(..., min_length=1, max_length=200)


class SessionBatchDeleteResponse(BaseModel):
    ok: bool = True
    removed: int = 0
