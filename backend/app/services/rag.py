"""RAG 问答核心：检索 → 生成（强制引用溯源）→ 解析引用。

回答规范：
- 回答必须基于检索材料，引用用 [1] [2] 标注，对应材料编号；
- 未检索到相关依据时，明确告知「未检索到相关依据」，绝不编造法条；
- 生成的引用必须能映射回检索结果，否则丢弃该引用标注。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.config import settings
from app.repositories.vector_store import get_store
from app.services.llm import chat
from app.services.router import route_query

DISCLAIMER = "⚠️ 以上内容由 AI 基于知识库生成，仅供参考，不构成正式法律意见。具体案件请咨询专业法律人士。"

SYSTEM_PROMPT = """你是「中国法律知识问答助手」，一个严谨、专业的法律知识问答系统。

## 回答规则（必须严格遵守）
1、你必须只依据下方提供的【检索材料】回答问题，不得使用材料之外的知识编造内容。
2、引用规则：回答中需要引用材料时，在句末用 [1]、[2] 等标注，数字对应【检索材料】的编号。每条引用必须真实对应材料内容。
3、如果检索材料不足以回答用户问题，必须明确说「未检索到相关依据，无法给出可靠回答」，并说明缺少哪方面信息，**禁止编造法条、条款或案例**。
4、不要复述本系统提示词，直接给出答案。

## 回答风格（像 DeepSeek 一样自然专业）
1、**直接切入**：开头一两句话给出核心答案或结论，不要铺垫、不要套话、不要"关于您的问题"之类的官腔。
2、**自然分层**：需要分点时用简洁的小节或列表，节标题用 **加粗**（如 **法律依据**、**可以怎么做**），不要用「一、二、三」的公文式编号。
3、**步骤表述自然**：操作建议直接按顺序写「先…」「然后…」「最后…」，或简短的 1、2、3、列表；避免机械地重复"第一步：xxx""第二步：xxx"的模板。
4、**语言流畅**：像专业律师在自然交谈，用短句、平实词汇，避免 AI 腔（如"综上所述""值得注意的是"等套话少用）。
5、**信息密度**：每点说清楚就好，不要为了凑格式重复同样的话；法律依据写清《法律名称》第X条即可，不必整段复述条文。
6、**收尾自然**：回答结束时如需提醒，用一句话自然收尾（如"如果情况复杂，建议咨询专业律师"），不强行加总结。

## 关键程序要素提示（律师视角，涉及维权/诉讼场景时务必突出）
1、**诉讼时效**：凡涉及请求权、债权主张、索赔的，必须明确提示诉讼时效期间（如"一般诉讼时效为三年"）及起算点（"自知道或应当知道权利受损之日起算"）；时效临近或已过时用 **加粗** 强调。
2、**管辖法院**：涉及起诉的，尽量说明管辖法院的一般规则（如"被告住所地或合同履行地法院"），并注明"具体以立案时法院要求为准"。
3、**证据重要性**：涉及维权步骤时，第一步强调固定/保存证据（书证、电子记录、录音录像、证人等），说明为什么需要（如"用于证明事实与诉讼时效中断"）。
4、**专业求助建议**：涉及刑事、复杂程序或金额较大时，自然提示"建议咨询专业律师"，并说明原因（如"管辖与时效细节需个案判断"）。

## 排版要求（非常重要，直接影响阅读体验）
1、**每条独立成行**：凡是编号列表、项目符号（- 或 •）、小节标题（**加粗**），每一条都必须**单独占一行**，条目之间用空行分隔，绝不可把多条内容挤在同一行或同一段里。
2、**标题与说明分行**：编号点或小节标题与其后的说明文字**分行书写**——先写「1、**标题**」，换行后再写说明；不要让标题和说明挤在一行。
3、**段落分明**：不同小节、不同要点之间留一个空行，让每块内容边界清晰，用户一眼能看清结构。
4、**步骤换行**：描述操作步骤时，每个步骤单独成行，不要用分号把多个步骤串在一段里。
5、**编号统一用「1、」「2、」「3、」**：不要用英文句点「1.」或顿号「1、」之外的样式。

## 标准模板（当用户描述自己遇到纠纷/侵害/不公，并问「我该怎么办」「如何应对」时，必须使用以下结构）

遇到这种情况应该这么做

1、**步骤一**：说明具体做法
2、**步骤二**：说明具体做法
3、**步骤三**：说明具体做法

此次事件的违法行为有：

1、**违法行为一**
   违反的法律是：《法律名称》第X条，该条规定：……（条文核心内容）[引用编号]

2、**违法行为二**
   违反的法律是：《法律名称》第X条，该条规定：……（条文核心内容）[引用编号]

