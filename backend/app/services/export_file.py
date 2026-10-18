"""把 Markdown 草稿导出为 Word（.docx）或 PDF。"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Pt
from fpdf import FPDF

from app.core.errors import AppError

_FONT_CANDIDATES = [
    Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyh.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def _plain(line: str) -> str:
    text = re.sub(r"^#{1,6}\s*", "", line.strip())
    text = text.replace("**", "").replace("`", "")
    return text


def _blocks(markdown: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for raw in (markdown or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("### "):
            blocks.append(("h3", _plain(stripped)))
        elif stripped.startswith("## "):
            blocks.append(("h2", _plain(stripped)))
        elif stripped.startswith("# "):
            blocks.append(("h1", _plain(stripped)))
        else:
            blocks.append(("p", _plain(stripped)))
    return blocks


def to_docx(title: str, markdown: str) -> bytes:
    doc = Document()
    heading = doc.add_heading(title or "导出文档", level=0)
    for run in heading.runs:
        run.font.size = Pt(18)
    for kind, text in _blocks(markdown):
        if kind == "h1":
            doc.add_heading(text, level=1)
        elif kind == "h2":
            doc.add_heading(text, level=2)
        elif kind == "h3":
            doc.add_heading(text, level=3)
        else:
            doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _find_font() -> Path:
    for path in _FONT_CANDIDATES:
        if path.exists():
            return path
    raise AppError("服务器未安装中文字体，暂时无法导出 PDF", 503)


def to_pdf(title: str, markdown: str) -> bytes:
    font = _find_font()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()
    pdf.add_font("zh", fname=str(font))
    pdf.set_font("zh", size=16)
    pdf.multi_cell(0, 10, title or "导出文档")
    pdf.ln(2)
    for kind, text in _blocks(markdown):
        if kind == "h1":
            pdf.set_font("zh", size=14)
            pdf.multi_cell(0, 9, text)
        elif kind in {"h2", "h3"}:
            pdf.set_font("zh", size=12)
            pdf.multi_cell(0, 8, text)
        else:
            pdf.set_font("zh", size=11)
            pdf.multi_cell(0, 7, text)
        pdf.ln(1)
    return bytes(pdf.output())
