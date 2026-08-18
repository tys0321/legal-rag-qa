"""OCR 服务：基于 RapidOCR（onnxruntime）识别扫描件 PDF。

惰性加载模型，首次使用下载；识别失败/未启用时回退文本模式。
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger("service.ocr")


@lru_cache(maxsize=1)
def get_ocr() -> Any | None:
    """惰性加载 RapidOCR 引擎；不可用时返回 None。"""
    if not settings.ocr_enabled:
        return None
    try:
        from rapidocr_onnxruntime import RapidOCR

        logger.info("初始化 RapidOCR…")
        engine = RapidOCR()
        logger.info("RapidOCR 就绪")
        return engine
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR 初始化失败，回退文本模式: %s", exc)
        return None


def ocr_image(image_bytes: bytes) -> list[str]:
    """识别单张图片，返回文本行列表。"""
    engine = get_ocr()
    if engine is None:
        return []
    try:
        result, _ = engine(image_bytes)
        if not result:
            return []
        # result: [[box, text, score], ...]
        return [str(row[1]) for row in result if len(row) >= 2 and row[1]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR 单页识别失败: %s", exc)
        return []


def ocr_pdf_page(page: Any) -> list[str]:
    """对 pdfplumber 页面对象做 OCR（渲染为图片后识别）。"""
    engine = get_ocr()
    if engine is None:
        return []
    try:
        # 高 DPI 渲染保证识别质量
        img = page.to_image(resolution=220)
        pil_img = img.original.convert("RGB")
        # 用 numpy 转换到内存，避免依赖 PIL 的 png 编码器
        import io

        import numpy as np

        arr = np.asarray(pil_img)
        buf = io.BytesIO()
        np.save(buf, arr, allow_pickle=False)
        # RapidOCR 直接接收 ndarray 或 bytes
        return ocr_array(arr)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR 页面渲染失败: %s", exc)
        return []


def ocr_array(arr) -> list[str]:
    """识别 numpy 数组图像。"""
    engine = get_ocr()
    if engine is None:
        return []
    try:
        result, _ = engine(arr)
        if not result:
            return []
        return [str(row[1]) for row in result if len(row) >= 2 and row[1]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR 数组识别失败: %s", exc)
        return []