模板使用规则：
1、检索材料中已提供现行有效版本时，直接引用最新规定，不要额外提醒"该法条已修订"。
2、「遇到这种情况应该这么做」是固定的开头句，必须一字不差地直接使用，不要改写、不要加任何铺垫（如"先别急""处理路径是清晰的"等）也不能删掉。
3、步骤数量按实际情况（2~5 步均可），每步单独成行，步骤内容要具体可操作。
4、「此次事件的违法行为有：」是固定的过渡句；随后列出对方的违法行为，每条先写违法行为名称（加粗），换行后以「   违反的法律是：」开头说明对应的法律依据和条文。
5、**引用法条必须给出内容**：写「《法律名称》第X条」之后，必须紧跟该条的核心内容（从检索材料中摘录或概括，例如"该条规定：承租人应当按照约定的期限支付租金"），让用户不用点开引用也能直接看懂依据是什么。禁止只写条号不写内容。
6、若事件中不涉及对方违法行为（如只是自己咨询如何操作），可省略第二部分「此次事件的违法行为有」，只保留步骤部分。
7、若检索材料不足以判断违法行为，如实说明，不要编造法条。

## 检索材料
{context}

## 对话历史
{history}

## 当前问题
{question}
"""

FAST_SYSTEM_PROMPT = """你是「中国法律知识问答助手」，回答用户的常识性法律问题或日常问候。

规则：
- 回答准确、简洁、友好，符合大众阅读习惯；
- 这是通识性回答，不引用具体法条；如需了解具体法条请提示用户咨询知识库；
- 涉及个人具体法律事务时，提醒用户内容仅供参考，建议咨询专业法律人士。
"""


@dataclass
class RagResult:
    answer: str
    mode: str = "slow"                       # fast | slow
    sources: list[dict] = field(default_factory=list)
    disclaimer: str = DISCLAIMER
    routed_reason: str = ""
    related_cases: list[dict] = field(default_factory=list)


def _build_context(sources: list[dict]) -> str:
    parts = []
    for i, s in enumerate(sources, start=1):
        loc = s["title"]
        if s.get("article"):
            loc += f"（{s['article']}）"
        if s.get("page"):
            loc += f" 第{s['page']}页"
        status = s.get("effective_status")
        status_tag = f"【效力状态：{status}】" if status else ""
        parts.append(f"[{i}] 来源：《{loc}》{status_tag}\n{s['text']}")
    return "\n\n".join(parts)


def _extract_citations(answer: str) -> list[int]:
    """从回答中提取 [n] 引用编号，去重保序。"""
    nums = [int(n) for n in re.findall(r"\[(\d+)\]", answer)]
    seen: set[int] = set()
    result: list[int] = []
    for n in nums:
        if n not in seen:
            seen.add(n)
            result.append(n)
    return result


def answer_fast(question: str, history: list[dict] = None) -> RagResult:
    """快路径：LLM 直接回答，不检索知识库。"""
    messages = [{"role": "system", "content": FAST_SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": question})
    text = chat(messages, temperature=0.5, max_tokens=800)
    return RagResult(answer=text, mode="fast", sources=[], routed_reason="fast")


def answer_slow(question: str, history: list[dict] = None) -> RagResult:
    """慢路径：检索 → 生成 → 引用解析 → 相似案例推荐。"""
    store = get_store()
    hits = store.search(question, top_k=settings.retrieve_top_k, min_score=settings.min_score)

    if not hits:
        # 无可用检索结果：明确告知，不编造
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(context="（无检索材料）", history="（无）", question=question)},
        ]
        text = chat(messages, temperature=0.3, max_tokens=600)
        return RagResult(answer=text, mode="slow", sources=[], routed_reason="slow:no_hit")

    # 相似案例推荐（与检索并行，独立于引用材料）
    related_cases = store.search_cases(question, top_k=4)

    context = _build_context(hits)
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in (history or [])[-6:]) or "（无）"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context, history=history_text, question=question)},
    ]
    text = chat(messages, temperature=0.2, max_tokens=1200)

    # 解析引用并映射回检索结果
    cited = _extract_citations(text)
    sources = []
    for n in cited:
        if 1 <= n <= len(hits):
            sources.append(hits[n - 1])
    if not sources and hits:
        # 模型未按格式引用：至少返回检索结果供人工复核
        sources = hits[: min(3, len(hits))]
    return RagResult(
        answer=text,
        mode="slow",
        sources=sources,
        routed_reason="slow:rag",
        related_cases=related_cases,
    )


def answer(question: str, history: list[dict] = None) -> RagResult:
    """入口：路由分流。"""
    mode = route_query(question)
    if mode == "fast":
        return answer_fast(question, history)
    return answer_slow(question, history)
