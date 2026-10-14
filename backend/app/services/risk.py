"""高风险法律问题分级：L1 强拦截 / L2 降级+转人工 / L3 正常。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.config import settings

# L1：人身安全 / 刑事指控等高风险 —— 强拦截
L1_PATTERNS = [
    r"(杀人|伤害致死|强奸|绑架|拐卖|恐怖|爆炸|放火|投毒)",
    r"(吸毒|贩毒|制毒|枪支|弹药|爆炸物)",
    r"(自杀|自残|家暴.*报警|正在被打|有人要杀)",
    r"(被刑事拘留|被逮捕|取保候审|检察院起诉|刑事辩护|刑事责任)",
    r"(包庇|窝藏|伪证|毁灭证据|串供)",
]

# L2：重大财产（金额阈值）或复杂高标的民事
L2_PATTERNS = [
    r"(破产|清算|股权大战|恶意收购|跨境追偿)",
    r"(标的|涉案|损失|欠款|赔偿|合同金额|借款).{0,12}(\d+\.?\d*)\s*(万|亿)",
]

L2_AMOUNT_RE = re.compile(
    r"(?:标的|涉案|损失|欠款|赔偿|金额|借款|货款|工程款).{0,16}(\d+(?:\.\d+)?)\s*(万|亿|元)"
)


@dataclass
class RiskResult:
    level: str  # L1 | L2 | L3
    reason: str = ""
    block_answer: bool = False
    force_lawyer_cta: bool = False
    banner: str = ""


def _parse_amount_yuan(text: str) -> float | None:
    m = L2_AMOUNT_RE.search(text)
    if not m:
        # 宽松：任意「数字+万/亿」
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*(万|亿)", text)
        if not m2:
            return None
        num, unit = float(m2.group(1)), m2.group(2)
    else:
        num, unit = float(m.group(1)), m.group(2)
    if unit == "亿":
        return num * 100_000_000
    if unit == "万":
        return num * 10_000
    return num


def classify_risk(question: str) -> RiskResult:
    q = (question or "").strip()
    if not q:
        return RiskResult(level="L3")

    for p in L1_PATTERNS:
        if re.search(p, q):
            return RiskResult(
                level="L1",
                reason="命中人身安全/刑事等高风险信号",
                block_answer=True,
                force_lawyer_cta=True,
                banner=(
                    "⚠️ 高风险提示：该问题可能涉及人身安全或刑事责任。"
                    "系统不提供具体操作建议。请立即寻求专业律师帮助；"
                    "若有人身危险请拨打 110 / 报警。"
                ),
            )

    threshold = settings.risk_l2_amount_yuan  # 默认 50 万
    amount = _parse_amount_yuan(q)
    if amount is not None and amount >= threshold:
        return RiskResult(
            level="L2",
            reason=f"涉案金额约 {amount:.0f} 元，超过阈值 {threshold:.0f}",
            block_answer=False,
            force_lawyer_cta=True,
            banner=(
                "⚠️ 重大财产风险：本案标的较高，以下仅为一般性法律科普，"
                "不构成个案意见。建议尽快咨询执业律师或通过案源广场对接律师。"
            ),
        )

    for p in L2_PATTERNS:
        if re.search(p, q):
            return RiskResult(
                level="L2",
                reason="命中重大财产/复杂商事信号",
                block_answer=False,
                force_lawyer_cta=True,
                banner=(
                    "⚠️ 复杂高风险民事/商事场景：建议在专业律师指导下行动，"
                    "可使用「转律师/案源」入口。"
                ),
            )

    return RiskResult(level="L3")


def l1_safe_reply() -> str:
    return (
        "根据系统风险策略，该问题属于高风险场景（可能涉及人身安全或刑事责任），"
        "我不能提供具体操作或策略建议。\n\n"
        "1、**如有紧急人身危险**：请立即拨打 **110** 或向当地公安机关求助。\n\n"
        "2、**法律帮助**：请咨询执业律师或值班律师；后续可在律师版「案源广场」发布需求（M3）。\n\n"
        "3、**说明**：本系统仅提供一般性法律知识参考，不构成正式法律意见。"
    )
