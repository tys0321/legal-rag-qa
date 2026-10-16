"""向量库为空时的词面检索兜底。"""
from __future__ import annotations

from app.services.lexical_kb import lexical_search, load_docs


def test_eval_core_loads_and_hits_labor() -> None:
    docs = load_docs(force=True)
    assert len(docs) >= 5
    hits = lexical_search("公司拖欠工资，劳动合同怎么维权", top_k=5)
    assert hits
    blob = " ".join(h["title"] for h in hits)
    assert "劳动合同" in blob or "劳动" in blob
