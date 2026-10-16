"""检索产品化 API：法规检索 / 类案检索（真实向量链路）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.repositories.vector_store import get_store
from app.schemas.search import CaseHitOut, CaseSearchOut, LawHitOut, LawSearchOut
from app.services.hybrid_retrieve import hybrid_search
from app.services.lexical_kb import lexical_search

router = APIRouter(prefix="/api", tags=["search"])

_CASE_NOTICE = (
    "以下为司法解释、批复、指导性文件等类案参考材料；"
    "知识库无裁判文书全文时，不展示为「法院判决书原文」。"
)


def _case_kind(title: str, category: str) -> str:
    t = title or ""
    c = category or ""
    if "指导案例" in t or "公报" in t:
        return "guiding_case"
    if "批复" in t or "答复" in t:
        return "reply"
    if "决定" in t:
        return "decision"
    if c == "司法解释" or "解释" in t:
        return "judicial_interp"
    if c in ("裁判文书", "案例"):
        return "guiding_case"
    return "reference"


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
    backend = "hybrid"
    try:
        hits = hybrid_search(query, top_k=top_k) if store.stats().get("chunk_count", 0) else []
    except Exception:  # noqa: BLE001
        hits = []
    if hits and hits[0].get("match") == "lexical":
        backend = "lexical"
    elif not hits:
        hits = lexical_search(query, top_k=top_k)
        backend = "lexical"
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
    return LawSearchOut(query=query, backend=backend, total=len(items), items=items)


@router.get("/cases/search", response_model=CaseSearchOut)
def search_cases(
    q: str = Query(..., min_length=1, max_length=200, description="问题或检索式"),
    top_k: int = Query(6, ge=1, le=20),
    _: dict = Depends(get_current_user),
) -> CaseSearchOut:
    """类案/司法解释检索：稠密向量召回 + 案例特征过滤（与问答 related_cases 同源）。"""
    query = q.strip()
    if not query:
        raise AppError("检索词不能为空", 400)

    store = get_store()
    store.load()
    hits = store.search_cases(query, top_k=top_k)
    items = [
        CaseHitOut(
            id=h.get("id") or "",
            doc_id=h.get("doc_id") or "",
            title=h.get("title") or "",
            category=h.get("category") or "",
            article=h.get("article") or "",
            page=int(h.get("page") or 0),
            text=h.get("text") or "",
            score=float(h.get("score") or 0),
            kind=_case_kind(h.get("title") or "", h.get("category") or ""),
        )
        for h in hits
    ]
    return CaseSearchOut(
        query=query,
        backend="vector_cases",
        total=len(items),
        notice=_CASE_NOTICE,
        items=items,
    )
