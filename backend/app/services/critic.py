"""自批评模块：第二轮检查是否编造条号/超出材料。"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger("service.critic")


@dataclass
class CriticResult:
    ok: bool = True
    issues: list[str] = field(default_factory=list)
    strip_citations: list[str] = field(default_factory=list)
    revised_answer: str | None = None


_CRITIC_PROMPT = """你是法律回答质检员。根据【检索材料】检查【回答】是否编造法条、条号或材料中不存在的内容。

只输出 JSON（不要 markdown）：
{{"ok": true/false, "issues": ["..."], "strip_citations": ["《X法》第Y条", "[n]"], "needs_revise": true/false, "revised_answer": "若需小修则给出修订全文，否则空字符串"}}

规则：
- 材料中没有的法名/条号必须列入 strip_citations 且 ok=false
- 允许对材料内容做概括，但不允许捏造条款
- 若回答已声明「未检索到相关依据」，ok=true

【检索材料】
{context}

【回答】
{answer}
"""


def self_critic(answer: str, hits: list[dict], context: str) -> CriticResult:
    if not settings.critic_enabled:
        return CriticResult(ok=True)
    if not hits and "未检索到" in answer:
        return CriticResult(ok=True)

    from app.services.llm import chat

    try:
        raw = chat(
            [
                {
                    "role": "user",
                    "content": _CRITIC_PROMPT.format(context=context or "（无）", answer=answer),
                }
            ],
            temperature=0.0,
            max_tokens=1200,
            timeout=90.0,
        )
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if not m:
            logger.warning("自批评未返回 JSON，跳过: %s", raw[:160])
            return CriticResult(ok=True, issues=["critic_parse_skip"])
        data = json.loads(m.group(0))
        revised = (data.get("revised_answer") or "").strip() or None
        if data.get("needs_revise") and revised:
            return CriticResult(
                ok=bool(data.get("ok", False)),
                issues=list(data.get("issues") or []),
                strip_citations=list(data.get("strip_citations") or []),
                revised_answer=revised,
            )
        return CriticResult(
            ok=bool(data.get("ok", True)),
            issues=list(data.get("issues") or []),
            strip_citations=list(data.get("strip_citations") or []),
            revised_answer=None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("自批评失败，跳过: %s", exc)
        return CriticResult(ok=True, issues=[f"critic_error:{exc}"])


def confidence_label(
    *,
    hits: list[dict],
    verified_ratio: float,
    critic_ok: bool,
    stripped: list[str],
) -> str:
    """高/中/低 置信度。"""
    if not hits:
        return "low"
    avg = 0.0
    if hits:
        scores = [float(h.get("rerank_score") or h.get("score") or 0) for h in hits]
        avg = sum(scores) / max(len(scores), 1)
    if critic_ok and verified_ratio >= 0.9 and avg >= settings.confidence_high_threshold and not stripped:
        return "high"
    if verified_ratio >= 0.6 and avg >= settings.confidence_mid_threshold:
        return "medium"
    return "low"
