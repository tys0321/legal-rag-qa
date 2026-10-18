"""导出 Word / PDF。"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.errors import AppError
from app.services.export_file import to_docx, to_pdf

router = APIRouter(prefix="/api", tags=["export"])


class ExportRequest(BaseModel):
    title: str = Field("", max_length=200)
    markdown: str = Field(..., min_length=1, max_length=40000)
    format: str = Field(..., pattern="^(docx|pdf)$")


def _filename(title: str, ext: str) -> str:
    name = "".join(ch for ch in (title or "导出文档") if ch not in '\\/:*?"<>|').strip() or "导出文档"
    return f"{name[:80]}.{ext}"


@router.post("/export")
def export_file(req: ExportRequest, _user: dict = Depends(get_current_user)) -> Response:
    title = req.title.strip() or "导出文档"
    if req.format == "docx":
        data = to_docx(title, req.markdown)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    elif req.format == "pdf":
        data = to_pdf(title, req.markdown)
        media = "application/pdf"
        ext = "pdf"
    else:
        raise AppError("仅支持 docx 或 pdf", 400)
    filename = _filename(title, ext)
    disposition = f"attachment; filename*=UTF-8''{quote(filename)}"
    return Response(content=data, media_type=media, headers={"Content-Disposition": disposition})
