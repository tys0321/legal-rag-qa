"""向量化模块：使用 fastembed 加载本地中文嵌入模型（BGE 系列）。

免费、离线、无 token 成本。模型缓存固定到项目内 data/models 目录，
首次使用会从网络下载，之后完全离线。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT, settings

# 固定到仓库 data/models（Compose 挂载 /app/data，可持久化）
FASTEMBED_CACHE = PROJECT_ROOT / "data" / "models"
FASTEMBED_CACHE.mkdir(parents=True, exist_ok=True)
os.environ["FASTEMBED_CACHE_PATH"] = str(FASTEMBED_CACHE)


# fastembed 实际从 Qdrant 的 ONNX 仓库拉模型，缓存目录名与配置名不同
_HF_CACHE_REPO = {
    "BAAI/bge-small-zh-v1.5": "Qdrant/bge-small-zh-v1.5",
}


def _cache_repo(model_name: str) -> str:
    return _HF_CACHE_REPO.get(model_name, model_name)


def _hf_cache_dir_name(repo_id: str) -> str:
    """HuggingFace hub 风格缓存目录名。"""
    return "models--" + repo_id.replace("/", "--")


def _file_big_enough(path: Path, min_bytes: int = 1_000_000) -> bool:
    """Windows 上 HuggingFace 符号链接可能无法 stat，忽略这类路径。"""
    try:
        return path.is_file() and path.stat().st_size > min_bytes
    except OSError:
        return False


def _has_local_model_files(model_name: str | None = None) -> bool:
    """当前配置模型的 fastembed 缓存里是否已有完整 onnx。"""
    name = model_name or settings.embedding_model
    root = FASTEMBED_CACHE / _hf_cache_dir_name(_cache_repo(name))
    if not root.exists():
        return False
    blobs = root / "blobs"
    if blobs.exists():
        for path in blobs.iterdir():
            if _file_big_enough(path):
                return True
    return any(_file_big_enough(path) for path in root.rglob("model_optimized.onnx"))


if _has_local_model_files():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
else:
    os.environ.pop("HF_HUB_OFFLINE", None)


def is_embedder_ready() -> bool:
    """本地已有当前配置模型时才做稠密检索（不触发下载）。"""
    return _has_local_model_files()


@lru_cache(maxsize=1)
def get_embedder() -> Any:
    """惰性加载嵌入模型（进程内只加载一次）。缓存齐全时强制离线，避免联网重试。"""
    from fastembed import TextEmbedding

    kwargs: dict[str, Any] = {"cache_dir": str(FASTEMBED_CACHE)}
    if is_embedder_ready():
        kwargs["local_files_only"] = True
    return TextEmbedding(model_name=settings.embedding_model, **kwargs)


def embed_texts(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """批量计算文本向量。"""
    if not texts:
        return []
    if not is_embedder_ready():
        raise RuntimeError(
            "嵌入模型未就绪：请将 BGE 模型放到 data/models，或运行 scripts/ingest_eval_core.py"
        )
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
