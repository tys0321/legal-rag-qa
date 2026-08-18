"""对话服务层：编排「会话加载 → 问答 → 历史写入」的完整流程（按用户隔离）。"""
from __future__ import annotations

import logging

from app.repositories.sessions import SessionStore, get_session_store
from app.services.rag import RagResult, answer

logger = logging.getLogger("service.chat")


class ChatService:
    """封装一次对话的完整业务逻辑。"""

    def __init__(self, sessions: SessionStore | None = None) -> None:
        self.sessions = sessions or get_session_store()

    def ask(self, message: str, session_id: str | None, user_id: int) -> tuple[RagResult, str]:
        """处理一次提问：返回 (结果, 会话ID)。"""
        message = message.strip()
        sid = session_id
        history: list[dict] = []
        if sid:
            sess = self.sessions.get(sid, user_id)
            if not sess:
                raise ValueError("会话不存在")
            history = self.sessions.messages(sid, user_id)
        else:
            sid = self.sessions.create(user_id, first_message=message)

        try:
            result = answer(message, history)
        except Exception as exc:  # noqa: BLE001
            logger.exception("问答处理失败")
            raise

        self.sessions.append(sid, "user", message, user_id)
        self.sessions.append(sid, "assistant", result.answer, user_id)
        # 更新会话标题（若还是默认名且是首条消息）
        sess = self.sessions.get(sid, user_id)
        if sess and sess["title"] == "新对话" and sess.get("msg_count", 0) == 0:
            pass  # create 时已用首条消息命名
        return result, sid

    def list(self, user_id: int) -> list[dict]:
        return self.sessions.list_sessions(user_id)

    def messages(self, session_id: str, user_id: int) -> list[dict]:
        return self.sessions.messages(session_id, user_id)

    def rename(self, session_id: str, title: str, user_id: int) -> bool:
        return self.sessions.rename(session_id, title, user_id)

    def delete(self, session_id: str, user_id: int) -> bool:
        return self.sessions.delete(session_id, user_id)


_chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
