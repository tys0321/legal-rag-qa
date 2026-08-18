"""知识库服务层：封装文档管理业务逻辑。"""
from __future__ import annotations

import logging
import threading
import uuid
from pathlib import Path

from app.core.config import settings
from app.repositories.vector_store import VectorStore, get_store
from app.services.ingest import ingest_documents, ingest_single_file

logger = logging.getLogger("service.documents")

ALLOWED_UPLOAD_SUFFIXES = {".docx", ".pdf", ".txt", ".md", ".markdown"}


class DocumentService:
    """文档列表 / 统计 / 后台入库 / 上传 / 删除。"""

    def __init__(self, store: VectorStore | None = None) -> None:
        self.store = store or get_store()

    def list_documents(self) -> list[dict]:
        return self.store.doc_list()

    def stats(self) -> dict:
        return self.store.stats()

    def start_ingest(self, limit: int | None = None, category: str | None = None) -> str:
        """启动后台入库线程，立即返回提示。"""

        def worker() -> None:
            try:
                ingest_documents(
                    settings.kb_source_dir,
                    limit=limit,
                    category=category,
                    progress_cb=None,
                )
            except Exception:  # noqa: BLE001
                logger.exception("后台入库失败")

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return "入库任务已在后台启动，可通过 /api/stats 查看进度。"

    def upload_file(self, filename: str, content: bytes) -> dict:
        """保存上传文件到 upload_dir，立即返回；入库在后台线程执行。"""
        filename = self._fix_filename(filename)
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_UPLOAD_SUFFIXES:
            return {"error": f"不支持的格式: {suffix}（支持 docx/pdf/txt/md）"}
        # 大小限制：50MB（防止超大文件拖垮内存/磁盘）
        if len(content) > 50 * 1024 * 1024:
            return {"error": "文件超过 50MB 限制"}

        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
        target = settings.upload_dir / safe_name
        target.write_bytes(content)

        # 后台异步入库（大文件向量化耗时，不阻塞请求）
        def worker() -> None:
            try:
                result = ingest_single_file(target, settings.upload_dir, category="上传文档")
                if "error" in result:
                    logger.warning("后台入库失败 %s: %s", target.name, result["error"])
                    target.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                logger.exception("后台入库异常 %s", target)
                target.unlink(missing_ok=True)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

        rel_id = target.relative_to(settings.upload_dir).as_posix()
        return {
            "doc_id": rel_id,
            "title": target.stem,
            "category": "上传文档",
            "chunks_added": 0,
            "status": "",
            "ocr_pages": 0,
            "pending": True,
            "file_path": str(target),
        }

    @staticmethod
    def _fix_filename(name: str) -> str:
        """修复中文文件名编码错乱。

        两种常见变体：
        A) UTF-8 字节被 latin-1 解码（ÖÐ»ªÈËÃñ…）
        B) GBK 字节被 UTF-8 解码（ÑéÊÕ²âÊÔ…）
        """
        # 变体 B：GBK → 错误 UTF-8。特征：含 Ã/Ê/Ñ/Õ/²/â/Ô 等且尝试 utf-8 解码失败
        try:
            raw = name.encode("utf-8", errors="strict")
            # 若原始字符串含 GBK mojibake 特征字符，尝试用 gbk 解释原始字节
            if any(c in name for c in ("Ã", "Ê", "Ñ", "Õ", "â", "Ô", "²", "é", "ê")):
                fixed_b = name.encode("latin-1", errors="strict").decode("gbk", errors="strict")
                # 变体 B 实际上 latin-1 编码不适用，尝试 cp1252
                fixed_c = name.encode("cp1252", errors="strict").decode("gbk", errors="strict")
                candidate = fixed_c if "Ã" not in fixed_c else fixed_b
                if candidate != name and "\ufffd" not in candidate:
                    return candidate
        except Exception:  # noqa: BLE001
            pass
        # 变体 A：UTF-8 被 latin-1 解码（ÖÐ»ªÈËÃñ…）
        try:
            if any(c in name for c in ("Ö", "ª", "¹", "Ã", "Ð", "Ë")):
                fixed = name.encode("latin-1", errors="strict").decode("gbk", errors="strict")
                if fixed != name:
                    return fixed
        except Exception:  # noqa: BLE001
            pass
        return name

    def delete_document(self, doc_id: str) -> int:
        """从向量库删除文档的全部块。返回删除块数。"""
        removed = self.store.remove_doc(doc_id)
        # 若文件在 upload_dir 内，同步删除物理文件
        try:
            p = Path(doc_id)
            if p.is_absolute() or (settings.upload_dir / p).exists():
                (settings.upload_dir / p).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            logger.warning("删除物理文件失败: %s", doc_id)
        return removed


_doc_service: DocumentService | None = None


def get_document_service() -> DocumentService:
    global _doc_service
    if _doc_service is None:
        _doc_service = DocumentService()
    return _doc_service
