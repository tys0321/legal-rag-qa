"""职业研判草稿：律师意见书 / 法官说理 / 检察审查报告（混合检索 + LLM）。"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.repositories.vector_store import get_store
from app.services.citation_verify import verify_answer
from app.services.llm import chat
from app.services.risk import classify_risk

MODES = ("lawyer", "judge", "prosecutor")

DISCLAIMERS = {
    "lawyer": (
        "本意见书由 AI 基于知识库检索材料生成，仅供一般性法律知识参考，"
        "不构成律师正式法律意见或委托代理建议。具体案件请咨询执业律师并以现行有效法规为准。"
    ),
    "judge": (
        "本说理草稿由 AI 基于知识库检索材料生成，仅供审判辅助参考，"
        "不构成裁判意见；事实认定与法律适用以合议庭/独任法官依职权审查为准。"
    ),
    "prosecutor": (
        "本审查草稿由 AI 基于知识库检索材料生成，仅供办案辅助参考，"
        "不构成检察机关正式意见；定性与处理以承办检察官依法审查认定为准。"
    ),
}

WATERMARKS = {
    "lawyer": "AI 生成草稿，须律师审核，不构成正式法律意见",
    "judge": "AI 生成草稿，仅供审判辅助，不构成裁判意见",
    "prosecutor": "AI 生成草稿，仅供检察辅助，不构成正式意见",
}

TITLES = {
    "lawyer": "法律意见书（AI 草稿）",
    "judge": "裁判说理草稿（AI）",
    "prosecutor": "审查报告草稿（AI）",
}

# 各模式一级标题 → sections key
SECTION_MAPS = {
    "lawyer": {
        "案情梳理": "case_summary",
        "法律分析": "legal_analysis",
        "行动建议": "action_advice",
        "免责声明": "disclaimer",
    },
    "judge": {
        "事实要点": "case_summary",
        "争议焦点": "issues",
        "法律适用": "legal_analysis",
        "裁判思路": "action_advice",
        "庭审提纲": "hearing_outline",
        "免责声明": "disclaimer",
    },
    "prosecutor": {
        "事实摘要": "case_summary",
        "证据与证明": "evidence",
        "定性分析": "legal_analysis",
        "处理意见": "action_advice",
        "补查提纲": "supplement",
        "免责声明": "disclaimer",
    },
}

PROMPTS = {
    "lawyer": """你是执业律师办案助手。输入按接案谈话结构给出（当事人、诉求、对方主张、事实时间线、证据、研判重点）。
请依据【检索材料】撰写「给委托人看的」简版法律意见书草稿。
必须严格按以下 Markdown 结构输出（四个一级标题，勿增删）：

## 案情梳理
- 用条目归纳：委托人诉求、对方立场、关键时间线
- 标的/金额若有则写出；材料矛盾处标注「待核实」

## 法律分析
- 先写可能的请求权基础或抗辩路径，再结合检索材料逐点分析
- 法条引用格式用 [1][2] 对应材料编号；不得编造法条
- 单独用一小段写「主要风险」（败诉点、时效、管辖、举证难等）

## 行动建议
- 按优先级分点：固定证据 → 协商/发函 → 仲裁或诉讼路径 → 注意事项
- 写清「建议先做什么、暂不建议做什么」；不得教唆违法

## 免责声明
（复述：本意见为 AI 草稿，须承办律师审核，不构成正式法律意见）

约束：优先吃透【槽位补充】；材料不足则降低确定性；简体中文。

【业务类型】{scene}
【研判重点】{question}
【接案材料】
{fact}

【槽位补充】
{slots}

【检索材料】
{context}
""",
    "judge": """你是民事/行政审判辅助助手。输入按阅卷习惯给出（原告诉请、被告答辩、无争议事实、争议事实、待决问题）。
请撰写供合议或撰写裁判文书前使用的「争点与说理」工作草稿。
必须严格按以下 Markdown 结构输出（六个一级标题，勿增删）：

