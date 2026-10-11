"""M1：混合检索 / 引用验证 / 分块结构 / 置信度。"""
from __future__ import annotations

from app.services.bm25_index import tokenize
from app.services.chunker import ParsedDoc, chunk_document
from app.services.citation_verify import verify_answer
from app.services.critic import confidence_label
from app.services.hybrid_retrieve import _rrf_fuse
from app.services.rerank import _heuristic_rerank


def test_tokenize_zh() -> None:
    toks = tokenize("劳动合同法第三十九条 用人单位可以解除合同")
    assert any("劳动" in t or "合同" in t for t in toks)
    assert any("三十九" in t or "第" in t for t in toks)


def test_rrf_prefers_multi_channel_hits() -> None:
    a = [{"id": "x", "score": 1, "match": "article", "title": "t", "text": "a"}]
    b = [{"id": "x", "score": 0.9, "match": "vector", "title": "t", "text": "a"}]
    c = [{"id": "y", "score": 0.8, "match": "bm25", "title": "t2", "text": "b"}]
    fused = _rrf_fuse([a, b, c])
    assert fused[0]["id"] == "x"
    assert "article" in fused[0]["match"] and "vector" in fused[0]["match"]


def test_citation_verify_strips_invalid_index() -> None:
    hits = [
        {
            "id": "1",
            "title": "中华人民共和国劳动合同法",
            "article": "第三十条",
            "text": "用人单位应当按照劳动合同约定和国家规定，向劳动者及时足额支付劳动报酬。",
            "doc_id": "d1",
            "category": "法律",
            "page": 0,
            "score": 1.0,
        }
    ]
    ans = "根据《中华人民共和国劳动合同法》第三十条，应及时支付报酬[1]。另见虚假条款[9]。"
    vr = verify_answer(ans, hits)
    assert "[9]" not in vr.answer
    assert "[1]" in vr.answer
    assert vr.sources


def test_citation_verify_flags_unknown_law() -> None:
    hits = [
        {
            "id": "1",
            "title": "中华人民共和国劳动法",
            "article": "第三条",
            "text": "劳动者享有平等就业和选择职业的权利。",
            "doc_id": "d1",
            "category": "法律",
            "page": 0,
            "score": 1.0,
        }
    ]
    ans = "依据《完全不存在的法》第九百九十九条可以怎么做[1]。"
    vr = verify_answer(ans, hits)
    assert vr.stripped_citations or "待核实" in vr.answer


def test_chunker_tracks_chapter_article() -> None:
    doc = ParsedDoc(
        doc_id="demo.docx",
        title="示范法",
        category="法律",
        paragraphs=["第一章 总则", "第一条 为了保护劳动者合法权益，制定本法。", "第二条 适用范围。"],
        page_of_para=[1, 1, 1],
    )
    chunks = chunk_document(doc, chunk_size=600, overlap=80)
    arts = [c for c in chunks if c.article.startswith("第") and c.article.endswith("条")]
    assert arts
    assert any(c.chapter == "第一章" for c in arts)


def test_heuristic_rerank_boosts_article_match() -> None:
    cands = [
        {
            "id": "a",
            "title": "中华人民共和国劳动合同法",
            "article": "第三十九条",
            "text": "用人单位可以解除劳动合同",
            "rrf_score": 0.01,
            "match": "article",
            "effective_status": "现行有效",
        },
        {
            "id": "b",
            "title": "无关条例",
            "article": "",
            "text": "公园管理规定",
            "rrf_score": 0.02,
            "match": "bm25",
            "effective_status": "",
        },
    ]
    out = _heuristic_rerank("劳动合同法第三十九条", cands, top_k=2)
    assert out[0]["id"] == "a"


def test_confidence_low_without_hits() -> None:
    assert confidence_label(hits=[], verified_ratio=1.0, critic_ok=True, stripped=[]) == "low"
