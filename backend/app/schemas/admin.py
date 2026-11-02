"""管理后台请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel


class AdminPermItem(BaseModel):
    key: str
    label: str


class AdminAccessResponse(BaseModel):
    is_root: bool
    permissions: list[str]
    catalog: list[AdminPermItem]


class SetRoleRequest(BaseModel):
    permissions: list[str] = []


class AdminUserItem(BaseModel):
    id: int
    username: str
    role: str
    created_at: str
    session_count: int = 0
    message_count: int = 0
    permissions: list[str] = []
    is_root: bool = False


class AdminUserListResponse(BaseModel):
    users: list[AdminUserItem]


class UserStatsResponse(BaseModel):
    user_count: int
    session_count: int
    message_count: int
    doc_count: int
    chunk_count: int


class DayCount(BaseModel):
    date: str
    count: int


class RoleCount(BaseModel):
    role: str
    count: int


class CategoryCount(BaseModel):
    name: str
    docs: int
    chunks: int


class DashboardSummary(BaseModel):
    user_count: int
    session_count: int
    message_count: int
    doc_count: int
    chunk_count: int
    lawyer_pending: int = 0
    lawyer_approved: int = 0
    feedback_total: int = 0
    feedback_useful: int = 0
    feedback_useless: int = 0
    useful_rate: float | None = None
    avg_messages_per_session: float = 0


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    roles: list[RoleCount] = []
    daily_messages: list[DayCount] = []
    daily_sessions: list[DayCount] = []
    daily_new_users: list[DayCount] = []
    kb_categories: list[CategoryCount] = []


class SystemStatusResponse(BaseModel):
    chat_model: str
    embedding_model: str
    embedding_dim: int
    ocr_enabled: bool
    effective_status_enabled: bool
    vector_store: str
    kb_source: str
