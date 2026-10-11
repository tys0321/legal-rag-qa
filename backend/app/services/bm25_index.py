"""BM25 稀疏检索索引（基于知识库 chunk 文本）。

中文用字 bigram + 法条号/英文数字 token，避免强依赖 jieba。
"""
from __future__ import annotations

import re
import threading
from typing import Any

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(
    r"第[一二三四五六七八九十百千0-9]+[条款章节编]|[\u4e00-\u9fff]{2,}|[A-Za-z0-9]{2,}"
)


def tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens = _TOKEN_RE.findall(text)
    if tokens:
        return tokens
    # 极短文本：逐字
    chars = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text)
    return chars or [text] if text else []


class Bm25Index:
    """与 VectorStore 元数据同步的 BM25 索引。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bm25: BM25Okapi | None = None
        self._ids: list[str] = []
        self._metas: list[dict] = []
        self._tokenized: list[list[str]] = []
        self._fingerprint: int = -1

    def rebuild_if_needed(self, ids: list[str], metas: list[dict]) -> None:
        fp = len(ids)
        if self._bm25 is not None and fp == self._fingerprint and len(self._ids) == len(ids):
            return
        with self._lock:
            self._ids = list(ids)
            self._metas = list(metas)
            corpus = []
            for m in metas:
                blob = f"{m.get('title', '')} {m.get('article', '')} {m.get('text', '')}"
                corpus.append(tokenize(blob))
            self._tokenized = corpus
            self._bm25 = BM25Okapi(corpus) if corpus else None
            self._fingerprint = fp

    def search(self, query: str, top_k: int = 20) -> list[dict]:
        with self._lock:
            if not self._bm25 or not self._ids:
                return []
            scores = self._bm25.get_scores(tokenize(query))
            order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            out: list[dict] = []
            for i in order:
                sc = float(scores[i])
                if sc <= 0:
                    continue
                m = self._metas[i]
                out.append(
                    {
                        "id": self._ids[i],
                        "doc_id": m["doc_id"],
                        "title": m["title"],
                        "category": m["category"],
                        "article": m.get("article", ""),
                        "page": m.get("page", 0),
                        "text": m.get("text", ""),
                        "score": round(sc, 4),
                        "match": "bm25",
                        "effective_status": m.get("effective_status", ""),
                        "effective_detail": m.get("effective_detail", ""),
                        "bian": m.get("bian", ""),
                        "chapter": m.get("chapter", ""),
                        "section": m.get("section", ""),
                    }
                )
            return out


_index: Bm25Index | None = None


def get_bm25_index() -> Bm25Index:
    global _index
    if _index is None:
        _index = Bm25Index()
    return _index
