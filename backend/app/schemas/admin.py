"""管理后台请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: int
    username: str
    role: str
    created_at: str
    session_count: int = 0
    message_count: int = 0


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]


class UserStatsResponse(BaseModel):
    user_count: int
    session_count: int
    message_count: int
    doc_count: int
    chunk_count: int


class SystemStatusResponse(BaseModel):
    chat_model: str
    embedding_model: str
    embedding_dim: int
    ocr_enabled: bool
    effective_status_enabled: bool
    vector_store: str
    kb_source: str
