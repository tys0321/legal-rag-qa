"""轻量向量库：numpy 余弦相似度检索 + JSON 持久化。

Phase 1 用轻量自研实现（几万到十几万块规模足够快），
Phase 3 规模化时无缝替换为 Milvus/Qdrant（接口保持一致）。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.services.embeddings import embed_query, embed_texts


_CN_DIGITS = "零一二三四五六七八九"

# 效力状态优先级（值越小越优先）：现行有效 > 已修订 > 部分失效 > 已废止 > 未知
_STATUS_PRIORITY = {"现行有效": 0, "已修订": 1, "部分失效": 2, "已废止": 3}


def _status_sort_key(doc: dict) -> tuple:
    """按效力状态 + 标题中的修正年份排序（现行有效优先、年份新者优先）。"""
    status = doc.get("effective_status", "")
    pri = _STATUS_PRIORITY.get(status, 4)
    # 从标题提取 4 位年份，取最新
    import re

    years = re.findall(r"(19|20)\d{2}", doc.get("title", ""))
    latest_year = max(int(y) for y in years) if years else 0
    # 返回 (状态优先级, -年份) 使得 sort 后优先
    return (pri, -latest_year)


def _to_chinese_numeral(num_str: str) -> str:
    """阿拉伯数字转中文数字（支持 1-99，够法规条款使用）。"""
    if not num_str.isdigit():
        return ""
    n = int(num_str)
    if n < 1 or n > 99:
        return ""
    if n <= 10:
        return "十" if n == 10 else _CN_DIGITS[n]
    tens, ones = divmod(n, 10)
    out = ""
    if tens > 1:
        out += _CN_DIGITS[tens]
    out += "十"
    if ones:
        out += _CN_DIGITS[ones]
    return out


class VectorStore:
    """内存向量库，磁盘持久化到 vector_store_dir。"""

    def __init__(self, store_dir: Path) -> None:
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._vectors: list[np.ndarray] = []
        self._metas: list[dict] = []
        self._ids: list[str] = []
        self._id_set: set[str] = set()
        self._loaded = False

    # ---------- 持久化 ----------
    @property
    def meta_path(self) -> Path:
        return self.store_dir / "meta.jsonl"

    @property
    def vec_path(self) -> Path:
        return self.store_dir / "vectors.npy"

    def save(self) -> None:
        """原子写入：先写临时文件再替换，避免崩溃损坏数据。"""
        import os

        with self._lock:
            arr = np.array(self._vectors, dtype=np.float32) if self._vectors else np.zeros((0, 0), dtype=np.float32)
            # vectors.npy：tmp 名不带 .npy，np.save 会写成 vectors_tmp.npy
            tmp_vec = self.vec_path.with_name("vectors_tmp")
            np.save(tmp_vec, arr)
            os.replace(Path(str(tmp_vec) + ".npy"), self.vec_path)
            # meta.jsonl
            tmp_meta = Path(str(self.meta_path) + ".tmp")
            with open(tmp_meta, "w", encoding="utf-8") as f:
                for mid, meta in zip(self._ids, self._metas):
                    f.write(json.dumps({"id": mid, **meta}, ensure_ascii=False) + "\n")
            os.replace(tmp_meta, self.meta_path)

    def load(self) -> None:
        if self._loaded:
            return
        if self.vec_path.exists() and self.meta_path.exists():
            arr = np.load(self.vec_path)
            with open(self.meta_path, encoding="utf-8") as f:
                lines = [json.loads(l) for l in f if l.strip()]
            self._ids = [l["id"] for l in lines]
            self._metas = [l for l in lines]
            self._id_set = set(self._ids)
            self._vectors = [arr[i] for i in range(len(arr))]
        self._loaded = True

    # ---------- 写入 ----------
    def add_chunks(self, chunks: list, vectors: list[list[float]] | None = None,
                   doc_meta: dict | None = None) -> int:
        """添加 Chunk 列表；可传入预计算向量与文档级元数据（效力状态等）。返回新增数量。"""
        self.load()
        texts = [c.text for c in chunks]
        vecs = vectors if vectors is not None else embed_texts(texts)
        added = 0
        with self._lock:
            for chunk, vec in zip(chunks, vecs):
                cid = f"{chunk.doc_id}#{chunk.chunk_index}"
                if cid in self._id_set:
                    continue
                self._ids.append(cid)
                self._id_set.add(cid)
                self._vectors.append(np.asarray(vec, dtype=np.float32))
                meta = {
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "category": chunk.category,
                    "article": chunk.article,
                    "page": chunk.page,
                    "text": chunk.text,
                    "chunk_index": chunk.chunk_index,
                }
                if doc_meta:
                    meta.update(doc_meta)
                self._metas.append(meta)
                added += 1
        self.save()
        return added

    def remove_doc(self, doc_id: str) -> int:
        """删除某文档的全部块。返回删除数量。"""
        self.load()
        removed = 0
        with self._lock:
            keep = [(i, v, m) for i, v, m in zip(self._ids, self._vectors, self._metas) if m.get("doc_id") != doc_id]
            removed = len(self._ids) - len(keep)
            if removed:
                self._ids = [k[0] for k in keep]
                self._vectors = [k[1] for k in keep]
                self._metas = [k[2] for k in keep]
                self._id_set = set(self._ids)
                self.save()
        return removed

    # ---------- 检索 ----------
    def search(self, query: str, top_k: int = 6, min_score: float = 0.0) -> list[dict]:
        """检索。法律场景增强：
        1) 查询含「第X条/章」时先做条款号精确匹配（若提到法律名则限定该文档）；
        2) 向量语义检索取足量候选（不被条款命中挤占配额）；
        3) 条款匹配优先，向量结果补足，去重后截断到 top_k。"""
        self.load()
        if not self._vectors:
            return []

        # 1) 条款号结构化匹配（感知查询中的法律名）
        article_hits = self._search_by_article(query, top_k)

        # 2) 向量语义检索：候选数 = top_k + 条款命中数，保证配额
        vec_candidates = top_k + len(article_hits)
        q = np.asarray(embed_query(query), dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        mat = np.array(self._vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        scores = (mat @ q).reshape(-1) / norms.reshape(-1)
        order = np.argsort(-scores)[:vec_candidates]

        article_ids = {r["id"] for r in article_hits}
        results: list[dict] = []
        seen: set[str] = set()
        # 条款匹配结果优先（保留匹配方式标注）
        for r in article_hits:
            if r["id"] not in seen:
                seen.add(r["id"])
                results.append(r)
        # 再补向量结果
        for i in order:
            score = float(scores[i])
            if score < min_score:
                continue
            cid = self._ids[i]
            if cid in seen:
                continue
            seen.add(cid)
            m = self._metas[i]
            results.append(
                {
                    "id": cid,
                    "doc_id": m["doc_id"],
                    "title": m["title"],
                    "category": m["category"],
                    "article": m["article"],
                    "page": m["page"],
                    "text": m["text"],
                    "score": round(score, 4),
                    "match": "article" if cid in article_ids else "vector",
                    "effective_status": m.get("effective_status", ""),
                    "effective_detail": m.get("effective_detail", ""),
                }
            )
        # 按效力状态排序：现行有效/最新版本优先（条款匹配的结果内部也按此排序）
        results = sorted(results, key=_status_sort_key)
        return results[:top_k]

    # ---------- 案例推荐检索 ----------
    def search_cases(self, query: str, top_k: int = 4) -> list[dict]:
        """相似案例推荐：语义检索 + 案例特征过滤。

        案例特征：类别为「司法解释」，或标题含 案例/批复/答复/决定/判例/指导案例 等。
        """
        self.load()
        if not self._vectors:
            return []

        q = np.asarray(embed_query(query), dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        mat = np.array(self._vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        scores = (mat @ q).reshape(-1) / norms.reshape(-1)
        order = np.argsort(-scores)

        results: list[dict] = []
        seen_docs: set[str] = set()
        for i in order:
            if len(results) >= top_k:
                break
            m = self._metas[i]
            title = m.get("title", "")
            category = m.get("category", "")
            is_case = (
                category in ("司法解释", "裁判文书", "案例")
                or any(k in title for k in ("案例", "批复", "答复", "决定", "判例", "指导案例", "公报"))
            )
            if not is_case:
                continue
            if m.get("doc_id") in seen_docs:
                continue
            seen_docs.add(m["doc_id"])
            results.append(
                {
                    "id": self._ids[i],
                    "doc_id": m["doc_id"],
                    "title": title,
                    "category": category,
                    "article": m.get("article", ""),
                    "page": m.get("page", 0),
                    "text": m.get("text", ""),
                    "score": round(float(scores[i]), 4),
                }
            )
        return results

    def _search_by_article(self, query: str, top_k: int) -> list[dict]:
        """从查询中提取「第X条/章」并做精确匹配。

        若查询提到法律名（如「劳动合同法第三十九条」），只匹配该文档的条款，
        避免跨法律同名条款（宪法/专利法都有第39条）干扰。
        """
        import re

        m = re.search(r"第([一二三四五六七八九十百千0-9]+)([条款章])", query)
        if not m:
            return []
        num, unit = m.group(1), m.group(2)

        # 提取查询中的法律名（形如「XX法」「XX条例」「XX办法」）
        law_match = re.search(r"([\u4e00-\u9fff]{2,12}(?:法|条例|办法|规定|细则|规章))", query)
        law_name = law_match.group(1) if law_match else ""

        # 生成候选写法：阿拉伯数字与中文数字
        candidates = {num}
        cn = _to_chinese_numeral(num)
        if cn:
            candidates.add(cn)
        for cand in candidates:
            target = f"第{cand}{unit}"
            hits = [
                i for i, meta in enumerate(self._metas)
                if meta.get("article") == target
                and (not law_name or law_name in meta.get("title", ""))
            ]
            if hits:
                out = []
                for i in hits[:top_k]:
                    meta = self._metas[i]
                    out.append(
                        {
                            "id": self._ids[i],
                            "doc_id": meta["doc_id"],
                            "title": meta["title"],
                            "category": meta["category"],
                            "article": meta["article"],
                            "page": meta["page"],
                            "text": meta["text"],
                            "score": 1.0,
                            "match": "article",
                            "effective_status": meta.get("effective_status", ""),
                            "effective_detail": meta.get("effective_detail", ""),
                        }
                    )
                return out
        return []

    # ---------- 统计 ----------
    def stats(self) -> dict:
        self.load()
        docs: dict[str, dict] = {}
        for m in self._metas:
            d = docs.setdefault(m["doc_id"], {"title": m["title"], "category": m["category"], "chunks": 0})
            d["chunks"] += 1
        return {"chunk_count": len(self._ids), "doc_count": len(docs), "docs": docs}

    def doc_list(self) -> list[dict]:
        self.load()
        docs: dict[str, dict] = {}
        for m in self._metas:
            d = docs.setdefault(
                m["doc_id"],
                {
                    "doc_id": m["doc_id"],
                    "title": m["title"],
                    "category": m["category"],
                    "chunks": 0,
                    "effective_status": m.get("effective_status", ""),
                    "effective_detail": m.get("effective_detail", ""),
                },
            )
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda x: x["doc_id"])


_store: VectorStore | None = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore(settings.vector_store_dir)
        _store.load()
    return _store
