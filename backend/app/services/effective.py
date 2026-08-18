"""法规时效（效力状态）模块。

通过文本规则自动推断法规的效力状态：
- 现行有效：标题/正文无失效标记；
- 已废止/已失效：含「已废止」「同时废止」「失效」「不再适用」等标记；
- 已修订：含「修正」「修订」「修改决定」等，或标题带修正年份；
- 部分失效：含「部分条款失效」等。

Phase 2 用规则引擎实现；后续可扩展为外部权威数据源（国家法律法规数据库）对照。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 废止/失效强信号
REPEALED_PATTERNS = [
    r"本(法|条例|办法|规定|细则).{0,20}(废止|失效|不再适用)",
    r"自.{0,20}起(同时)?废止",
    r"予以(废止|撤销|终止执行)",
    r"已经(被|为).{0,30}(取代|替代)",
    r"(现予|予以)废止",
]

# 修订信号
REVISED_PATTERNS = [
    r"(根据|依据).{0,20}(修改|修正).{0,20}(决定|意见)",
    r"(修正案|修订本|修改决定)",
    r"第.{0,10}次(修正|修订)",
]

# 部分失效（某条款/某章废止，而非全文）
PARTIAL_PATTERNS = [
    r"部分(条款|条文).{0,10}(失效|废止)",
    r"(第[一二三四五六七八九十百千0-9]+条)(、第[一二三四五六七八九十百千0-9]+条)*.{0,20}(废止|失效)",
    r"(第[一二三四五六七八九十百千0-9]+章).{0,20}(废止|失效)",
]

# 标题中的修正年份（如 2018年修正）
TITLE_REVISION_RE = re.compile(r"(19|20)\d{2}年(修正|修订)")


@dataclass
class EffectiveStatus:
    """法规效力状态。"""

    status: str = "现行有效"        # 现行有效 / 已废止 / 已修订 / 部分失效 / 未知
    evidence: list[str] = field(default_factory=list)  # 判断依据
    detail: str = ""


def detect_status(title: str, text_head: str, body: str = "") -> EffectiveStatus:
    """根据标题与正文开头推断效力状态。"""
    sample = (text_head + "\n" + body[:2000])
    evidence: list[str] = []

    # 1) 部分条款失效（优先于整体废止判断：如「第X条废止」≠ 全文废止）
    for pat in PARTIAL_PATTERNS:
        m = re.search(pat, sample)
        if m:
            return EffectiveStatus(status="部分失效", evidence=[m.group(0)], detail="检测到部分条款失效")
    # 2) 整体废止/失效（排除仅个别条款废止的情况）
    for pat in REPEALED_PATTERNS:
        m = re.search(pat, sample)
        if m:
            return EffectiveStatus(status="已废止", evidence=[m.group(0)], detail="检测到废止/失效表述")
    # 3) 修订
    for pat in REVISED_PATTERNS:
        m = re.search(pat, sample)
        if m:
            evidence.append(m.group(0))
    if TITLE_REVISION_RE.search(title):
        evidence.append(f"标题含修正年份: {TITLE_REVISION_RE.search(title).group(0)}")
    if evidence:
        return EffectiveStatus(status="已修订", evidence=evidence, detail="检测到修订/修正标记")
    return EffectiveStatus(status="现行有效", evidence=[], detail="未检测到失效或修订标记")
