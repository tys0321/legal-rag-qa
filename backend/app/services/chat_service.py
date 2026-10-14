"""对话服务层：风险分级 → 槽位引导 → RAG（按用户隔离）。"""
from __future__ import annotations

import logging

from app.core.config import settings
from app.repositories.sessions import SessionStore, get_session_store
from app.services.rag import DISCLAIMER, RagResult, answer
from app.services.risk import classify_risk, l1_safe_reply
from app.services import slots as slot_svc

logger = logging.getLogger("service.chat")


class ChatService:
    """封装一次对话的完整业务逻辑。"""

    def __init__(self, sessions: SessionStore | None = None) -> None:
        self.sessions = sessions or get_session_store()

    def ask(
        self,
        message: str,
        session_id: str | None,
        user_id: int,
        *,
        scene: str | None = None,
        skip_slots: bool = False,
    ) -> tuple[RagResult, str]:
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

        # ---- 风险分级 ----
        risk = classify_risk(message)
        if risk.block_answer:
            result = RagResult(
                answer=l1_safe_reply(),
                mode="risk_block",
                sources=[],
                disclaimer=DISCLAIMER,
                routed_reason=f"risk:{risk.level}:{risk.reason}",
                confidence="low",
                risk_level=risk.level,
                risk_banner=risk.banner,
                force_lawyer_cta=risk.force_lawyer_cta,
            )
            self.sessions.append(sid, "user", message, user_id)
            self.sessions.append(sid, "assistant", result.answer, user_id)
            return result, sid

        # ---- 槽位引导 ----
        state = slot_svc.get_session_slots(sid)
        current_scene = scene or state.get("scene") or ""
        filled = dict(state.get("slots") or {})

        if settings.slot_guidance_enabled and not skip_slots:
            if not current_scene:
                current_scene = slot_svc.detect_scene(message) or ""
            if current_scene:
                # 仅当本会话已进入该场景追问时，才把本轮当作槽位填写
                if state.get("scene") == current_scene and slot_svc.missing_slots(current_scene, filled):
                    filled = slot_svc.try_fill_from_message(current_scene, message, filled)
                slot_svc.save_session_slots(sid, current_scene, filled)
                missing = slot_svc.missing_slots(current_scene, filled)
                if missing:
                    q = slot_svc.build_slot_question(current_scene, missing)
                    result = RagResult(
                        answer=q,
                        mode="slot",
                        sources=[],
                        disclaimer=DISCLAIMER,
                        routed_reason=f"slot:{current_scene}",
                        confidence="medium",
                        risk_level=risk.level,
                        risk_banner=risk.banner,
                        force_lawyer_cta=risk.force_lawyer_cta,
                        scene=current_scene,
                        need_slots=[{"key": m["key"], "prompt": m["prompt"]} for m in missing],
                        waiting_for_slot=True,
                    )
                    self.sessions.append(sid, "user", message, user_id)
                    self.sessions.append(sid, "assistant", result.answer, user_id)
                    return result, sid

        # ---- 正常 / L2 RAG ----
        enriched = message
        if current_scene and filled:
            ctx = slot_svc.slots_context_text(current_scene, filled)
            enriched = f"{message}\n\n【案情要素】\n{ctx}"

        try:
            result = answer(enriched, history)
        except Exception:
            logger.exception("问答处理失败")
            raise

        result.risk_level = risk.level
        result.risk_banner = risk.banner
        result.force_lawyer_cta = risk.force_lawyer_cta
        result.scene = current_scene
        result.need_slots = []
        result.waiting_for_slot = False

        self.sessions.append(sid, "user", message, user_id)
        self.sessions.append(sid, "assistant", result.answer, user_id)
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
