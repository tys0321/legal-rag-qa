"""合同审查：混合检索 + LLM，输出风险点、法规对照与备忘录草稿。"""
from __future__ import annotations

from app.core.config import settings
from app.repositories.vector_store import get_store
from app.services.citation_verify import verify_answer
from app.services.llm import chat
from app.services.risk import classify_risk

DISCLAIMER = (
    "本审查备忘录由 AI 基于知识库检索材料生成，仅供一般性参考，"
    "不构成律师正式审查意见。签约前请由执业律师审阅并以现行有效法规为准。"
)
WATERMARK = "AI 生成草稿，须律师审核，不构成正式法律意见"

REVIEW_PROMPT = """你是法律知识顾问。请审查下面的合同摘录，并严格按以下 Markdown 结构输出（四个一级标题，勿增删）：

## 风险点
（分点列出违约金、解除、管辖、付款、责任限制等风险；每点一行，以「- 」开头）

## 法规对照
（只对照【检索材料】中的条款，引用格式使用 [1][2]；材料没有的内容写明「检索材料未覆盖」）

## 审查备忘录
（给签约人的修改建议，分点列出；不得教唆违法或规避监管）

## 免责声明
（复述：本审查为 AI 草稿，须律师审核，不构成正式法律意见）

约束：不得编造材料中不存在的法条；材料不足时降低结论确定性；使用简体中文。

【标题】{title}
【关注点】{focus}
【合同摘录】
{text}

【检索材料】
{context}
"""


def _build_context(hits: list[dict]) -> str:
    parts = []
    for i, h in enumerate(hits, start=1):
        title = h.get("title") or ""
        article = h.get("article") or ""
        body = (h.get("text") or "")[:800]
        parts.append(f"[{i}] 《{title}》{article}\n{body}")
    return "\n\n".join(parts) if parts else "（无检索材料）"


def _section(md: str, heading: str) -> str:
    current = None
    buf: list[str] = []
    found: list[str] = []
    for line in (md or "").splitlines():
        name = line.strip().lstrip("#").strip()
        if name in {"风险点", "法规对照", "审查备忘录", "免责声明"}:
            if current == heading:
                found = buf
            current = name
            buf = []
            continue
        if current == heading:
            buf.append(line)
    if current == heading:
        found = buf
    return "\n".join(found).strip()


def _findings(md: str) -> list[str]:
    lines = []
    for raw in _section(md, "风险点").splitlines():
        item = raw.strip().lstrip("-").lstrip("•").strip()
        if item:
            lines.append(item)
    return lines[:12]


def _fallback(title: str, text: str, focus: str, hits: list[dict]) -> str:
    risks = ["请核对主体、标的、价款、履行期限与违约责任是否写明。"]
    if focus:
        risks.append(f"请重点核对关注点「{focus}」对应条款是否对等、是否约定了上限或例外。")
    if "管辖" not in text and "仲裁" not in text:
        risks.append("摘录中未见管辖或仲裁约定，发生争议时可能按法定管辖处理。")
    cite = []
    for i, h in enumerate(hits[:4], start=1):
        cite.append(f"- [{i}] 《{h.get('title') or '未知'}》{h.get('article') or ''}")
    cite_block = "\n".join(cite) if cite else "- 检索材料未覆盖，请律师对照现行法规复核。"
    risk_block = "\n".join(f"- {x}" for x in risks)
    return (
        f"## 风险点\n{risk_block}\n\n"
        f"## 法规对照\n{cite_block}\n\n"
        f"## 审查备忘录\n- 合同《{title or '未命名'}》仅完成初步对照，修改前请律师确认。\n"
        f"- 不要仅凭本草稿签署。\n\n"
        f"## 免责声明\n{DISCLAIMER}"
    )


def _sources(hits: list[dict]) -> list[dict]:
    out = []
    for h in hits:
        out.append(
            {
                "id": str(h.get("id") or ""),
                "doc_id": str(h.get("doc_id") or ""),
                "title": str(h.get("title") or ""),
                "category": str(h.get("category") or ""),
                "article": str(h.get("article") or ""),
                "page": int(h.get("page") or 0),
                "text": str(h.get("text") or "")[:500],
                "score": float(h.get("score") or 0),
                "match": h.get("match"),
                "effective_status": str(h.get("effective_status") or ""),
                "effective_detail": str(h.get("effective_detail") or ""),
            }
        )
    return out


def review_contract(*, title: str, text: str, focus: str = "") -> dict:
    title = (title or "").strip()
    text = (text or "").strip()
    focus = (focus or "").strip()
    risk = classify_risk(f"{title}\n{focus}\n{text}")
    if risk.level == "L1" and risk.block_answer:
        md = (
            "## 风险点\n- 涉及人身安全或刑事等高风险事项，系统不提供具体审查意见。\n\n"
            "## 法规对照\n- 请向执业律师或主管机关咨询。\n\n"
            "## 审查备忘录\n- 如有紧迫危险请拨打 110/120。\n\n"
            f"## 免责声明\n{DISCLAIMER}"
        )
        return {
            "available": True,
            "status": "active",
            "blocked": True,
            "message": "高风险内容已拦截，未生成具体审查意见。",
            "title": title,
            "focus": focus,
            "findings": _findings(md),
            "markdown": md,
            "sources": [],
            "watermark": WATERMARK,
            "disclaimer": DISCLAIMER,
        }

    query = f"合同 {title} {focus} {text[:500]}".strip()
    hits: list[dict] = []
    try:
        hits = get_store().search(query, top_k=settings.retrieve_top_k, min_score=settings.min_score)
    except Exception:  # noqa: BLE001
        hits = []

    sources: list[dict] = []
    try:
        prompt = REVIEW_PROMPT.format(
            title=title or "未命名合同",
            focus=focus or "整体风险",
            text=text[:12000],
            context=_build_context(hits),
        )
        md = chat([{"role": "system", "content": prompt}], temperature=0.2, max_tokens=1600)
        if hits:
            verified = verify_answer(md, hits)
            md = verified.answer
            sources = _sources(verified.sources or hits[:4])
    except Exception:  # noqa: BLE001
        md = _fallback(title, text, focus, hits)
        sources = _sources(hits[:4])

    if "免责声明" not in md:
        md = md.rstrip() + f"\n\n## 免责声明\n{DISCLAIMER}"

    findings = _findings(md)
    return {
        "available": True,
        "status": "active",
        "blocked": False,
        "message": "已生成审查备忘录草稿，须律师审核后再使用。",
        "title": title,
        "focus": focus,
        "findings": findings,
        "markdown": md,
        "sources": sources,
        "watermark": WATERMARK,
        "disclaimer": DISCLAIMER,
    }
