"""知识库管理路由（瘦路由）：文档列表 / 统计 / 后台入库 / 上传 / 删除。"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.core.errors import AppError
from app.schemas.document import (
    DeleteRequest,
    DeleteResponse,
    DocumentItem,
    DocumentListResponse,
    IngestRequest,
    IngestResponse,
    StatsResponse,
    UploadResponse,
)
from app.services.document_service import get_document_service

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    try:
        docs = get_document_service().list_documents()
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"获取文档列表失败: {exc}", 500) from exc
    return DocumentListResponse(documents=[DocumentItem(**d) for d in docs])


@router.get("/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    try:
        data = get_document_service().stats()
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"获取统计失败: {exc}", 500) from exc
    return StatsResponse(
        chunk_count=data["chunk_count"],
        doc_count=data["doc_count"],
        docs=data["docs"],
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest_endpoint(req: IngestRequest) -> IngestResponse:
    note = get_document_service().start_ingest(limit=req.limit, category=req.category)
    return IngestResponse(started=True, note=note)


@router.post("/upload", response_model=UploadResponse)
async def upload_endpoint(file: UploadFile = File(...)) -> UploadResponse:
    """上传单个文档并入库。支持 docx/pdf/txt/md。"""
    content = await file.read()
    if not content:
        raise AppError("文件为空", 400)
    result = get_document_service().upload_file(file.filename or "upload.bin", content)
    if "error" in result:
        raise AppError(result["error"], 400)
    return UploadResponse(
        ok=True,
        doc_id=result.get("doc_id"),
        title=result.get("title"),
        category=result.get("category"),
        chunks_added=result.get("chunks_added", 0),
        status=result.get("status", ""),
        ocr_pages=result.get("ocr_pages", 0),
        pending=result.get("pending", False),
    )


@router.post("/delete", response_model=DeleteResponse)
def delete_endpoint(req: DeleteRequest) -> DeleteResponse:
    try:
        removed = get_document_service().delete_document(req.doc_id)
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"删除失败: {exc}", 500) from exc
    return DeleteResponse(ok=True, removed_chunks=removed)
