"""会话管理 API：列表 / 详情 / 删除 / 批量删除 / 改名。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories.sessions import get_session_store
from app.schemas.session import (
    SessionBatchDeleteRequest,
    SessionBatchDeleteResponse,
    SessionDeleteResponse,
    SessionItem,
    SessionListResponse,
    SessionRenameRequest,
    SessionRenameResponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(user: dict = Depends(get_current_user)) -> SessionListResponse:
    items = get_session_store().list_sessions(user["id"])
    return SessionListResponse(sessions=[SessionItem(**i) for i in items])


# 批量删除必须定义在 /sessions/{session_id} 之前，避免被路径参数捕获
@router.post("/sessions/batch-delete", response_model=SessionBatchDeleteResponse)
def batch_delete_sessions(
    req: SessionBatchDeleteRequest, user: dict = Depends(get_current_user)
) -> SessionBatchDeleteResponse:
    """批量删除会话（仅删除当前用户的会话）。"""
    removed = get_session_store().delete_many(req.session_ids, user["id"])
    return SessionBatchDeleteResponse(ok=True, removed=removed)


@router.get("/sessions/{session_id}/messages", response_model=SessionListResponse)
def session_messages(session_id: str, user: dict = Depends(get_current_user)):
    """读取会话消息（供切换历史会话时恢复对话）。"""
    store = get_session_store()
    sess = store.get(session_id, user["id"])
    if not sess:
        raise AppError("会话不存在", 404)
    return {"sessions": [], "messages": store.messages(session_id, user["id"]), "title": sess["title"]}


@router.post("/sessions/{session_id}/rename", response_model=SessionRenameResponse)
def rename_session(session_id: str, req: SessionRenameRequest, user: dict = Depends(get_current_user)):
    ok = get_session_store().rename(session_id, req.title, user["id"])
    if not ok:
        raise AppError("会话不存在", 404)
    return SessionRenameResponse(ok=True)


@router.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
def delete_session(session_id: str, user: dict = Depends(get_current_user)) -> SessionDeleteResponse:
    ok = get_session_store().delete(session_id, user["id"])
    if not ok:
        raise AppError("会话不存在", 404)
    return SessionDeleteResponse(ok=True)
