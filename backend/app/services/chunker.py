"""文档解析与切块模块。

支持 .docx / .pdf / .txt / .md 格式。
切块策略对法律文档做了专门优化：
- 优先识别「第X条」「第X章」等结构标记，以条款为切块边界；
- 保留每个块的元数据（来源文件、分类、文件名、页码、条款号）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ARTICLE_RE = re.compile(r"^\s*(第[一二三四五六七八九十百千0-9]+[条章节编])\s*(.*)$")
LINE_BREAK_RE = re.compile(r"[ \t\u3000]+")
STRUCT_RE = re.compile(r"^\s*(第[一二三四五六七八九十百千0-9]+[编章节条])\s*")

# 立法套话 / 目录等对检索无用的行（入库时剔除，缩短块长、加快检索与生成）
_BOILERPLATE_RES = [
    re.compile(r"^为了.{2,120}?(制定|修订)本[法条例办法规定规则]"),
    re.compile(r"^为保障.{2,80}制定本"),
    re.compile(r"^为规范.{2,80}制定本"),
    re.compile(r"^根据宪法[，,].{0,60}制定本"),
    re.compile(r"^根据《[^》]+》[，,].{0,60}制定本"),
    re.compile(r"^依据《[^》]+》[，,].{0,60}制定本"),
    re.compile(r"^目\s*录$"),
    re.compile(r"^目\s*次$"),
    re.compile(r"^（?[一二三四五六七八九十]+）?\s*总\s*则\s*$"),
    re.compile(r"^发布机关[:：]"),
    re.compile(r"^主\s*席\s*令"),
    re.compile(r"^中华人民共和国主席令"),
    re.compile(r"^现予公布"),
    re.compile(r"^自\d{4}年\d{1,2}月\d{1,2}日起施行[。.]?$"),
    re.compile(r"^\d{4}年\d{1,2}月\d{1,2}日.*(通过|公布|修正|修订)"),
    re.compile(r"^(第[一二三四五六七八九十百]+届)?.{0,20}人民代表大会.{0,30}(通过|决定)"),
    re.compile(r"^（?[0-9]{4}年修订）?$"),
    re.compile(r"^本法自.+起施行[。.]?$"),
    re.compile(r"^本条例自.+起施行[。.]?$"),
]


def is_boilerplate(para: str) -> bool:
    """判断是否为立法套话 / 目录等可丢弃行。含「第×条」的正文一律保留。"""
    t = (para or "").strip()
    if not t:
        return True
    if STRUCT_RE.match(t) and ("条" in t[:8] or "章" in t[:8] or "节" in t[:8] or "编" in t[:8]):
        # 结构标题本身保留（条尤为重要）
        if t.endswith("条") or "条" in t[:12]:
            return False
    for pat in _BOILERPLATE_RES:
        if pat.search(t):
            return True
    # 过短且像页眉页脚
    if len(t) <= 4 and t in {"目录", "目次", "附录", "附则"}:
        return True
    return False


def filter_boilerplate(
    paras: list[str], pages: list[int]
) -> tuple[list[str], list[int]]:
    out_p: list[str] = []
    out_pg: list[int] = []
    for p, pg in zip(paras, pages):
        if is_boilerplate(p):
            continue
        out_p.append(p)
        out_pg.append(pg)
    return out_p, out_pg


@dataclass
class Chunk:
    """知识库中的一个检索单元。"""

    text: str
    doc_id: str              # 文档唯一 ID（相对路径）
    title: str               # 文件名（不含扩展名）
    category: str            # 一级分类目录名
    article: str = ""        # 条款号，如「第三十九条」
    page: int = 0            # 页码（PDF）
    chunk_index: int = 0     # 块序号
    bian: str = ""           # 编
    chapter: str = ""        # 章
    section: str = ""        # 节
    meta: dict = field(default_factory=dict)


@dataclass
class ParsedDoc:
    """解析结果：段落列表 + 页面信息。"""

    doc_id: str
    title: str
    category: str
    paragraphs: list[str] = field(default_factory=list)
    page_of_para: list[int] = field(default_factory=list)  # 每段所在页码
    meta: dict = field(default_factory=dict)


def detect_category(path: Path, kb_root: Path) -> str:
    """根据一级目录名推断分类，如 宪法/法律/行政法规/司法解释。"""
    try:
        rel = path.relative_to(kb_root)
        parts = rel.parts
        if len(parts) >= 2:
            return parts[0]
        return "未分类"
    except ValueError:
        return "未分类"


def _norm(text: str) -> str:
    return LINE_BREAK_RE.sub(" ", text).strip()


def parse_docx(path: Path, kb_root: Path) -> ParsedDoc:
    import docx  # python-docx

    doc = docx.Document(str(path))
    paras: list[str] = []
    for p in doc.paragraphs:
        t = _norm(p.text)
        if t:
            paras.append(t)
    # 表格内容也提取（法规常有表格）
    for table in doc.tables:
        for row in table.rows:
            cells = [_norm(c.text) for c in row.cells if _norm(c.text)]
            if cells:
                paras.append(" | ".join(cells))
    rel = path.relative_to(kb_root) if path.is_relative_to(kb_root) else path
    return ParsedDoc(
        doc_id=rel.as_posix(),
        title=path.stem,
        category=detect_category(path, kb_root),
        paragraphs=paras,
        page_of_para=[0] * len(paras),
    )


def parse_pdf(path: Path, kb_root: Path, use_ocr: bool = True) -> ParsedDoc:
    """解析 PDF。

    优先提取文本层；若某页无文本（扫描件），且启用 OCR，则自动用 RapidOCR 识别。
    """
    import pdfplumber

    from app.core.config import settings
    from app.services.ocr import ocr_pdf_page

    paras: list[str] = []
    pages: list[int] = []
    ocr_pages = 0
    with pdfplumber.open(str(path)) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = [_norm(l) for l in text.splitlines() if _norm(l)]
            if not lines and use_ocr and settings.ocr_enabled and not page.images == []:
                # 扫描页：走 OCR
                ocr_lines = ocr_pdf_page(page)
                lines = [_norm(l) for l in ocr_lines if _norm(l)]
                if lines:
                    ocr_pages += 1
            for line in lines:
                paras.append(line)
                pages.append(pno)
    rel = path.relative_to(kb_root) if path.is_relative_to(kb_root) else path
    return ParsedDoc(
        doc_id=rel.as_posix(),
        title=path.stem,
        category=detect_category(path, kb_root),
        paragraphs=paras,
        page_of_para=pages,
        meta={"ocr_pages": ocr_pages},
    )


def parse_txt(path: Path, kb_root: Path) -> ParsedDoc:
    content = path.read_text(encoding="utf-8", errors="ignore")
    paras = [_norm(p) for p in content.splitlines() if _norm(p)]
    rel = path.relative_to(kb_root) if path.is_relative_to(kb_root) else path
    return ParsedDoc(
        doc_id=rel.as_posix(),
        title=path.stem,
        category=detect_category(path, kb_root),
        paragraphs=paras,
        page_of_para=[0] * len(paras),
    )


def parse_document(path: Path, kb_root: Path) -> ParsedDoc:
    """按扩展名分发解析。"""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return parse_docx(path, kb_root)
    if suffix == ".pdf":
        return parse_pdf(path, kb_root)
    if suffix in (".txt", ".md", ".markdown"):
        return parse_txt(path, kb_root)
    raise ValueError(f"不支持的格式: {suffix}")


def _split_articles(
    paras: list[str], pages: list[int]
) -> list[tuple[str, str, int, str, str, str]]:
    """按编/章/节/条切分，返回 (文本, 条, 页码, 编, 章, 节)。"""
    groups: list[tuple[list[str], str, int, str, str, str]] = []
    cur: list[str] = []
    cur_article = ""
    cur_page = 0
    cur_bian = ""
    cur_chapter = ""
    cur_section = ""

    def flush() -> None:
        nonlocal cur
        if cur:
            groups.append(("".join(cur), cur_article, cur_page, cur_bian, cur_chapter, cur_section))
            cur = []

    for para, page in zip(paras, pages):
        sm = STRUCT_RE.match(para)
        if sm:
            label = sm.group(1)
            if label.endswith("编"):
                flush()
                cur_bian, cur_chapter, cur_section, cur_article = label, "", "", ""
                cur_page = page
                cur.append(para)
                continue
            if label.endswith("章"):
                flush()
                cur_chapter, cur_section, cur_article = label, "", ""
                cur_page = page
                cur.append(para)
                continue
            if label.endswith("节"):
                flush()
                cur_section, cur_article = label, ""
                cur_page = page
                cur.append(para)
                continue
            if label.endswith("条"):
                flush()
                cur_article = label
                cur_page = page
                cur.append(para)
                continue
        cur.append(para)
    flush()
    return [(t, a, p, b, c, s) for t, a, p, b, c, s in groups if len(t) >= 5]


def chunk_document(doc: ParsedDoc, chunk_size: int = 600, overlap: int = 80) -> list[Chunk]:
    """把解析后的文档切成检索块。

    优先按「编-章-节-条」聚合；条款过长时按 chunk_size 硬切并保留 overlap。
    """
    chunks: list[Chunk] = []
    idx = 0
    paras, pages = filter_boilerplate(doc.paragraphs, doc.page_of_para)
    for text, article, page, bian, chapter, section in _split_articles(paras, pages):
        text = text.strip()
        if not text:
            continue
        common = dict(
            doc_id=doc.doc_id,
            title=doc.title,
            category=doc.category,
            article=article,
            page=page,
            bian=bian,
            chapter=chapter,
            section=section,
        )
        if len(text) <= chunk_size * 1.3:
            chunks.append(Chunk(text=text, chunk_index=idx, **common))
            idx += 1
        else:
            step = chunk_size - overlap
            start = 0
            while start < len(text):
                seg = text[start : start + chunk_size]
                chunks.append(Chunk(text=seg, chunk_index=idx, **common))
                idx += 1
                start += step
                if len(seg) < chunk_size:
                    break
    return chunks
