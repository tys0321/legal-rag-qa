"""知识库/文档相关请求响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    doc_id: str
    title: str
    category: str
    chunks: int
    effective_status: str = ""
    effective_detail: str = ""


class DocumentListResponse(BaseModel):
    documents: list[DocumentItem]


class UploadResponse(BaseModel):
    ok: bool
    doc_id: str | None = None
    title: str | None = None
    category: str | None = None
    chunks_added: int = 0
    status: str = ""
    ocr_pages: int = 0
    pending: bool = False
    error: str | None = None


class DeleteRequest(BaseModel):
    doc_id: str


class DeleteResponse(BaseModel):
    ok: bool
    removed_chunks: int = 0


class IngestRequest(BaseModel):
    limit: int | None = Field(None, ge=1, description="限制入库文件数")
    category: str | None = Field(None, description="按一级分类入库")


class IngestResponse(BaseModel):
    started: bool
    note: str


class StatsDoc(BaseModel):
    title: str
    category: str
    chunks: int


class StatsResponse(BaseModel):
    chunk_count: int
    doc_count: int
    docs: dict[str, StatsDoc]
