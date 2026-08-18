"""向量化模块：使用 fastembed 加载本地中文嵌入模型（BGE 系列）。

免费、离线、无 token 成本。模型缓存固定到项目内 data/models 目录，
首次使用会从网络下载，之后完全离线。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings

# fastembed 默认把模型缓存在系统 TEMP，不稳定；固定到项目内目录
FASTEMBED_CACHE = Path(__file__).resolve().parent.parent.parent / "data" / "models"
FASTEMBED_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["FASTEMBED_CACHE_PATH"] = str(FASTEMBED_CACHE)
# 模型已缓存则强制离线，避免每次启动都尝试联网导致超时等待
os.environ.setdefault("HF_HUB_OFFLINE", "1")


@lru_cache(maxsize=1)
def get_embedder() -> Any:
    """惰性加载嵌入模型（进程内只加载一次）。"""
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """批量计算文本向量。"""
    if not texts:
        return []
    embedder = get_embedder()
    vectors: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        for emb in embedder.embed(batch):
            vectors.append(emb.tolist())
    return vectors


def embed_query(text: str) -> list[float]:
    """计算单个查询向量。"""
    return embed_texts([text])[0]


def embedding_dim() -> int:
    """查询当前模型的向量维度（用于初始化索引）。"""
    embedder = get_embedder()
    return embedder.model.model.config.hidden_size
