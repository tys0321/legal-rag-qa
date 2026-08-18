"""RAG 引用解析与回答结构测试。"""
from __future__ import annotations

from app.services.rag import _build_context, _extract_citations


def test_extract_citations_dedup_ordered() -> None:
    answer = "根据[3]和[1]以及[3]的规定，同时参考[2]。"
    assert _extract_citations(answer) == [3, 1, 2]


def test_extract_citations_empty() -> None:
    assert _extract_citations("没有引用标注的回答") == []


def test_build_context_numbering() -> None:
    sources = [
        {"title": "宪法", "article": "第三十五条", "page": 3, "text": "公民有言论自由"},
        {"title": "劳动法", "article": "", "page": 0, "text": "劳动者享有平等就业权"},
    ]
    ctx = _build_context(sources)
    assert "[1] 来源：《宪法（第三十五条） 第3页》" in ctx
    assert "[2] 来源：《劳动法》" in ctx
    assert "公民有言论自由" in ctx
