"""入库管线：扫描知识库目录 → 解析（含 OCR）→ 切块 → 时效检测 → 向量化 → 存入向量库。

Phase 2 增强：
- PDF 扫描件自动 OCR（RapidOCR）；
- 入库时为每个文档计算法规效力状态（现行有效/已废止/已修订/部分失效）。
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.repositories.vector_store import get_store
from app.services.chunker import chunk_document, parse_document
from app.services.effective import detect_status
from app.services.embeddings import embed_texts

logger = logging.getLogger("ingest")

SUPPORTED_SUFFIXES = {".docx", ".pdf", ".txt", ".md", ".markdown"}


def iter_documents(kb_root: Path, limit: int | None = None, category: str | None = None):
    """遍历知识库目录下的受支持文档。"""
    files = sorted(
        p for p in kb_root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if category:
        files = [p for p in files if p.relative_to(kb_root).parts[0] == category]
    if limit is not None:
        files = files[:limit]
    return files


def ingest_documents(
    kb_root: Path,
    limit: int | None = None,
    category: str | None = None,
    progress_cb=None,
) -> dict:
    """入库主函数。返回统计信息。"""
    store = get_store()
    store.load()

    files = iter_documents(kb_root, limit=limit, category=category)
    total = len(files)
    logger.info("开始入库：共 %d 个文件（limit=%s, category=%s）", total, limit, category)

    stats = {
        "total_files": total,
        "parsed_ok": 0,
        "parsed_fail": 0,
        "chunks_added": 0,
        "chunks_skipped": 0,
        "ocr_pages": 0,
        "status_counts": {},
        "errors": [],
    }

    def add_doc(path: Path, doc, chunks: list) -> None:
        """单个文档：检测效力状态 → 向量化 → 入库。"""
        if not chunks:
            return
        # 效力状态检测：基于标题 + 前几段正文
        head = "\n".join(doc.paragraphs[:6])
        body = "\n".join(doc.paragraphs)
        status = detect_status(doc.title, head, body)
        doc_meta = {
            "effective_status": status.status,
            "effective_detail": status.detail,
            "effective_evidence": status.evidence[:2],
        }
        stats["status_counts"][status.status] = stats["status_counts"].get(status.status, 0) + 1
        stats["ocr_pages"] += doc.meta.get("ocr_pages", 0)

        vectors = embed_texts([c.text for c in chunks])
        added = store.add_chunks(chunks, vectors=vectors, doc_meta=doc_meta)
        stats["chunks_added"] += added
        stats["chunks_skipped"] += len(chunks) - added

    for done, path in enumerate(files, start=1):
        try:
            doc = parse_document(path, kb_root)
            chunks = chunk_document(doc)
            stats["parsed_ok"] += 1
            add_doc(path, doc, chunks)
        except Exception as exc:  # noqa: BLE001
            stats["parsed_fail"] += 1
            stats["errors"].append({"file": str(path), "error": str(exc)})
            logger.warning("解析失败 %s: %s", path, exc)
        if progress_cb and done % 10 == 0:
            progress_cb(done, total)

    if progress_cb:
        progress_cb(done, total)

    logger.info("入库完成：ok=%d fail=%d chunks=%d ocr_pages=%d",
                stats["parsed_ok"], stats["parsed_fail"], stats["chunks_added"], stats["ocr_pages"])
    return stats


def ingest_single_file(path: Path, kb_root: Path, category: str = "上传文档") -> dict:
    """入库单个文件（文档上传用）。返回 {chunks, doc_id, status, ocr_pages, error?}。"""
    store = get_store()
    store.load()
    try:
        doc = parse_document(path, kb_root)
        chunks = chunk_document(doc)
        head = "\n".join(doc.paragraphs[:6])
        body = "\n".join(doc.paragraphs)
        status = detect_status(doc.title, head, body)
        doc_meta = {
            "effective_status": status.status,
            "effective_detail": status.detail,
            "effective_evidence": status.evidence[:2],
        }
        vectors = embed_texts([c.text for c in chunks])
        added = store.add_chunks(chunks, vectors=vectors, doc_meta=doc_meta)
        return {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "category": doc.category,
            "chunks_added": added,
            "status": status.status,
            "ocr_pages": doc.meta.get("ocr_pages", 0),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("单文件入库失败: %s", path)
        return {"error": str(exc)}


if __name__ == "__main__":
    import sys

    from app.core.config import settings

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings.ensure_dirs()
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    cat_arg = sys.argv[2] if len(sys.argv) > 2 else None
    result = ingest_documents(settings.kb_source_dir, limit=limit_arg, category=cat_arg)
    print(result)