## 事实要点
分两块书写：
1. 无争议 / 可初步认定的事实（条目）
2. 待证事实（条目，并提示证明责任大致归属）

## 争议焦点
- 必须从「原告诉请 vs 被告答辩」对立中提炼，每点一句话
- 按审理逻辑排序（程序问题在前，实体问题在后）
- 与【待决问题】对齐，勿堆砌无关争点

## 法律适用
- 分别对应各争点：请求权基础 / 抗辩规范
- 引用检索材料 [1][2]；不得编造法条；效力不明时写明「须核对现行文本」

## 裁判思路
- 按诉讼请求逐项分段：请求一 / 请求二 … 分别写支持 / 部分支持 / 驳回的论证路径（不是最终主文）
- 立场中立，禁止代理口吻

## 庭审提纲
- 拟重点查明事项（条目）
- 拟组织质证的证据与询问要点（条目）

## 免责声明
（复述：本草稿仅供审判辅助，不构成裁判意见）

约束：优先使用【槽位补充】；简体中文。

【案由】{scene}
【待决问题】{question}
【阅卷材料】
{fact}

【槽位补充】
{slots}

【检索材料】
{context}
""",
    "prosecutor": """你是审查起诉辅助助手。输入按阅卷习惯给出（阶段、嫌疑人、移送罪名、认定事实、证据及证明对象、辩解、缺口、审查焦点、要件勾选结果）。
请撰写「审查报告要点」工作草稿（非正式文书）。
必须严格按以下 Markdown 结构输出（六个一级标题，勿增删）：

## 事实摘要
- 按何人、何时、何地、手段、结果压缩叙述
- 材料不足处标明「待补查」；不做有罪预断表述

## 证据与证明
用对照表意识书写（可用条目）：
- 证据名称 → 证明对象 → 能否印证 / 矛盾点
- 单列「缺口与程序瑕疵」（吸收用户已填缺口）

## 定性分析
- 对照构成要件：罪与非罪、此罪与彼罪
- 回应嫌疑人辩解是否足以动摇证明体系
- 引用 [1][2]；不得编造法条

## 处理意见
必须包含：
1. 方向建议：起诉 / 不起诉 / 退回补充侦查（可多选说明条件）
2. 理由要点（对应证据与定性）
3. 注明「须承办检察官依卷宗复核」

## 补查提纲
- 无论是否建议退查，均单独列出待补查/核实事项（要调取什么、核实什么、对应哪个要件）
- 若要件已齐备，写明「暂无强制补查项，建议复核证明力与程序合法性」

## 免责声明
（复述：本草稿仅供检察辅助，不构成正式意见）

约束：禁止教唆违法或规避侦查；优先【槽位补充】；简体中文。

【案件类型】{scene}
【审查焦点】{question}
【卷宗材料】
{fact}

【槽位补充】
{slots}

