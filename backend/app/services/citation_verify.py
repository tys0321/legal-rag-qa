"""引用验证层：剥离无法在检索材料中落地的法名/条号/[n] 标注。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_CITE_NUM_RE = re.compile(r"\[(\d+)\]")
_LAW_ART_RE = re.compile(
    r"《([^》]+)》\s*第([一二三四五六七八九十百千0-9]+)([条款章])"
)
_BARE_ART_RE = re.compile(r"第([一二三四五六七八九十百千0-9]+)([条款章])")


@dataclass
class VerifyResult:
    answer: str
    sources: list[dict]
    stripped_citations: list[str] = field(default_factory=list)
    verified_ratio: float = 1.0
    ok: bool = True


def _material_blob(hits: list[dict]) -> str:
    parts = []
    for h in hits:
        parts.append(
            f"{h.get('title', '')} {h.get('article', '')} {h.get('text', '')}"
        )
    return "\n".join(parts)


def verify_answer(answer: str, hits: list[dict]) -> VerifyResult:
    """校验 [n] 与《法》第X条 是否可映射到 hits。"""
    if not hits:
        # 无材料时不应出现具体法条引用
        cleaned = answer
        stripped = []
        for m in _LAW_ART_RE.finditer(answer):
            stripped.append(m.group(0))
        if stripped:
            for s in stripped:
                cleaned = cleaned.replace(s, "（未检索到对应条文，已省略）")
            return VerifyResult(
                answer=cleaned,
                sources=[],
                stripped_citations=stripped,
                verified_ratio=0.0,
                ok=False,
            )
        return VerifyResult(answer=answer, sources=[], verified_ratio=1.0, ok=True)

    blob = _material_blob(hits)
    stripped: list[str] = []

    # 1) [n] 范围校验
    nums = [int(n) for n in _CITE_NUM_RE.findall(answer)]
    valid_nums = {n for n in nums if 1 <= n <= len(hits)}
    invalid_nums = {n for n in nums if n not in valid_nums}
    cleaned = answer
    for n in invalid_nums:
        cleaned = cleaned.replace(f"[{n}]", "")
        stripped.append(f"[{n}]")

    # 2) 《法名》第X条 必须在材料中出现法名，且条号尽量可对齐
    for m in list(_LAW_ART_RE.finditer(cleaned)):
        law, num, unit = m.group(1), m.group(2), m.group(3)
        art = f"第{num}{unit}"
        law_ok = law in blob
        art_ok = art in blob or num in blob
        if not (law_ok and art_ok):
            stripped.append(m.group(0))
            cleaned = cleaned.replace(m.group(0), f"《{law}》（依据待核实）", 1)

    # 映射引用 sources
    cited = []
    seen = set()
    for n in _CITE_NUM_RE.findall(cleaned):
        i = int(n)
        if 1 <= i <= len(hits) and i not in seen:
            seen.add(i)
            cited.append(hits[i - 1])
    if not cited:
        cited = hits[: min(3, len(hits))]

    total_checks = max(len(nums) + len(list(_LAW_ART_RE.finditer(answer))), 1)
    verified_ratio = max(0.0, 1.0 - len(stripped) / total_checks)
    return VerifyResult(
        answer=cleaned.strip(),
        sources=cited,
        stripped_citations=stripped,
        verified_ratio=verified_ratio,
        ok=len(stripped) == 0,
    )
