"""法规 / 类案检索响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LawHitOut(BaseModel):
    id: str
    doc_id: str
    title: str
    category: str = ""
    article: str = ""
    page: int = 0
    text: str = ""
    score: float = 0.0
    match: str | None = None
    rrf_score: float | None = None
    effective_status: str = ""
    effective_detail: str = ""
    bian: str = ""
    chapter: str = ""
    section: str = ""


class LawSearchOut(BaseModel):
    query: str
    backend: str = Field("hybrid", description="检索后端：hybrid=BM25+向量+条款+重排")
    total: int
    items: list[LawHitOut]