【检索材料】
{context}
""",
}


@dataclass
class OpinionResult:
    scene: str = ""
    risk_level: str = "L3"
    blocked: bool = False
    title: str = "法律意见书（AI 草稿）"
    mode: str = "lawyer"
    sections: dict[str, str] = field(default_factory=dict)
    markdown: str = ""
    sources: list[dict] = field(default_factory=list)
    confidence: str = "medium"
    watermark: str = WATERMARKS["lawyer"]
    disclaimer: str = DISCLAIMERS["lawyer"]


def _normalize_mode(mode: str | None) -> str:
    m = (mode or "lawyer").strip().lower()
    return m if m in MODES else "lawyer"


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


def _parse_sections(md: str, mode: str) -> dict[str, str]:
    keys = SECTION_MAPS[mode]
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
        sections["disclaimer"] = DISCLAIMERS[mode]
    return sections


def _blocked_markdown(mode: str) -> str:
    if mode == "judge":
        return (
            "## 事实要点\n（高风险问题，系统已拦截详细分析）\n\n"
            "## 争议焦点\n涉及人身安全或刑事等高风险事项，请依法移送或依职权处理。\n\n"
            "## 法律适用\n本系统不提供具体操作指引。\n\n"
            "## 裁判思路\n请通过正式办案系统与合议程序处理。\n\n"
            "## 庭审提纲\n（已拦截）\n\n"
            f"## 免责声明\n{DISCLAIMERS[mode]}"
        )
    if mode == "prosecutor":
        return (
            "## 事实摘要\n（高风险问题，系统已拦截详细分析）\n\n"
            "## 证据与证明\n涉及紧急人身安全事项，请立即通过公安机关等法定渠道处置。\n\n"
            "## 定性分析\n本系统不提供规避侦查或违法指引。\n\n"
            "## 处理意见\n请依刑事诉讼法与内部规定办理。\n\n"
            "## 补查提纲\n（已拦截）\n\n"
            f"## 免责声明\n{DISCLAIMERS[mode]}"
        )
    return (
        "## 案情梳理\n（高风险问题，系统已拦截详细分析）\n\n"
        "## 法律分析\n涉及人身安全或刑事等高风险事项，本系统不提供具体操作建议。"
        "请立即寻求警方、急救或执业律师帮助。\n\n"
        "## 行动建议\n1. 如有紧迫危险请拨打 110/120\n2. 通过案源广场联系认证律师\n\n"
        f"## 免责声明\n{DISCLAIMERS[mode]}"
    )


def generate_opinion(
    *,
    fact_summary: str,
    scene: str = "",
    question: str = "",
    slot_answers: dict[str, str] | None = None,
    mode: str = "lawyer",
) -> OpinionResult:
    mode = _normalize_mode(mode)
    fact = (fact_summary or "").strip()
    scene = (scene or "").strip()
    default_q = {
        "lawyer": "请出具法律意见",
        "judge": "请整理裁判说理思路",
        "prosecutor": "请整理审查意见要点",
    }[mode]
    question = (question or "").strip() or default_q
    slots = slot_answers or {}
    disclaimer = DISCLAIMERS[mode]
    watermark = WATERMARKS[mode]
    title = TITLES[mode]

    risk = classify_risk(f"{question}\n{fact}")
    if risk.level == "L1" and risk.block_answer:
        md = _blocked_markdown(mode)
        return OpinionResult(
            scene=scene,
            risk_level="L1",
            blocked=True,
            title=title,
            mode=mode,
            sections=_parse_sections(md, mode),
            markdown=md,
            sources=[],
            confidence="low",
            watermark=watermark,
            disclaimer=disclaimer,
        )

    query = f"{scene} {question} {fact}".strip()
    store = get_store()
    hits = store.search(query, top_k=settings.retrieve_top_k, min_score=settings.min_score)
    context = _build_context(hits)

    prompt = PROMPTS[mode].format(
        scene=scene or "未指定",
        question=question,
        fact=fact,
        slots=_slots_text(slots),
        context=context,
    )
    text = chat(
        [{"role": "system", "content": prompt}],
        temperature=0.2,
        max_tokens=1800,
    )

    sources: list[dict] = []
    if hits:
        verified = verify_answer(text, hits)
        text = verified.answer
        sources = verified.sources

    if "免责声明" not in text:
        text = text.rstrip() + f"\n\n## 免责声明\n{disclaimer}"

    sections = _parse_sections(text, mode)
    conf = "high" if len(sources) >= 2 else ("medium" if sources or hits else "low")
    if risk.level == "L2":
        conf = "medium"

    return OpinionResult(
        scene=scene,
        risk_level=risk.level,
        blocked=False,
        title=title,
        mode=mode,
        sections=sections,
        markdown=text,
        sources=sources,
        confidence=conf,
        watermark=watermark,
        disclaimer=disclaimer,
    )
