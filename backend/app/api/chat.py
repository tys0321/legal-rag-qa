"""对话路由（瘦路由：鉴权 + 参数校验 + 响应转换）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.schemas.chat import ChatRequest, ChatResponse, ClearSessionRequest, ClearSessionResponse
from app.services.chat_service import get_chat_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, user: dict = Depends(get_current_user)) -> ChatResponse:
    """对话：快慢分流 → 检索 → 生成带引用的回答（按用户隔离会话）。"""
    if not req.message.strip():
        raise AppError("消息不能为空", 400)

    try:
        result, sid = get_chat_service().ask(req.message, req.session_id, user["id"])
    except ValueError as exc:
        raise AppError(str(exc), 404) from exc
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"处理失败: {exc}", 500) from exc

    return ChatResponse(
        session_id=sid,
        answer=result.answer,
        mode=result.mode,
        sources=result.sources,
        disclaimer=result.disclaimer,
        routed_reason=result.routed_reason,
        related_cases=result.related_cases,
    )


@router.post("/session/clear", response_model=ClearSessionResponse)
def clear_session(req: ClearSessionRequest, user: dict = Depends(get_current_user)) -> ClearSessionResponse:
    get_chat_service().delete(req.session_id, user["id"])
    return ClearSessionResponse(ok=True)
