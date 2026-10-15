"""检索产品化 API：法规检索（混合检索 + 向量）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories.vector_store import get_store
from app.schemas.search import LawHitOut, LawSearchOut
from app.services.hybrid_retrieve import hybrid_search

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/laws/search", response_model=LawSearchOut)
def search_laws(
    q: str = Query(..., min_length=1, max_length=200, description="检索式或问题"),
    top_k: int = Query(8, ge=1, le=30),
    _: dict = Depends(get_current_user),
) -> LawSearchOut:
    """法规条款检索：走 BM25 + 稠密向量 + 条款精确 + 重排（与 RAG 问答同链路）。"""
    query = q.strip()
    if not query:
        raise AppError("检索词不能为空", 400)

    store = get_store()
    store.load()
    hits = hybrid_search(query, top_k=top_k)
    items = [
        LawHitOut(
            id=h.get("id") or "",
            doc_id=h.get("doc_id") or "",
            title=h.get("title") or "",
            category=h.get("category") or "",
            article=h.get("article") or "",
            page=int(h.get("page") or 0),
            text=h.get("text") or "",
            score=float(h.get("score") or 0),
            match=h.get("match"),
            rrf_score=h.get("rrf_score"),
            effective_status=h.get("effective_status") or "",
            effective_detail=h.get("effective_detail") or "",
            bian=h.get("bian") or "",
            chapter=h.get("chapter") or "",
            section=h.get("section") or "",
        )
        for h in hits
    ]
    return LawSearchOut(query=query, backend="hybrid", total=len(items), items=items)
