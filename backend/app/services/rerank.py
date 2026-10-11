"""候选重排序：heuristic（默认）/ llm / cross_encoder（可选）。"""
from __future__ import annotations

import json
import logging
import re

from app.core.config import settings

logger = logging.getLogger("service.rerank")

_LAW_RE = re.compile(r"([\u4e00-\u9fff]{2,12}(?:法|条例|办法|规定|细则|规章))")
_ART_RE = re.compile(r"第([一二三四五六七八九十百千0-9]+)([条款章])")


def _heuristic_score(query: str, doc: dict) -> float:
    """无模型重排：关键词重叠 + 条款/效力加分 + RRF 分。"""
    q = query.lower()
    title = (doc.get("title") or "").lower()
    article = (doc.get("article") or "").lower()
    text = (doc.get("text") or "")[:400].lower()
    blob = f"{title} {article} {text}"

    score = float(doc.get("rrf_score") or 0.0) * 10.0
    for m in _LAW_RE.findall(query):
        if m in title or m in text:
            score += 1.5
    am = _ART_RE.search(query)
    if am and (am.group(0) in article or am.group(0) in blob):
        score += 2.0
    if "article" in (doc.get("match") or ""):
        score += 1.2
    if doc.get("effective_status") == "现行有效":
        score += 0.5
    elif doc.get("effective_status") == "已废止":
        score -= 1.0

    q_tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}", q))
    d_tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}", blob))
    if q_tokens:
        score += 2.0 * len(q_tokens & d_tokens) / max(len(q_tokens), 1)
    return score


def _heuristic_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    scored = []
    for c in candidates:
        row = dict(c)
        row["rerank_score"] = _heuristic_score(query, row)
        scored.append(row)
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[:top_k]


def _llm_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """用 LLM 对候选打 0-10 分（候选较多时只评前 N）。"""
    from app.services.llm import chat

    pool = candidates[: min(12, len(candidates))]
    lines = []
    for i, c in enumerate(pool, start=1):
        preview = (c.get("text") or "")[:180].replace("\n", " ")
        lines.append(f"{i}. 《{c.get('title')}》{c.get('article', '')} :: {preview}")
    prompt = (
        "你是法律检索重排器。根据用户问题，给下列候选材料打分（0-10 整数），"
        "只输出 JSON 数组，如 [8,3,9,...]，长度必须与候选数一致，不要其它文字。\n"
        f"问题：{query}\n候选：\n" + "\n".join(lines)
    )
    try:
        raw = chat(
            [{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
            timeout=60.0,
        )
        m = re.search(r"\[[\d,\s\.]+\]", raw)
        if not m:
            raise ValueError(f"无法解析重排分数: {raw[:120]}")
        scores = json.loads(m.group(0))
        if not isinstance(scores, list) or len(scores) != len(pool):
            raise ValueError("分数长度不匹配")
        ranked = []
        for c, s in zip(pool, scores):
            row = dict(c)
            row["rerank_score"] = float(s) + float(row.get("rrf_score") or 0) * 2
            ranked.append(row)
        ranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        seen = {r["id"] for r in ranked}
        for c in candidates:
            if c["id"] not in seen:
                row = dict(c)
                row["rerank_score"] = float(row.get("rrf_score") or 0)
                ranked.append(row)
        return ranked[:top_k]
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 重排失败，回退 heuristic: %s", exc)
        return _heuristic_rerank(query, candidates, top_k)


def _cross_encoder_rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """可选：fastembed TextCrossEncoder（需额外模型下载）。"""
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    engine = TextCrossEncoder(model_name=settings.rerank_model)
    docs = [f"{c.get('title', '')} {c.get('article', '')} {c.get('text', '')[:500]}" for c in candidates]
    ranks = list(engine.rerank(query, docs))
    scored = []
    if ranks and isinstance(ranks[0], (list, tuple)) and len(ranks[0]) >= 2:
        for item in ranks:
            idx, sc = int(item[0]), float(item[1])
            row = dict(candidates[idx])
            row["rerank_score"] = sc
            scored.append(row)
    else:
        for c, sc in zip(candidates, ranks):
            row = dict(c)
            row["rerank_score"] = float(sc)
            scored.append(row)
    scored.sort(key=lambda x: x["rerank_score"], reverse=True)
    return scored[:top_k]


def rerank_candidates(query: str, candidates: list[dict], top_k: int = 6) -> list[dict]:
    if not candidates:
        return []
    mode = (settings.rerank_mode or "heuristic").lower()
    if mode == "llm":
        return _llm_rerank(query, candidates, top_k)
    if mode == "cross_encoder":
        try:
            return _cross_encoder_rerank(query, candidates, top_k)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cross_encoder 不可用，回退 heuristic: %s", exc)
            return _heuristic_rerank(query, candidates, top_k)
    return _heuristic_rerank(query, candidates, top_k)
