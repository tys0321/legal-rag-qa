"""混合检索：条款精确匹配 + 稠密向量 + BM25，RRF 融合。"""
from __future__ import annotations

from collections import defaultdict

from app.core.config import settings
from app.repositories.vector_store import get_store
from app.services.bm25_index import get_bm25_index
from app.services.rerank import rerank_candidates


def _rrf_fuse(
    ranked_lists: list[list[dict]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[dict]:
    """倒数排名融合。"""
    weights = weights or [1.0] * len(ranked_lists)
    scores: dict[str, float] = defaultdict(float)
    payload: dict[str, dict] = {}
    match_tags: dict[str, set[str]] = defaultdict(set)

    for w, lst in zip(weights, ranked_lists):
        for rank, item in enumerate(lst, start=1):
            cid = item["id"]
            scores[cid] += w * (1.0 / (k + rank))
            if cid not in payload:
                payload[cid] = dict(item)
            match_tags[cid].add(item.get("match") or "unknown")
            # 保留更高原始分供调试
            if item.get("score", 0) > payload[cid].get("score", 0):
                payload[cid]["score"] = item["score"]

    ordered = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    out = []
    for cid in ordered:
        row = payload[cid]
        row = dict(row)
        row["rrf_score"] = round(scores[cid], 6)
        row["match"] = "+".join(sorted(match_tags[cid]))
        out.append(row)
    return out


def hybrid_search(query: str, top_k: int | None = None, min_score: float | None = None) -> list[dict]:
    """混合检索 → 重排 → 截断 top_k。"""
    top_k = top_k or settings.retrieve_top_k
    min_score = settings.min_score if min_score is None else min_score
    candidate_k = max(settings.hybrid_candidate_k, top_k)

    store = get_store()
    store.load()
    if not store._vectors:  # noqa: SLF001 — 与仓库内部状态同步
        # 向量库未入库时：词面扫描 data/kb（含 eval_core），保证演示可用
        from app.services.lexical_kb import lexical_search

        return lexical_search(query, top_k=top_k)

    # 条款精确
    article_hits = store._search_by_article(query, top_k=candidate_k)  # noqa: SLF001

    # 稠密：无本地嵌入模型时跳过，避免下载重试卡死
    dense_hits = store.search_dense(query, top_k=candidate_k, min_score=max(0.0, min_score - 0.1))

    # BM25
    bm25 = get_bm25_index()
    bm25.rebuild_if_needed(store._ids, store._metas)  # noqa: SLF001
    bm25_hits = bm25.search(query, top_k=candidate_k)

    # 仅有元数据、稠密不可用且 BM25/条款也无命中时，词面兜底
    if not article_hits and not dense_hits and not bm25_hits:
        from app.services.lexical_kb import lexical_search

        return lexical_search(query, top_k=top_k)

    fused = _rrf_fuse(
        [article_hits, dense_hits, bm25_hits],
        k=60,
        weights=[settings.rrf_weight_article, settings.rrf_weight_dense, settings.rrf_weight_bm25],
    )
    if not fused:
        return []

    # 重排到 top_k
    reranked = rerank_candidates(query, fused, top_k=top_k)

    # 效力状态轻量排序：同分时现行有效优先
    from app.repositories.vector_store import _status_sort_key

    reranked = sorted(reranked, key=lambda r: (_status_sort_key(r), -r.get("rerank_score", r.get("rrf_score", 0))))
    return reranked[:top_k]
