"""法律意见书生成：混合检索 + LLM，结构化输出。"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.repositories.vector_store import get_store
from app.services.citation_verify import verify_answer
from app.services.llm import chat
from app.services.risk import classify_risk

DISCLAIMER = (
    "本意见书由 AI 基于知识库检索材料生成，仅供一般性法律知识参考，"
    "不构成律师正式法律意见或委托代理建议。具体案件请咨询执业律师并以现行有效法规为准。"
)

WATERMARK = "AI 生成草稿，须律师审核，不构成正式法律意见"

OPINION_PROMPT = """你是法律知识顾问。请根据【检索材料】与【案情】撰写简版法律意见书草稿。
必须严格按以下 Markdown 结构输出（四个一级标题，勿增删）：

## 案情梳理
（归纳事实与诉求，客观简洁）

## 法律分析
（结合材料中的法规条款分析；引用格式使用 [1][2] 对应材料编号；无依据处明确说明）

## 行动建议
（可执行的下一步建议，分点列出；不得教唆违法）

## 免责声明
（复述：本意见为 AI 草稿，须律师审核，不构成正式法律意见）

约束：
- 不得编造不存在的法条
- 材料不足时降低结论确定性
- 使用简体中文

【场景】{scene}
【诉求】{question}
【案情】
{fact}

【槽位补充】
{slots}

【检索材料】
{context}
"""


@dataclass
class OpinionResult:
    scene: str = ""
    risk_level: str = "L3"
    blocked: bool = False
    title: str = "法律意见书（AI 草稿）"
    sections: dict[str, str] = field(default_factory=dict)
    markdown: str = ""
    sources: list[dict] = field(default_factory=list)
    confidence: str = "medium"
    watermark: str = WATERMARK
    disclaimer: str = DISCLAIMER


def _slots_text(slots: dict[str, str]) -> str:
    if not slots:
        return "（无）"
    lines = [f"- {k}: {v}" for k, v in slots.items() if v]
    return "\n".join(lines) if lines else "（无）"


def _build_context(hits: list[dict]) -> str:
    parts = []
    for i, h in enumerate(hits, start=1):
        title = h.get("title") or ""
        article = h.get("article") or ""
        text = (h.get("text") or "")[:800]
        parts.append(f"[{i}] 《{title}》{article}\n{text}")
    return "\n\n".join(parts) if parts else "（无检索材料）"


def _parse_sections(md: str) -> dict[str, str]:
    keys = {
        "案情梳理": "case_summary",
        "法律分析": "legal_analysis",
        "行动建议": "action_advice",
        "免责声明": "disclaimer",
    }
    sections = {v: "" for v in keys.values()}
    current = None
    buf: list[str] = []
    for line in (md or "").splitlines():
        heading = line.strip().lstrip("#").strip()
        if heading in keys:
            if current:
                sections[current] = "\n".join(buf).strip()
            current = keys[heading]
            buf = []
            continue
        if current is not None:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    if not sections.get("disclaimer"):
        sections["disclaimer"] = DISCLAIMER
    return sections


def generate_opinion(
    *,
    fact_summary: str,
    scene: str = "",
    question: str = "",
    slot_answers: dict[str, str] | None = None,
) -> OpinionResult:
    fact = (fact_summary or "").strip()
    scene = (scene or "").strip()
    question = (question or "").strip() or "请出具法律意见"
    slots = slot_answers or {}

    risk = classify_risk(f"{question}\n{fact}")
    if risk.level == "L1" and risk.block_answer:
        md = (
            "## 案情梳理\n（高风险问题，系统已拦截详细分析）\n\n"
            "## 法律分析\n涉及人身安全或刑事等高风险事项，本系统不提供具体操作建议。"
            "请立即寻求警方、急救或执业律师帮助。\n\n"
            "## 行动建议\n1. 如有紧迫危险请拨打 110/120\n2. 通过案源广场联系认证律师\n\n"
            f"## 免责声明\n{DISCLAIMER}"
        )
        return OpinionResult(
            scene=scene,
            risk_level="L1",
            blocked=True,
            sections=_parse_sections(md),
            markdown=md,
            sources=[],
            confidence="low",
        )

    query = f"{scene} {question} {fact}".strip()
    store = get_store()
    hits = store.search(query, top_k=settings.retrieve_top_k, min_score=settings.min_score)
    context = _build_context(hits)

    prompt = OPINION_PROMPT.format(
        scene=scene or "未指定",
        question=question,
        fact=fact,
        slots=_slots_text(slots),
        context=context,
    )
    text = chat(
        [{"role": "system", "content": prompt}],
        temperature=0.2,
        max_tokens=1600,
    )

    sources: list[dict] = []
    if hits:
        verified = verify_answer(text, hits)
        text = verified.answer
        sources = verified.sources

    if "免责声明" not in text:
        text = text.rstrip() + f"\n\n## 免责声明\n{DISCLAIMER}"

    sections = _parse_sections(text)
    conf = "high" if len(sources) >= 2 else ("medium" if sources or hits else "low")
    if risk.level == "L2":
        conf = "medium"

    return OpinionResult(
        scene=scene,
        risk_level=risk.level,
        blocked=False,
        sections=sections,
        markdown=text,
        sources=sources,
        confidence=conf,
    )
